import json
import os
import time
import boto3
import traceback
import re

dynamodb = boto3.client('dynamodb')

table_name = os.environ.get('TABLE_NAME', 'missing')
bucket_name = os.environ.get('BUCKET_NAME', 'missing')

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))
    print("TABLE:", table_name)

    paste_id = event.get("pathParameters", {}).get("paste_id")
    
    if not paste_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "Missing paste_id"})
        }

    try:
        response = dynamodb.get_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}}
        )
        item = response.get("Item")
        if not item:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Paste not found"})
            }

        # Expiry check
        expiry_ts = int(item.get("expiry", {}).get("N", "0"))
        if expiry_ts < int(time.time()):
            return {
                "statusCode": 410,
                "body": json.dumps({"message": "Paste expired"})
            }

        # One-time use check
        if item.get("used", {}).get("BOOL", False):
            return {
                "statusCode": 410,
                "body": json.dumps({"message": "Paste already viewed"})
            }

        # Mark as used
        content = ""
        encrypted = item.get("encrypted", {}).get("BOOL", False)

        if "s3_key" in item:
            s3_key = item["s3_key"]["S"]
            s3 = boto3.client('s3')

            try:
                s3_obj = s3.get_object(
                    Bucket=os.environ.get('BUCKET_NAME'),
                    Key = s3_key
                )
                content = s3_obj['Body'].read().decode('utf-8')
            except Exception as e:
                print("s3 fetch error: ", str(e))
                traceback.print_exc()
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "message": "Failed to retrieve content from s3"
                    })
                }
        elif "content" in item:
            content = item["content"]["S"]

        dynamodb.update_item(
            TableName=table_name,
            Key={"paste_id": {"S": paste_id}},
            UpdateExpression="SET used = :val",
            ExpressionAttributeValues={":val": {"BOOL": True}}
        )

        if item.get("has_secrets", {}).get("BOOL", False):
            return {
                "statusCode": 403,
                "body": json.dumps({
                    "message": "Paste flagged as containing sensitive patterns",
                    "secret_types": item.get("secret_types", {}).get("S", "")
                })
            }

        return {
            "statusCode": 200,
            "body": json.dumps({
                "paste_id": paste_id,
                "encrypted": encrypted,
                "content": content,
                "message": "Paste retrieved successfully"
            })
        }

    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal error"})
        }
