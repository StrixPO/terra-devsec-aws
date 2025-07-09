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

def detect_secrets(content: str) -> list:
    patterns = {
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Private Key": r"-----BEGIN (RSA|EC|DSA)? PRIVATE KEY-----",
        "Password Pattern": r"password\s*=\s*['\"].+?['\"]",
        "Secret Pattern": r"secret\s*=\s*['\"].+?['\"]",
        "JWT Token": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    }

    detected = []
    for label, pattern in patterns.items():
        if re.search(pattern, content, re.IGNORECASE):
            detected.append(label)
    return detected

def lambda_handler(event, context):
    if event["requestContext"]["http"]["method"] == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            },
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        body = json.loads(event.get("body", "{}"))
        paste_id = body.get("paste_id", str(uuid.uuid4()))
        content = body.get("content", "")
        expiry_seconds = int(body.get("expiry_second", 3600))
        content_encrypted = body.get("content_encrypted", False)
    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {  
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"message": f"Invalid input: {e}"})
        }
    
    if not re.match(r"^[a-zA-Z0-9_-]{3,50}$", paste_id):
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
    if content_str and len(content_bytes) <= MAX_INLINE_SIZE:
        item["content"] = {"S": content_str}
    if secrets_found:
        item["has_secrets"] = {"BOOL":True}
        item["secret_types"] = {"S": ", ".join(secrets_found)}
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

