import os
import boto3
import json
import uuid
import spacy
from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import List, Dict
from bs4 import BeautifulSoup

# --- Load models once ---
nlp = spacy.load('en_core_web_sm')
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# --- AWS Clients ---
sqs = boto3.client('sqs')
s3 = boto3.client('s3')

# --- Config ---
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

# --- Semantic Chunking Functions ---

def extract_tags(text: str, top_n: int = 3) -> List[str]:
    doc = nlp(text)
    tags = [token.lemma_ for token in doc if token.pos_ == 'NOUN']
    return list(dict.fromkeys(tags))[:top_n]

def generate_title(text: str) -> str:
    doc = nlp(text)
    if doc.sents:
        first_sent = next(doc.sents).text.strip()
        return first_sent[:80]
    return ' '.join(text.split()[:8])

def generate_description(text: str) -> str:
    doc = nlp(text)
    sents = list(doc.sents)
    return ' '.join([s.text.strip() for s in sents[:2]])

def chunk_text_semantic(text: str, max_chunk_size: int = 500) -> List[Dict]:
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    embeddings = embedder.encode(paragraphs)
    chunks = []
    current_chunk = ''
    current_embeds = []
    page_index = 1
    for i, para in enumerate(paragraphs):
        if not current_chunk:
            current_chunk = para
            current_embeds = [embeddings[i]]
        else:
            sim = util.cos_sim(np.mean(current_embeds, axis=0), embeddings[i]).item()
            if len(current_chunk) < max_chunk_size and sim > 0.6:
                current_chunk += '\n' + para
                current_embeds.append(embeddings[i])
            else:
                chunk_text = current_chunk.strip()
                chunks.append({
                    'id': str(uuid.uuid4()),
                    'title': generate_title(chunk_text),
                    'description': generate_description(chunk_text),
                    'tags': extract_tags(chunk_text),
                    'pageIndex': page_index,
                    'content': chunk_text,
                })
                page_index += 1
                current_chunk = para
                current_embeds = [embeddings[i]]
    if current_chunk:
        chunk_text = current_chunk.strip()
        chunks.append({
            'id': str(uuid.uuid4()),
            'title': generate_title(chunk_text),
            'description': generate_description(chunk_text),
            'tags': extract_tags(chunk_text),
            'pageIndex': page_index,
            'content': chunk_text,
        })
    return chunks

# --- AWS Integration Functions ---

def get_sqs_messages(max_messages=5):
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=10
    )
    return response.get('Messages', [])

def parse_s3_event(msg_body):
    body = json.loads(msg_body)
    record = body['Records'][0]
    bucket = record['s3']['bucket']['name']
    key = record['s3']['object']['key']
    return bucket, key

def get_file_from_s3(bucket: str, key: str) -> str:
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj['Body'].read().decode('utf-8')
    return content

def extract_text(content: str, content_type: str = 'text/plain') -> str:
    if content_type == 'text/html':
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(separator='\n')
    return content

def delete_sqs_message(receipt_handle):
    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)

def extract_doc_id_from_key(key: str) -> str:
    # Example: uploads/documents/mydoc.docx.txt → mydoc
    filename = key.split('/')[-1]
    return filename.split('.')[0]

def store_chunks_to_s3(bucket: str, doc_id: str, chunks: List[Dict]):
    output_key = f"semantic-chunks/{doc_id}.json"
    body = json.dumps(chunks, indent=2)
    s3.put_object(Bucket=bucket, Key=output_key, Body=body.encode('utf-8'))
    print(f"✅ Stored semantic chunks to s3://{bucket}/{output_key}")

# --- Main Processor ---

def process_sqs_messages():
    messages = get_sqs_messages()
    if not messages:
        print("No messages in queue.")
        return

    for msg in messages:
        try:
            bucket, key = parse_s3_event(msg['Body'])
            print(f"\n📄 Processing: s3://{bucket}/{key}")

            content = get_file_from_s3(bucket, key)
            content_type = 'text/html' if key.endswith('.html') else 'text/plain'
            cleaned = extract_text(content, content_type)

            chunks = chunk_text_semantic(cleaned)
            doc_id = extract_doc_id_from_key(key)

            # Add documentId to each chunk
            for chunk in chunks:
                chunk["documentId"] = doc_id

            # Store chunks to S3
            store_chunks_to_s3(bucket, doc_id, chunks)

            delete_sqs_message(msg['ReceiptHandle'])
            print("✅ Message processed and deleted from SQS.")

        except Exception as e:
            print(f"❌ Error processing message: {e}")

# --- Entry Point ---

if __name__ == "__main__":
    process_sqs_messages()
