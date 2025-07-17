import boto3
import os
import json
import uuid
from botocore.exceptions import ClientError
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# ENV VARS you should set in Lambda config
BUCKET_NAME = os.environ['BUCKET_NAME']
DDB_TABLE_NAME = os.environ['DDB_TABLE_NAME']

def lambda_handler(event, context):
    query_params = event.get('queryStringParameters') or {}
    original_filename = query_params.get('filename')
    user_id = query_params.get('userId')

    if not original_filename or not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing filename or userId'})
        }

    file_extension = original_filename.split('.')[-1]
    base_name = '.'.join(original_filename.split('.')[:-1]) or "file"

    # Generate a UUID and build a unique file name
    file_id = str(uuid.uuid4())
    unique_filename = f"{base_name}--{file_id}.{file_extension}"
    s3_key = f"uploads/{unique_filename}"

    # Check if file already exists (extremely rare, but can be kept)
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=s3_key)
        return {
            'statusCode': 409,
            'body': json.dumps({'error': 'File with generated name already exists. Try again.'})
        }
    except ClientError as e:
        if e.response['Error']['Code'] != "404":
            raise  # other error, bubble up

    # Put record in DynamoDB
    table = dynamodb.Table(DDB_TABLE_NAME)
    table.put_item(
        Item={
            'FileID': unique_filename,
            'UserID': user_id,
            'OriginalFilename': original_filename,
            'S3Key': s3_key,
            'Status': 'uploading',
            'CreatedAt': datetime.utcnow().isoformat()
        }
    )

    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=300,
        HttpMethod='PUT'
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'upload_url': presigned_url,
            'fileId': file_id,
            'unique_filename': unique_filename
        })
    }
