from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId
from enum import Enum

class DocumentType(str, Enum):
    TEXT = "text"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"

class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = None  # Extracted text content
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    document_type: DocumentType = DocumentType.TEXT
    tags: List[str] = Field(default_factory=list)
    
class DocumentCreate(DocumentBase):
    project_id: Optional[str] = None

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    project_id: Optional[str] = None

class DocumentInDB(DocumentBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    project_id: Optional[str] = None
    word_count: int = 0
    processed: bool = False  # Whether content has been processed for memories
    embedding: Optional[List[float]] = None  # Vector embedding
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Document(DocumentBase):
    id: str
    user_id: str
    project_id: Optional[str]
    word_count: int
    processed: bool
    entities: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

class DocumentProcessingStatus(BaseModel):
    document_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int = 0  # 0-100
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None