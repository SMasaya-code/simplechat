import json
import os
import re
import urllib.request
import urllib.error

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

# モデルID（未使用だが環境変数はそのまま残す）
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得（省略可能だが残しておく）
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)

        # ---  FastAPI へ送信する部分ここから ---
        fastapi_url = "https://b2b0-34-83-115-79.ngrok-free.app/predict"  

        fastapi_payload = json.dumps({
            "message": message,
            "conversationHistory": conversation_history
        }).encode('utf-8')

        req = urllib.request.Request(
            fastapi_url,
            data=fastapi_payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            fastapi_response = json.loads(response.read().decode('utf-8'))
        print("FastAPI response:", fastapi_response)
        # ---  FastAPI へ送信する部分ここまで ---

        assistant_response = fastapi_response.get("response", "")
        updated_history = fastapi_response.get("conversationHistory", [])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": updated_history
            })
        }

    except urllib.error.HTTPError as e:
        print("HTTPError:", e.read().decode())
        return {
            "statusCode": e.code,
            "body": json.dumps({"success": False, "error": e.reason})
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }

