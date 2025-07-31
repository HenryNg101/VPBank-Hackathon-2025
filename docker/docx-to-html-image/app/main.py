import boto3
import json
import os
import subprocess
import time

sqs = boto3.client('sqs')
s3 = boto3.client('s3')

# Set these from env
QUEUE_URL = os.environ["SQS_QUEUE_URL"]
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "")  # Optional

def process_message(msg):
    body = json.loads(msg["Body"])

    bucket = body["bucket"]
    key = body["key"]

    filename = key.split("/")[-1]
    local_docx = f"/tmp/{filename}"
    local_html = local_docx.replace(".docx", ".html")

    # Download DOCX from S3
    s3.download_file(bucket, key, local_docx)

    # Run pandoc
    try:
        subprocess.run([
            "pandoc", local_docx,
            "-f", "docx", "-t", "html",
            "-o", local_html
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Pandoc failed: {e}")
        return

    print(f"[INFO] Converted {filename} to HTML.")

    # Optional: Upload HTML result back to S3
    if OUTPUT_BUCKET:
        output_key = key.replace(".docx", ".html")
        s3.upload_file(local_html, OUTPUT_BUCKET, output_key)
        print(f"[INFO] Uploaded {output_key} to {OUTPUT_BUCKET}")

    # Cleanup
    os.remove(local_docx)
    os.remove(local_html)

def poll_sqs():
    while True:
        messages = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10
        ).get("Messages", [])

        for msg in messages:
            try:
                process_message(msg)
                # Delete the message after successful processing
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg["ReceiptHandle"]
                )
            except Exception as e:
                print(f"[ERROR] Failed to process message: {e}")

        time.sleep(1)

if __name__ == "__main__":
    poll_sqs()
