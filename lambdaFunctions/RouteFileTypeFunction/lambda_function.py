import boto3
import os
import mimetypes
import json
import filetype

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

QUEUE_MAP = {
    'application/pdf': os.environ['PDF_QUEUE_URL'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': os.environ['DOCX_QUEUE_URL'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': os.environ['EXCEL_QUEUE_URL'],
    'image/jpeg': os.environ['IMAGE_QUEUE_URL'],
    'image/png': os.environ['IMAGE_QUEUE_URL']
}

def lambda_handler(event, context):
    print(event)
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Download first few KBs
        response = s3.get_object(Bucket=bucket, Key=key, Range='bytes=0-2048')
        content = response['Body'].read()

        # Detect file type
        kind = filetype.guess(content)
        print("Detected type:", kind)

        if kind and kind.mime in QUEUE_MAP:
            queue_url = QUEUE_MAP[kind.mime]
            message = {
                'bucket': bucket,
                'key': key,
                'detected_type': kind.mime
            }
            sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))
            print(f"Sent to queue {queue_url}")
        else:
            print(f"Unknown file type for: {key}")

        # Get file metadata
        # head = s3.head_object(Bucket=bucket, Key=key)
        # print(f"Head content is: {head}")
        # content_type = head.get('ContentType')
        
        # if not content_type or content_type == "binary/octet-stream":
        #     # Fallback: guess based on file extension
        #     content_type, _ = mimetypes.guess_type(key)

        # print(f"Detected content type: {content_type}")
        
        # queue_url = QUEUE_MAP.get(content_type)
        
        # if queue_url:
        #     message = {
        #         'bucket': bucket,
        #         'key': key,
        #         'type': content_type
        #     }
        #     sqs.send_message(
        #         QueueUrl=queue_url,
        #         MessageBody=json.dumps(message)
        #     )
        #     print(f"Sent message to queue: {queue_url}")
        # else:
        #     print(f"Unknown or unsupported file type: {content_type}")
