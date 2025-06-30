from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId

class ProjectBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    instructions: Optional[str] = None  # Project-specific AI instructions
    tags: List[str] = Field(default_factory=list)
    color: Optional[str] = "#3498db"  # Hex color for UI
    
class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    is_archived: Optional[bool] = None

class ProjectInDB(ProjectBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    is_archived: bool = False
    document_count: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Project(ProjectBase):
    id: str
    user_id: str
    is_archived: bool
    document_count: int
    last_activity: datetime
    created_at: datetime
    updated_at: datetime

class ProjectStats(BaseModel):
    project_id: str
    document_count: int
    total_words: int
    last_modified: datetime
    most_active_day: Optional[str] = None