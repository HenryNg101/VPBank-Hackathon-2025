from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from minio import Minio
from .database import init_models, get_db
from .models import Document

import uuid
import os
import io

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_models()

host_name = "localhost"

minio_client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    
    # endpoint=f"{host_name}:9000",
    # access_key="minioadmin",
    # secret_key="minioadmin",
    secure=False
)

# BUCKET_NAME = "raw-files"

if not minio_client.bucket_exists(bucket_name=os.getenv("MINIO_BUCKET")):
    minio_client.make_bucket(bucket_name=os.getenv("MINIO_BUCKET"))

# In-memory document status storage (replace with DB later)
DOCUMENT_STATUS = {}

UPLOAD_DIR = "storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_file(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    document_id = uuid.uuid4()
    file_bytes = await file.read()

    object_name = f"{document_id}_{file.filename}"

    # Upload to MinIO
    minio_client.put_object(
        bucket_name=os.getenv("MINIO_BUCKET"),
        object_name=object_name,
        data=io.BytesIO(file_bytes),
        length=len(file_bytes)
    )

    # --- INSERT INTO DATABASE ---
    new_document = Document(
        id=document_id,
        user_id=user_id,
        filename=file.filename,
        file_type=file.content_type,
        status="uploaded",
    )

    db.add(new_document)
    await db.commit()
    await db.refresh(new_document)

    return {
        "document_id": str(new_document.id),
        "status": new_document.status,
        "filename": new_document.filename,
        "stored_as": object_name
    }


@app.post("/query")
async def handle_query(document_id: str, query: str):
    """
    Add your logic here to process queries on documents.
    Example: Searching text, calling ML models, etc.
    """

    if document_id not in DOCUMENT_STATUS:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update status
    DOCUMENT_STATUS[document_id]["status"] = "processing_query"

    # Dummy response (replace with actual logic)
    result = {
        "document_id": document_id,
        "query": query,
        "response": f"Dummy response for query: '{query}'",
    }

    # Mark as ready
    DOCUMENT_STATUS[document_id]["status"] = "query_completed"

    return result


@app.get("/status/{document_id}")
async def get_status(document_id: str):
    if document_id not in DOCUMENT_STATUS:
        raise HTTPException(status_code=404, detail="Document not found")

    return DOCUMENT_STATUS[document_id]