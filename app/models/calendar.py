from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from .user import PyObjectId
from enum import Enum

class EventStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

class RecurrenceType(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)  # Email addresses
    all_day: bool = False
    
class CalendarEventCreate(CalendarEventBase):
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_end: Optional[datetime] = None
    project_id: Optional[str] = None

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    all_day: Optional[bool] = None
    status: Optional[EventStatus] = None

class CalendarEventInDB(CalendarEventBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    project_id: Optional[str] = None
    status: EventStatus = EventStatus.PENDING
    apple_event_id: Optional[str] = None  # ID from Apple Calendar
    recurrence_type: RecurrenceType = RecurrenceType.NONE
    recurrence_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    synced_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class CalendarEvent(CalendarEventBase):
    id: str
    user_id: str
    project_id: Optional[str]
    status: EventStatus
    apple_event_id: Optional[str]
    recurrence_type: RecurrenceType
    recurrence_end: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime]

class CalendarSyncStatus(BaseModel):
    user_id: str
    last_sync: Optional[datetime] = None
    sync_status: str = "not_synced"  # "synced", "syncing", "error", "not_synced"
    error_message: Optional[str] = None
    events_synced: int = 0