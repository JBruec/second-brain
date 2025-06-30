from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime
import logging
import os
import aiofiles
import asyncio
from bson import ObjectId
import mimetypes

from app.models.document import DocumentCreate, DocumentUpdate, Document, DocumentInDB, DocumentType, DocumentProcessingStatus
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.database import MongoDB
from app.core.memory_store import MemoryStore
from app.core.config import settings
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

def get_document_type_from_mime(mime_type: str) -> DocumentType:
    """Determine document type from MIME type"""
    mime_mapping = {
        "text/plain": DocumentType.TEXT,
        "application/pdf": DocumentType.PDF,
        "application/msword": DocumentType.WORD,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.WORD,
        "application/vnd.ms-excel": DocumentType.EXCEL,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.EXCEL,
        "application/vnd.ms-powerpoint": DocumentType.POWERPOINT,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.POWERPOINT,
        "image/jpeg": DocumentType.IMAGE,
        "image/png": DocumentType.IMAGE,
        "image/gif": DocumentType.IMAGE,
        "audio/mpeg": DocumentType.AUDIO,
        "audio/wav": DocumentType.AUDIO,
        "video/mp4": DocumentType.VIDEO,
        "video/avi": DocumentType.VIDEO,
    }
    return mime_mapping.get(mime_type, DocumentType.OTHER)

@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated tags
    current_user: User = Depends(get_current_user)
):
    """Upload a document file"""
    try:
        # Validate file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
            )
        
        # Create upload directory if it doesn't exist
        upload_dir = f"{settings.upload_dir}/{current_user.id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Determine MIME type and document type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        document_type = get_document_type_from_mime(mime_type or "")
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Create document record
        collection = MongoDB.get_collection("documents")
        
        document_doc = DocumentInDB(
            title=title or file.filename,
            file_path=file_path,
            file_size=file.size,
            mime_type=mime_type,
            document_type=document_type,
            tags=tag_list,
            user_id=current_user.id,
            project_id=project_id
        )
        
        # Insert document
        result = await collection.insert_one(document_doc.dict(by_alias=True, exclude={"id"}))
        document_id = str(result.inserted_id)
        
        # Start background processing
        asyncio.create_task(process_document_background(document_id, file_path))
        
        # Get the created document
        created_doc = await collection.find_one({"_id": result.inserted_id})
        
        logger.info(f"Document uploaded: {file.filename} by {current_user.username}")
        
        return Document(
            id=str(created_doc["_id"]),
            title=created_doc["title"],
            content=created_doc.get("content"),
            file_path=created_doc.get("file_path"),
            file_size=created_doc.get("file_size"),
            mime_type=created_doc.get("mime_type"),
            document_type=created_doc["document_type"],
            tags=created_doc.get("tags", []),
            user_id=created_doc["user_id"],
            project_id=created_doc.get("project_id"),
            word_count=created_doc.get("word_count", 0),
            processed=created_doc.get("processed", False),
            entities=created_doc.get("entities", []),
            created_at=created_doc["created_at"],
            updated_at=created_doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )

async def process_document_background(document_id: str, file_path: str):
    """Background task to process uploaded document"""
    try:
        # Process the document to extract text content
        processor = DocumentProcessor()
        content = await processor.extract_text(file_path)
        
        if content:
            # Count words
            word_count = len(content.split())
            
            # Add to memory store for entity extraction
            memory_result = await MemoryStore.add_memory(
                user_id="", # Will be populated from document
                content=content,
                metadata={"document_id": document_id, "source": "document"}
            )
            
            # Update document with processed content
            collection = MongoDB.get_collection("documents")
            await collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "content": content,
                        "word_count": word_count,
                        "processed": True,
                        "entities": memory_result.get("entities", []),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Document processed successfully: {document_id}")
        
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        # Mark as processing failed
        collection = MongoDB.get_collection("documents")
        await collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {"processed": False, "updated_at": datetime.utcnow()}}
        )

@router.post("/", response_model=Document)
async def create_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a text document"""
    try:
        collection = MongoDB.get_collection("documents")
        
        # Count words if content provided
        word_count = 0
        if document.content:
            word_count = len(document.content.split())
        
        # Create document
        document_doc = DocumentInDB(
            **document.dict(),
            user_id=current_user.id,
            word_count=word_count,
            processed=bool(document.content)  # Mark as processed if content provided
        )
        
        # Insert document
        result = await collection.insert_one(document_doc.dict(by_alias=True, exclude={"id"}))
        
        # Add to memory store if content exists
        if document.content:
            await MemoryStore.add_memory(
                user_id=current_user.id,
                content=document.content,
                metadata={"document_id": str(result.inserted_id), "source": "document"}
            )
        
        # Get created document
        created_doc = await collection.find_one({"_id": result.inserted_id})
        
        logger.info(f"Document created: {document.title} by {current_user.username}")
        
        return Document(
            id=str(created_doc["_id"]),
            title=created_doc["title"],
            content=created_doc.get("content"),
            file_path=created_doc.get("file_path"),
            file_size=created_doc.get("file_size"),
            mime_type=created_doc.get("mime_type"),
            document_type=created_doc["document_type"],
            tags=created_doc.get("tags", []),
            user_id=created_doc["user_id"],
            project_id=created_doc.get("project_id"),
            word_count=created_doc.get("word_count", 0),
            processed=created_doc.get("processed", False),
            entities=created_doc.get("entities", []),
            created_at=created_doc["created_at"],
            updated_at=created_doc["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Document creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document"
        )

@router.get("/", response_model=List[Document])
async def get_documents(
    skip: int = 0,
    limit: int = 50,
    project_id: Optional[str] = None,
    document_type: Optional[DocumentType] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get user's documents"""
    try:
        collection = MongoDB.get_collection("documents")
        
        # Build query
        query = {"user_id": current_user.id}
        
        if project_id:
            query["project_id"] = project_id
        
        if document_type:
            query["document_type"] = document_type
        
        if search:
            query["$text"] = {"$search": search}
        
        # Get documents
        cursor = collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        return [
            Document(
                id=str(doc["_id"]),
                title=doc["title"],
                content=doc.get("content"),
                file_path=doc.get("file_path"),
                file_size=doc.get("file_size"),
                mime_type=doc.get("mime_type"),
                document_type=doc["document_type"],
                tags=doc.get("tags", []),
                user_id=doc["user_id"],
                project_id=doc.get("project_id"),
                word_count=doc.get("word_count", 0),
                processed=doc.get("processed", False),
                entities=doc.get("entities", []),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"]
            )
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )

@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific document"""
    try:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID"
            )
        
        collection = MongoDB.get_collection("documents")
        doc = await collection.find_one({
            "_id": ObjectId(document_id),
            "user_id": current_user.id
        })
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return Document(
            id=str(doc["_id"]),
            title=doc["title"],
            content=doc.get("content"),
            file_path=doc.get("file_path"),
            file_size=doc.get("file_size"),
            mime_type=doc.get("mime_type"),
            document_type=doc["document_type"],
            tags=doc.get("tags", []),
            user_id=doc["user_id"],
            project_id=doc.get("project_id"),
            word_count=doc.get("word_count", 0),
            processed=doc.get("processed", False),
            entities=doc.get("entities", []),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve document"
        )

@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a document"""
    try:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID"
            )
        
        collection = MongoDB.get_collection("documents")
        
        # Check if document exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(document_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in document_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # Update word count if content changed
        if "content" in update_data and update_data["content"]:
            update_data["word_count"] = len(update_data["content"].split())
            
            # Add updated content to memory store
            await MemoryStore.add_memory(
                user_id=current_user.id,
                content=update_data["content"],
                metadata={"document_id": document_id, "source": "document_update"}
            )
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
        
        # Return updated document
        updated_doc = await collection.find_one({"_id": ObjectId(document_id)})
        
        logger.info(f"Document updated: {document_id} by {current_user.username}")
        
        return Document(
            id=str(updated_doc["_id"]),
            title=updated_doc["title"],
            content=updated_doc.get("content"),
            file_path=updated_doc.get("file_path"),
            file_size=updated_doc.get("file_size"),
            mime_type=updated_doc.get("mime_type"),
            document_type=updated_doc["document_type"],
            tags=updated_doc.get("tags", []),
            user_id=updated_doc["user_id"],
            project_id=updated_doc.get("project_id"),
            word_count=updated_doc.get("word_count", 0),
            processed=updated_doc.get("processed", False),
            entities=updated_doc.get("entities", []),
            created_at=updated_doc["created_at"],
            updated_at=updated_doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document"
        )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a document"""
    try:
        if not ObjectId.is_valid(document_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID"
            )
        
        collection = MongoDB.get_collection("documents")
        
        # Check if document exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(document_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete file if it exists
        if existing.get("file_path") and os.path.exists(existing["file_path"]):
            try:
                os.remove(existing["file_path"])
            except Exception as e:
                logger.warning(f"Failed to delete file {existing['file_path']}: {e}")
        
        # Delete document record
        await collection.delete_one({"_id": ObjectId(document_id)})
        
        logger.info(f"Document deleted: {document_id} by {current_user.username}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )