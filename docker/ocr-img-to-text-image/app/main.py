# import boto3
# import json
# import time
# import pytesseract
# from PIL import Image
# import requests
# import io

# sqs = boto3.client('sqs')
# s3 = boto3.client('s3')

# QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/090081990755/pdf-queue'

# def process_image(bucket, key):
#     obj = s3.get_object(Bucket=bucket, Key=key)
#     img = Image.open(io.BytesIO(obj['Body'].read()))
#     text = pytesseract.image_to_string(img)
#     print(f"Some extracted text: {text[:100]}")
#     # Save or store the result somewhere (S3/DynamoDB)
#     return text

# def poll_queue():
#     while True:
#         resp = sqs.receive_message(
#             QueueUrl=QUEUE_URL,
#             MaxNumberOfMessages=1,
#             WaitTimeSeconds=10
#         )
#         messages = resp.get('Messages', [])
#         for msg in messages:
#             print(msg)
            
#             body = json.loads(msg['Body'])
#             bucket = body['bucket']
#             key = body['key']
#             print(f"Processing {key} from {bucket}")
#             process_image(bucket, key)
#             sqs.delete_message(
#                 QueueUrl=QUEUE_URL,
#                 ReceiptHandle=msg['ReceiptHandle']
#             )

# if __name__ == "__main__":
#     poll_queue()

import boto3
import json
import time
import pytesseract
from PIL import Image, UnidentifiedImageError
import io
import traceback
import os

sqs = boto3.client('sqs')
s3 = boto3.client('s3')

# QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/090081990755/pdf-queue'
# OUTPUT_BUCKET = 'your-output-bucket'  # Replace with your target bucket

# Set these from env
QUEUE_URL = os.environ["SQS_QUEUE_URL"]
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "")  # Optional

def process_image(bucket, key):
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        img = Image.open(io.BytesIO(obj['Body'].read()))
        text = pytesseract.image_to_string(img)

        print(f"[✓] Extracted text from {key[:50]}...")

        # Save extracted text to S3
        output_key = key.replace("images/", "ocr-text/") + ".txt"
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=text.encode('utf-8')
        )

        print(f"[→] Saved OCR text to s3://{OUTPUT_BUCKET}/{output_key}")
        return True

    except UnidentifiedImageError:
        print(f"[!] Could not identify image format for: {key}")
    except Exception as e:
        print(f"[!] Error processing image {key}: {str(e)}")
        traceback.print_exc()
    return False

def poll_queue():
    print("[*] Starting image processing worker...")
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            messages = resp.get('Messages', [])
            for msg in messages:
                try:
                    body = json.loads(msg['Body'])
                    bucket = body['bucket']
                    key = body['key']
                    print(f"[>] Received message: bucket={bucket}, key={key}")

                    success = process_image(bucket, key)

                    if success:
                        sqs.delete_message(
                            QueueUrl=QUEUE_URL,
                            ReceiptHandle=msg['ReceiptHandle']
                        )
                        print("[✓] Message deleted from queue")
                    else:
                        print("[x] Skipping deletion due to failure")

                except json.JSONDecodeError:
                    print("[!] Failed to parse SQS message body")
                    traceback.print_exc()

        except Exception as e:
            print(f"[!] Error polling queue: {str(e)}")
            traceback.print_exc()
        time.sleep(1)

if __name__ == "__main__":
    poll_queue()