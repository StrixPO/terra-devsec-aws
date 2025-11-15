import json
import os
import time
import boto3
import uuid
import base64
import hashlib
import re

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

table_name = os.environ.get('TABLE_NAME', 'missing')
bucket_name = os.environ.get('BUCKET_NAME', 'missing')

MAX_INLINE_SIZE = 4096

# def detect_secrets(content: str) -> list:
#     patterns = {
#         "AWS Access Key": r"AKIA[0-9A-Z]{16}",
#         "Private Key": r"-----BEGIN (RSA|EC|DSA)? PRIVATE KEY-----",
#         "Password Pattern": r"password\s*=\s*['\"].+?['\"]",
#         "Secret Pattern": r"secret\s*=\s*['\"].+?['\"]",
#         "JWT Token": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
#     }

#     detected = []
#     for label, pattern in patterns.items():
#         if re.search(pattern, content, re.IGNORECASE):
#             detected.append(label)
#     return detected

def detect_secrets(content: str) -> list:
    detected = set()

    # improved + expanded patterns
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
        # New GCP patterns for enhanced detection
        "GCP Refresh Token": r"\b1\/[0-9a-zA-Z\-_]{35,}\b",
        "GCP Client Secret": r"\b[A-Z0-9]{24}\b",
        "GCP Client ID": r"\b[0-9]{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com\b",
        "GCP Private Key ID": r"\b[0-9a-f]{40}\b"
    }

    # trivial placeholders to ignore
    placeholders = {"changeme", "password", "secret", "dummy", "example"}

    # helper: simple entropy for base64-looking strings (inline, minimal)
    def entropy(s: str) -> float:
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

    # context check for Azure GUID to avoid orphan matches
    def azure_guid_in_context(match_obj):
        window = content[max(0, match_obj.start() - 40): match_obj.end() + 40].lower()
        keywords = ["client_id", "tenant_id", "subscription_id", "applicationid", "app_id"]
        return any(k in window for k in keywords)

    for label, pattern in patterns.items():
        for m in re.finditer(pattern, content):
            raw = m.group(0)
            low = raw.lower()
            if any(p in low for p in placeholders):
                continue  # skip obvious dummy values

            if label == "Azure GUID":
                if not azure_guid_in_context(m):
                    continue  # ignore GUIDs without related keywords

            if label == "Docker Auth Base64":
                inner = m.group(1)
                if any(p in inner.lower() for p in placeholders):
                    continue
                # basic entropy threshold to avoid low-entropy junk
                if entropy(inner) < 3.5:
                    continue
                detected.add(label)
                continue

            detected.add(label)

    # lightweight heuristic for embedded full GCP service account JSON
    if '"type"' in content and 'service_account' in content and '"private_key"' in content:
        detected.add("GCP Service Account JSON")

    return sorted(detected)



def lambda_handler(event, context):
    if event["requestContext"]["http"]["method"] == "OPTIONS":
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

    try:
        body = json.loads(event.get("body", "{}"))
        paste_id = body.get("paste_id", str(uuid.uuid4()))
        content = body.get("content", "")
        expiry_seconds = int(body.get("expiry_seconds", 3600))
        content_encrypted = body.get("content_encrypted", False)
    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {  
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": f"Invalid input: {e}"})
        }
    
    if not re.match(r"^[a-zA-Z0-9_-]{10,50}$", paste_id):
        return {
            "statusCode": 400,
            "body": json.dumps({
                "message": "Invalid paste_id format. Use only letters, numbers, dashes, and underscores (3-50 chars)."
            })
        }

    expiry_ts = int(time.time()) + expiry_seconds
    s3_key = None
    content_bytes = b""
    content_str = ""

    print("Type of content:", type(content))
    print("Content size in bytes (pre-encoding):", len(content.encode("utf-8")))

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
        content_bytes = content.encode("utf-8")
        content_str = content
    
     # Detect secrets if not encrypted
    secrets_found = []
    if not content_encrypted and content_str:
        secrets_found = detect_secrets(content_str)

    # Store large or encrypted content in S3
    if len(content_bytes) > MAX_INLINE_SIZE:
        ext = ".enc" if content_encrypted else ".txt"
        s3_key = f"pastes/{paste_id}{ext}"
        try:
            result = s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=content_bytes,
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {  
                "Access-Control-Allow-Origin": "*"
            },
                "body": json.dumps({
                    "message": "Failed to upload to S3",
                    "error": str(e)
                })
            }

    # Prepare item for DynamoDB
    item = {
        "paste_id": {"S": paste_id},
        "expiry": {"N": str(expiry_ts)},
        "ttl": {"N": str(expiry_ts)},  # Optional: For DynamoDB TTL
        "used": {"BOOL": False},
        "encrypted": {"BOOL": content_encrypted}
    }

    if s3_key:
        item["s3_key"] = {"S": s3_key}
    if not content_encrypted and content_str and len(content_bytes) <= MAX_INLINE_SIZE:
        item["content"] = {"S": content_str}
    if secrets_found:
        item["has_secrets"] = {"BOOL":True}
        item["secret_types"] = {"S": ", ".join(secrets_found)}

    if content_encrypted:
        salt = body.get("salt")
        iv = body.get("iv")
        if salt:
            item["salt"] = {"S": salt}
        if iv:
            item["iv"] = {"S": iv}
    print("Secrets found:", secrets_found)
    print("DynamoDB Item:", json.dumps(item, indent=2))

    try:
        dynamodb.put_item(
            TableName=table_name,
            Item=item
        )
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": { 
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Internal server error",
                "error": str(e)
            })
        }


    return {
    "statusCode": 201,
    "headers": {  
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
    "body": json.dumps({
        "message": f"Paste {paste_id} created.",
        "expiry_seconds": expiry_seconds,
        "content_length": len(content_bytes),
        "secrets_detected": len(secrets_found) > 0,
        "secret_types": secrets_found
    })
}

