import json
import os
import time
import boto3
import uuid
import base64
import re

# AWS clients are created at import time to benefit from Lambda container reuse.
# This reduces cold-start overhead compared to creating clients inside the handler.
dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

# Configuration is provided via environment variables in AWS. Defaults are "missing" to fail loudly.
table_name = os.environ.get('TABLE_NAME', 'missing')
bucket_name = os.environ.get('BUCKET_NAME', 'missing')

# DynamoDB has a 400KB item size limit, but we also want to keep responses and storage efficient.
# Pastes larger than this are stored in S3 instead of DynamoDB.
MAX_INLINE_SIZE = 4096  # bytes


def detect_secrets(content: str) -> list:
    """
    Best-effort secrets detection for *unencrypted* content.

    SECURITY NOTE:
    - This is *not* a security boundary. It's a UX warning mechanism.
    - False positives/negatives are expected. We only use this to nudge users toward encryption.

    RETURNS:
    - Sorted list of detected secret categories (strings).
    """
    detected = set()

    # Regex patterns for common credential/token formats.
    # Add patterns carefully: high false-positive patterns will annoy users and reduce trust.
    patterns = {
        "AWS Access Key": r"\bAKIA[0-9A-Z]{16}\b",
        "Private Key": r"-----BEGIN (?:RSA|EC|DSA)? PRIVATE KEY-----",
        "Password Pattern": r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]+['\"]",
        "Secret Pattern": r"(?i)\bsecret\s*[:=]\s*['\"][^'\"]+['\"]",
        "JWT Token": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
        "GitHub PAT": r"\b(?:gh[pousr]_[A-Za-z0-9_]{36}|github_pat_[A-Za-z0-9_]{22,255})\b",
        "Azure GUID": r"\b[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[1-5][a-fA-F0-9]{3}-[89abAB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}\b",
        "Docker Auth Base64": r'"auth"\s*:\s*"([A-Za-z0-9+/=]{20,})"',
        "GCP Service Account Email": r"\b[0-9a-zA-Z._%+-]+@[0-9a-zA-Z.-]+\.iam\.gserviceaccount\.com\b",
        "Google API Key": r"\bAIza[0-9A-Za-z\-_]{35}\b",
        "GCP Refresh Token": r"\b1\/[0-9a-zA-Z\-_]{35,}\b",
        "GCP Client Secret": r"\b[A-Z0-9]{24}\b",
        "GCP Client ID": r"\b[0-9]{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com\b",
        "GCP Private Key ID": r"\b[0-9a-f]{40}\b"
    }

    # Trivial placeholders we ignore to reduce noise.
    placeholders = {"changeme", "password", "secret", "dummy", "example"}

    def entropy(s: str) -> float:
        """
        Lightweight entropy estimate to filter obvious low-entropy junk (esp. base64-ish strings).
        Not crypto-grade. Just a heuristic.
        """
        from math import log2
        if not s:
            return 0.0
        freq = {}
        for c in s:
            freq[c] = freq.get(c, 0) + 1
        e = 0.0
        length = len(s)
        for count in freq.values():
            p = count / length
            e -= p * log2(p)
        return e

    def azure_guid_in_context(match_obj):
        """
        Reduce false positives: GUIDs are everywhere.
        Only flag if nearby text suggests Azure identity context.
        """
        window = content[max(0, match_obj.start() - 40): match_obj.end() + 40].lower()
        keywords = ["client_id", "tenant_id", "subscription_id", "applicationid", "app_id"]
        return any(k in window for k in keywords)

    for label, pattern in patterns.items():
        for m in re.finditer(pattern, content):
            raw = m.group(0)
            low = raw.lower()

            # Skip obvious dummy/test values.
            if any(p in low for p in placeholders):
                continue

            # GUIDs require contextual keywords or we ignore them.
            if label == "Azure GUID" and not azure_guid_in_context(m):
                continue

            # For docker auth, we check the captured "auth" field only.
            if label == "Docker Auth Base64":
                inner = m.group(1)
                if any(p in inner.lower() for p in placeholders):
                    continue
                if entropy(inner) < 3.5:
                    continue
                detected.add(label)
                continue

            detected.add(label)

    # Heuristic for embedded service account JSON.
    if '"type"' in content and 'service_account' in content and '"private_key"' in content:
        detected.add("GCP Service Account JSON")

    return sorted(detected)


def lambda_handler(event, context):
    """
    Create Paste (Write Path)

    SECURITY INVARIANTS:
    - If content_encrypted == True, the server MUST treat content as opaque ciphertext.
      That means: no plaintext parsing, no "smart" transformations, no logging of content.
    - Avoid logging sensitive material (plaintext or ciphertext). Logs are a common leak path.
      (Right now the code prints sizes/types; keep it that way.)

    STORAGE POLICY:
    - Small payloads (<= MAX_INLINE_SIZE) are stored inline in DynamoDB.
    - Large payloads are stored in S3; DynamoDB stores only metadata + s3_key.
    - TTL is recorded for eventual deletion; actual deletion is best-effort (Dynamo TTL is not instant).
    """

    # Handle CORS preflight for API Gateway HTTP API.
    # Note: event formats differ between REST API vs HTTP API; hence defensive lookups.
    if "requestContext" in event and event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    # Parse and validate request body early to fail fast (cheaper and safer).
    try:
        body = json.loads(event.get("body", "{}"))

        # paste_id is client-provided or server-generated. Client-provided supports "bring your own ID".
        # SECURITY NOTE: IDs should be non-enumerable (random). If allowing client-provided IDs,
        # validate strictly to avoid injection/path issues.
        paste_id = body.get("paste_id", str(uuid.uuid4()))
        content = body.get("content", "")
        expiry_seconds = int(body.get("expiry_seconds", 3600))

        # content_encrypted indicates whether content is ciphertext (base64 string) from the client.
        # In a true zero-trust design, this should be True by default in the frontend.
        content_encrypted = body.get("content_encrypted", False)

        # Enforce retention bounds server-side so a malicious client cannot set "forever".
        MIN_EXPIRY = 300       # 5 minutes
        MAX_EXPIRY = 604800    # 7 days
        if expiry_seconds < MIN_EXPIRY or expiry_seconds > MAX_EXPIRY:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": f"Expiry must be between {MIN_EXPIRY} and {MAX_EXPIRY} seconds"
                })
            }

        # Protect Lambda + downstream services from huge payloads.
        MAX_CONTENT_SIZE = 1024 * 1024  # 1MB
        content_size = len(content.encode('utf-8'))
        if content_size > MAX_CONTENT_SIZE:
            return {
                "statusCode": 413,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": f"Content too large. Maximum size is 1MB ({MAX_CONTENT_SIZE} bytes). Your content is {content_size} bytes."
                })
            }

    except Exception as e:
        # Do not echo raw exception details in production if you can avoid it.
        # It can leak parsing behavior. For now we keep it for dev visibility.
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": f"Invalid input: {e}"})
        }

    # Strict ID validation reduces attack surface (S3 key construction, DynamoDB keys, etc).
    # NOTE: error message says (3-50 chars) but regex enforces (10-50). Keep those consistent.
    if not re.match(r"^[a-zA-Z0-9_-]{10,50}$", paste_id):
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Invalid paste_id format. Use only letters, numbers, dashes, and underscores (10-50 chars)."
            })
        }

    # Expiry timestamp is stored for:
    # - API checks (return 410 when expired)
    # - DynamoDB TTL (eventual removal)
    expiry_ts = int(time.time()) + expiry_seconds

    s3_key = None
    content_bytes = b""
    content_str = ""

    # Avoid printing content itself. Sizes/types are okay; content is not.
    print("Type of content:", type(content))
    print("Content size in bytes (pre-encoding):", len(content.encode("utf-8")))

    # If encrypted: content is expected to be a base64 string of ciphertext bytes.
    # We decode to bytes for storage (S3) or keep base64 string for inline DynamoDB storage.
    if content_encrypted:
        try:
            content_bytes = base64.b64decode(content.encode())
        except Exception as e:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "message": "Invalid base64 content",
                    "error": str(e)
                })
            }
    else:
        # Plaintext path: store as utf-8 bytes; also keep string for secret detection and inline storage.
        content_bytes = content.encode("utf-8")
        content_str = content

    # Secrets detection is only meaningful for plaintext.
    # We do this *before* storage so we can store metadata flags.
    secrets_found = []
    if not content_encrypted and content_str:
        secrets_found = detect_secrets(content_str)

    # Storage decision:
    # - If payload is large: store in S3.
    # - Otherwise: store directly in DynamoDB.
    #
    # SECURITY NOTE:
    # - S3 uses ServerSideEncryption="AES256" (SSE-S3). Consider SSE-KMS if you want KMS-backed auditing/key control.
    # - In "zero trust" framing, SSE is defense-in-depth; the real confidentiality should come from client-side encryption.
    if len(content_bytes) > MAX_INLINE_SIZE:
        ext = ".enc" if content_encrypted else ".txt"
        s3_key = f"pastes/{paste_id}{ext}"

        try:
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=content_bytes,
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": "Failed to upload to S3",
                    "error": str(e)
                })
            }

    # DynamoDB item contains metadata required for retrieval + deletion.
    item = {
        "paste_id": {"S": paste_id},
        "expiry": {"N": str(expiry_ts)},
        "ttl": {"N": str(expiry_ts)},     # DynamoDB TTL attribute (eventual deletion)
        "used": {"BOOL": False},          # One-time-read semantics
        "encrypted": {"BOOL": content_encrypted}
    }

    # If stored in S3, we keep only the key in DynamoDB.
    if s3_key:
        item["s3_key"] = {"S": s3_key}

    # If small enough, store inline in DynamoDB.
    # NOTE: For encrypted content we store the *base64 string* so retrieval can return it as-is.
    if len(content_bytes) <= MAX_INLINE_SIZE:
        if content_encrypted:
            item["content"] = {"S": content}  # already base64 string from frontend
        else:
            item["content"] = {"S": content_str}

    # Save detection results as metadata (do NOT store matches; only categories).
    if secrets_found:
        item["has_secrets"] = {"BOOL": True}
        item["secret_types"] = {"S": ", ".join(secrets_found)}

    # If encrypted, store decryption metadata required by the client.
    # SECURITY NOTE:
    # - salt/iv are not secrets; they can be stored server-side.
    # - Never store the user's encryption key.
    if content_encrypted:
        salt = body.get("salt")
        iv = body.get("iv")
        if salt:
            item["salt"] = {"S": salt}
        if iv:
            item["iv"] = {"S": iv}

    # Debug logging: keep it minimal. Avoid dumping full item if it can contain plaintext.
    # Right now item["content"] may contain plaintext for small, unencrypted pastes.
    # TODO (recommended): remove/guard this in production.
    print("Secrets found:", secrets_found)
    print("DynamoDB Item keys:", list(item.keys()))

    try:
        dynamodb.put_item(TableName=table_name, Item=item)
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Internal server error",
                "error": str(e)
            })
        }

    # Response includes warnings for plaintext secrets, but does not expose the content.
    response_data = {
        "message": f"Paste {paste_id} created.",
        "paste_id": paste_id,
        "expiry_seconds": expiry_seconds,
        "content_length": len(content_bytes),
        "secrets_detected": len(secrets_found) > 0,
        "secret_types": secrets_found
    }

    if secrets_found and not content_encrypted:
        response_data["warning"] = "⚠️ Potential secrets detected! Consider using encryption for sensitive data."

    return {
        "statusCode": 201,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps(response_data)
    }
