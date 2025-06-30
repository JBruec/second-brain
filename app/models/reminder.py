from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId
from enum import Enum

class ReminderPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ReminderStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ReminderBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: ReminderPriority = ReminderPriority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    
class ReminderCreate(ReminderBase):
    project_id: Optional[str] = None
    related_document_id: Optional[str] = None

class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[ReminderPriority] = None
    tags: Optional[List[str]] = None
    status: Optional[ReminderStatus] = None
    completed_at: Optional[datetime] = None

class ReminderInDB(ReminderBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    project_id: Optional[str] = None
    related_document_id: Optional[str] = None
    status: ReminderStatus = ReminderStatus.PENDING
    apple_reminder_id: Optional[str] = None  # ID from Apple Reminders
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    synced_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class Reminder(ReminderBase):
    id: str
    user_id: str
    project_id: Optional[str]
    related_document_id: Optional[str]
    status: ReminderStatus
    apple_reminder_id: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime]

class ReminderSyncStatus(BaseModel):
    user_id: str
    last_sync: Optional[datetime] = None
    sync_status: str = "not_synced"  # "synced", "syncing", "error", "not_synced"
    error_message: Optional[str] = None
    reminders_synced: int = 0

class ReminderList(BaseModel):
    name: str
    apple_list_id: Optional[str] = None
    color: Optional[str] = "#3498db"
    reminders: List[Reminder] = Field(default_factory=list)