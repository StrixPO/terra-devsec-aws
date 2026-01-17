import json
import os
import time
import boto3
import traceback
import re
import base64

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

table_name = os.environ.get('TABLE_NAME', 'missing')
bucket_name = os.environ.get('BUCKET_NAME', 'missing')


def lambda_handler(event, context):
    """
    Retrieve Paste (Read Path) - one-time read semantics.

    SECURITY INVARIANTS:
    - Paste content must not be logged (plaintext or ciphertext).
    - If encrypted == True, this function MUST NOT attempt decryption.
      It returns ciphertext + metadata (salt/iv) only.
    - Enforce one-time-read by marking "used" to True after successful retrieval.
      (Caveat: not perfectly atomic in current implementation; see TODO.)

    EXPIRY:
    - We check expiry in read-path even though DynamoDB TTL exists.
      TTL is eventual, so this prevents serving expired content during the TTL lag window.
    """

    # Logging full event is helpful during development but dangerous in production:
    # request bodies can contain paste_id and potentially other metadata.
    # Consider toggling with an env var like DEBUG_LOGS.
    print("=== EVENT RECEIVED (debug) ===")
    print(json.dumps(event, indent=2))

    # Parse request and validate paste_id early.
    try:
        body = json.loads(event.get("body", "{}"))
        paste_id = body.get("paste_id")

        if not paste_id:
            raise Exception("paste_id is missing in request body")

        paste_id = paste_id.strip()

        # Strict validation prevents weird keys, log injection, and S3 path shenanigans.
        if not re.match(r"^[a-zA-Z0-9_-]{10,50}$", paste_id):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": "Invalid paste_id format. Use 10-50 chars: letters, numbers, underscore, dash."
                })
            }

    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid or missing paste_id", "error": str(e)})
        }

    try:
        # Fetch metadata and (maybe) inline content.
        response = dynamodb.get_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}}
        )

        item = response.get("Item")
        if not item:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste not found"})
            }

        # Expiry check: prevents serving content during DynamoDB TTL delay.
        expiry_ts = int(item.get("expiry", {}).get("N", "0"))
        if expiry_ts < int(time.time()):
            return {
                "statusCode": 410,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste expired"})
            }

        # One-time-read check.
        if item.get("used", {}).get("BOOL", False):
            return {
                "statusCode": 410,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste already viewed"})
            }

        encrypted = item.get("encrypted", {}).get("BOOL", False)
        content = ""

        # Content may live in S3 (large pastes) or in DynamoDB inline (small pastes).
        if "s3_key" in item:
            s3_key = item["s3_key"]["S"]

            try:
                s3_obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
                content_bytes = s3_obj["Body"].read()

                if encrypted:
                    # Encrypted content must remain opaque: return as base64 string.
                    content = base64.b64encode(content_bytes).decode("ascii")
                else:
                    # Plaintext stored in S3 is expected to be UTF-8 text.
                    content = content_bytes.decode("utf-8")

            except Exception as e:
                traceback.print_exc()
                return {
                    "statusCode": 500,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"message": "Failed to retrieve content from S3", "error": str(e)})
                }

        elif "content" in item:
            # If encrypted and inline, item["content"] is base64 ciphertext string.
            # If plaintext and inline, it's the plain string.
            content = item["content"]["S"]
        else:
            content = ""

        # Mark paste as used.
        #
        # TODO (important for professionalism):
        # This should be conditional to prevent race conditions:
        # UpdateExpression + ConditionExpression (used = false AND expiry >= now)
        # Otherwise two fast requests could both succeed before 'used' flips.
        dynamodb.update_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}},
            UpdateExpression="SET used = :val",
            ExpressionAttributeValues={":val": {"BOOL": True}}
        )

        response_body = {
            "paste_id": paste_id,
            "encrypted": encrypted,
            "content": content,
            "message": "Paste retrieved successfully"
        }

        # Encrypted pastes require client-side decryption metadata.
        if encrypted:
            salt = item.get("salt", {}).get("S")
            iv = item.get("iv", {}).get("S")

            # If these are missing, the paste cannot be decrypted client-side.
            # Treat as server-side error: the paste is malformed/incomplete.
            if not salt or not iv:
                return {
                    "statusCode": 500,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({
                        "message": "Encrypted paste missing required decryption metadata (salt/iv)"
                    })
                }

            response_body["salt"] = salt
            response_body["iv"] = iv

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps(response_body)
        }

    except Exception as e:
        # Avoid returning stack traces in production.
        # It's useful for you now, but it leaks internal info in public deployments.
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Internal server error",
                "error": str(e),
                "trace": traceback.format_exc()
            })
        }
