import json
import os
import time
import boto3
import traceback
import re

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

table_name = os.environ.get('TABLE_NAME', 'missing')
bucket_name = os.environ.get('BUCKET_NAME', 'missing')

def lambda_handler(event, context):
    print("=== FULL EVENT RECEIVED ===")
    print(json.dumps(event, indent=2))

    try:
        body = json.loads(event.get("body", "{}"))
        paste_id = body.get("paste_id")

        print("Paste ID received:", paste_id)
        if not paste_id:
            raise Exception("paste_id is missing in request body")

        paste_id = paste_id.strip()

        # Validate paste_id format
        if not re.match(r"^[a-zA-Z0-9_-]{10,50}$", paste_id):
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": "Invalid paste_id format. Use 10-50 chars: letters, numbers, underscore, or dash."
                })
            }

    except Exception as e:
        print("Input validation error:", str(e))
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"message": "Invalid or missing paste_id", "error": str(e)})
        }

    try:
        print("Fetching from DynamoDB...")
        response = dynamodb.get_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}}
        )
        print("DynamoDB response:", json.dumps(response, indent=2))

        item = response.get("Item")
        if not item:
            print(f"No item found for paste_id: {paste_id}")
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste not found"})
            }

        # Check expiry
        expiry_ts = int(item.get("expiry", {}).get("N", "0"))
        print("Paste expiry timestamp:", expiry_ts)
        if expiry_ts < int(time.time()):
            print("Paste expired.")
            return {
                "statusCode": 410,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste expired"})
            }

        # Check if already used (one-time)
        if item.get("used", {}).get("BOOL", False):
            print("Paste already viewed.")
            return {
                "statusCode": 410,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"message": "Paste already viewed"})
            }

        encrypted = item.get("encrypted", {}).get("BOOL", False)
        content = ""

        if "s3_key" in item:
            s3_key = item["s3_key"]["S"]
            print(f"Fetching content from S3 key: {s3_key}")
            try:
                s3_obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
                content = s3_obj['Body'].read().decode('utf-8')
                print("Successfully fetched content from S3.")
            except Exception as e:
                print("Error fetching from S3:", str(e))
                traceback.print_exc()
                return {
                    "statusCode": 500,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"message": "Failed to retrieve content from S3", "error": str(e)})
                }
        elif "content" in item:
            content = item["content"]["S"]
            print("Content retrieved from DynamoDB directly.")
        else:
            print("No content found in item.")
            content = ""

        # Mark paste as used
        print("Marking paste as used...")
        dynamodb.update_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}},
            UpdateExpression="SET used = :val",
            ExpressionAttributeValues={":val": {"BOOL": True}}
        )
        print("Paste marked as used.")

        # Check for secrets flag
        if item.get("has_secrets", {}).get("BOOL", False):
            print("Paste contains secrets.")
            return {
                "statusCode": 403,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "message": "Paste flagged as containing sensitive patterns",
                    "secret_types": item.get("secret_types", {}).get("S", "")
                })
            }

        print("Returning successful response.")
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "paste_id": paste_id,
                "encrypted": encrypted,
                "content": content,
                "message": "Paste retrieved successfully"
            })
        }

    except Exception as e:
        print("Unhandled error:", str(e))
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
