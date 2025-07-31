# from sentence_transformers import SentenceTransformer
# import numpy as np
# import faiss
# from typing import List, Dict, Tuple

# embedder = SentenceTransformer('all-MiniLM-L6-v2')

# # Embed a list of chunk dicts (using 'content' field)
# def embed_chunks(chunks: List[Dict]) -> np.ndarray:
#     texts = [chunk['content'] for chunk in chunks]
#     embeddings = embedder.encode(texts, convert_to_numpy=True)
#     return embeddings

# # Build a FAISS index from embeddings
# def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatL2:
#     dim = embeddings.shape[1]
#     index = faiss.IndexFlatL2(dim)
#     index.add(embeddings)
#     return index

# # Search FAISS index for top-k similar chunks
# def search_faiss_index(index: faiss.IndexFlatL2, query_embedding: np.ndarray, k: int = 3) -> List[int]:
#     D, I = index.search(query_embedding, k)
#     return I[0].tolist() 

import os
import json
import boto3
import uuid
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np
from opensearchpy import OpenSearch, RequestsHttpConnection

# --- Config ---
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
OPENSEARCH_HOST = os.environ['OPENSEARCH_HOST']  # e.g. https://search-my-domain.us-east-1.es.amazonaws.com
INDEX_NAME = os.environ.get('OPENSEARCH_INDEX', 'semantic-chunks')
REGION = os.environ.get('AWS_REGION', 'us-east-1')

# --- AWS Clients ---
sqs = boto3.client('sqs')
s3 = boto3.client('s3')

# --- Embedder ---
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# --- OpenSearch Client ---
opensearch = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST.replace("https://", ""), 'port': 443}],
    http_auth=(os.environ['OS_USER'], os.environ['OS_PASS']),
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

# --- Utility Functions ---

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

def download_chunks_from_s3(bucket: str, key: str) -> List[Dict]:
    obj = s3.get_object(Bucket=bucket, Key=key)
    chunks = json.loads(obj['Body'].read().decode('utf-8'))
    return chunks

def embed_chunks(chunks: List[Dict]) -> np.ndarray:
    texts = [chunk['content'] for chunk in chunks]
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    return embeddings

def index_chunks(chunks: List[Dict], embeddings: np.ndarray):
    for chunk, embed in zip(chunks, embeddings):
        doc_id = chunk['id']
        doc = {
            "title": chunk.get("title"),
            "description": chunk.get("description"),
            "tags": chunk.get("tags", []),
            "pageIndex": chunk.get("pageIndex", 0),
            "content": chunk["content"],
            "embedding": embed.tolist(),  # Must convert np.array to list
        }
        opensearch.index(index=INDEX_NAME, id=doc_id, body=doc)
        print(f"✅ Indexed chunk: {doc_id}")

def delete_sqs_message(receipt_handle):
    sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)

def ensure_index_exists():
    if not opensearch.indices.exists(index=INDEX_NAME):
        print(f"🔧 Creating OpenSearch index: {INDEX_NAME}")
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 2
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "description": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "content": {"type": "text"},
                    "pageIndex": {"type": "integer"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 384  # for all-MiniLM-L6-v2
                    }
                }
            }
        }
        opensearch.indices.create(index=INDEX_NAME, body=index_body)
        print("✅ Index created.")

# --- Main ---

def process_sqs_messages():
    ensure_index_exists()
    messages = get_sqs_messages()
    if not messages:
        print("No messages in queue.")
        return

    for msg in messages:
        try:
            bucket, key = parse_s3_event(msg['Body'])
            print(f"\n📄 Processing: s3://{bucket}/{key}")

            chunks = download_chunks_from_s3(bucket, key)
            embeddings = embed_chunks(chunks)
            index_chunks(chunks, embeddings)

            delete_sqs_message(msg['ReceiptHandle'])
            print("✅ SQS message processed.")

        except Exception as e:
            print(f"❌ Error: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    process_sqs_messages()
