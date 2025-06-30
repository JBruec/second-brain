from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, date
import logging
from bson import ObjectId

from app.models.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEvent, CalendarEventInDB, CalendarSyncStatus
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.database import MongoDB
from app.services.apple_integration import AppleCalendarService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/events", response_model=CalendarEvent)
async def create_event(
    event: CalendarEventCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new calendar event"""
    try:
        collection = MongoDB.get_collection("calendar_events")
        
        # Create event document
        event_doc = CalendarEventInDB(
            **event.dict(),
            user_id=current_user.id
        )
        
        # Insert event
        result = await collection.insert_one(event_doc.dict(by_alias=True, exclude={"id"}))
        
        # Sync with Apple Calendar if enabled
        apple_service = AppleCalendarService()
        try:
            apple_event_id = await apple_service.create_event(event_doc)
            if apple_event_id:
                await collection.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"apple_event_id": apple_event_id, "synced_at": datetime.utcnow()}}
                )
        except Exception as e:
            logger.warning(f"Failed to sync with Apple Calendar: {e}")
        
        # Get created event
        created_doc = await collection.find_one({"_id": result.inserted_id})
        
        logger.info(f"Calendar event created: {event.title} by {current_user.username}")
        
        return CalendarEvent(
            id=str(created_doc["_id"]),
            title=created_doc["title"],
            description=created_doc.get("description"),
            start_date=created_doc["start_date"],
            end_date=created_doc["end_date"],
            location=created_doc.get("location"),
            attendees=created_doc.get("attendees", []),
            all_day=created_doc.get("all_day", False),
            user_id=created_doc["user_id"],
            project_id=created_doc.get("project_id"),
            status=created_doc["status"],
            apple_event_id=created_doc.get("apple_event_id"),
            recurrence_type=created_doc["recurrence_type"],
            recurrence_end=created_doc.get("recurrence_end"),
            created_at=created_doc["created_at"],
            updated_at=created_doc["updated_at"],
            synced_at=created_doc.get("synced_at")
        )
        
    except Exception as e:
        logger.error(f"Calendar event creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create calendar event"
        )

@router.get("/events", response_model=List[CalendarEvent])
async def get_events(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    project_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get calendar events"""
    try:
        collection = MongoDB.get_collection("calendar_events")
        
        # Build query
        query = {"user_id": current_user.id}
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = datetime.combine(start_date, datetime.min.time())
            if end_date:
                date_query["$lte"] = datetime.combine(end_date, datetime.max.time())
            query["start_date"] = date_query
        
        if project_id:
            query["project_id"] = project_id
        
        # Get events
        cursor = collection.find(query).sort("start_date", 1).skip(skip).limit(limit)
        events = await cursor.to_list(length=limit)
        
        return [
            CalendarEvent(
                id=str(doc["_id"]),
                title=doc["title"],
                description=doc.get("description"),
                start_date=doc["start_date"],
                end_date=doc["end_date"],
                location=doc.get("location"),
                attendees=doc.get("attendees", []),
                all_day=doc.get("all_day", False),
                user_id=doc["user_id"],
                project_id=doc.get("project_id"),
                status=doc["status"],
                apple_event_id=doc.get("apple_event_id"),
                recurrence_type=doc["recurrence_type"],
                recurrence_end=doc.get("recurrence_end"),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
                synced_at=doc.get("synced_at")
            )
            for doc in events
        ]
        
    except Exception as e:
        logger.error(f"Failed to get calendar events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar events"
        )

@router.get("/events/{event_id}", response_model=CalendarEvent)
async def get_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific calendar event"""
    try:
        if not ObjectId.is_valid(event_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event ID"
            )
        
        collection = MongoDB.get_collection("calendar_events")
        doc = await collection.find_one({
            "_id": ObjectId(event_id),
            "user_id": current_user.id
        })
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        return CalendarEvent(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc.get("description"),
            start_date=doc["start_date"],
            end_date=doc["end_date"],
            location=doc.get("location"),
            attendees=doc.get("attendees", []),
            all_day=doc.get("all_day", False),
            user_id=doc["user_id"],
            project_id=doc.get("project_id"),
            status=doc["status"],
            apple_event_id=doc.get("apple_event_id"),
            recurrence_type=doc["recurrence_type"],
            recurrence_end=doc.get("recurrence_end"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            synced_at=doc.get("synced_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve calendar event"
        )

@router.put("/events/{event_id}", response_model=CalendarEvent)
async def update_event(
    event_id: str,
    event_update: CalendarEventUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a calendar event"""
    try:
        if not ObjectId.is_valid(event_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event ID"
            )
        
        collection = MongoDB.get_collection("calendar_events")
        
        # Check if event exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(event_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in event_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await collection.update_one(
                {"_id": ObjectId(event_id)},
                {"$set": update_data}
            )
            
            # Sync with Apple Calendar if enabled
            apple_service = AppleCalendarService()
            try:
                if existing.get("apple_event_id"):
                    await apple_service.update_event(existing["apple_event_id"], update_data)
                    update_data["synced_at"] = datetime.utcnow()
                    await collection.update_one(
                        {"_id": ObjectId(event_id)},
                        {"$set": {"synced_at": update_data["synced_at"]}}
                    )
            except Exception as e:
                logger.warning(f"Failed to sync update with Apple Calendar: {e}")
        
        # Return updated event
        updated_doc = await collection.find_one({"_id": ObjectId(event_id)})
        
        logger.info(f"Calendar event updated: {event_id} by {current_user.username}")
        
        return CalendarEvent(
            id=str(updated_doc["_id"]),
            title=updated_doc["title"],
            description=updated_doc.get("description"),
            start_date=updated_doc["start_date"],
            end_date=updated_doc["end_date"],
            location=updated_doc.get("location"),
            attendees=updated_doc.get("attendees", []),
            all_day=updated_doc.get("all_day", False),
            user_id=updated_doc["user_id"],
            project_id=updated_doc.get("project_id"),
            status=updated_doc["status"],
            apple_event_id=updated_doc.get("apple_event_id"),
            recurrence_type=updated_doc["recurrence_type"],
            recurrence_end=updated_doc.get("recurrence_end"),
            created_at=updated_doc["created_at"],
            updated_at=updated_doc["updated_at"],
            synced_at=updated_doc.get("synced_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update calendar event"
        )

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a calendar event"""
    try:
        if not ObjectId.is_valid(event_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid event ID"
            )
        
        collection = MongoDB.get_collection("calendar_events")
        
        # Check if event exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(event_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Calendar event not found"
            )
        
        # Delete from Apple Calendar if synced
        if existing.get("apple_event_id"):
            apple_service = AppleCalendarService()
            try:
                await apple_service.delete_event(existing["apple_event_id"])
            except Exception as e:
                logger.warning(f"Failed to delete from Apple Calendar: {e}")
        
        # Delete event
        await collection.delete_one({"_id": ObjectId(event_id)})
        
        logger.info(f"Calendar event deleted: {event_id} by {current_user.username}")
        
        return {"message": "Calendar event deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete calendar event"
        )

@router.post("/sync")
async def sync_calendar(
    current_user: User = Depends(get_current_user)
):
    """Sync with Apple Calendar"""
    try:
        apple_service = AppleCalendarService()
        result = await apple_service.sync_calendar(current_user.id)
        
        logger.info(f"Calendar sync completed for user {current_user.username}")
        
        return result
        
    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync calendar"
        )

@router.get("/sync/status", response_model=CalendarSyncStatus)
async def get_sync_status(
    current_user: User = Depends(get_current_user)
):
    """Get calendar sync status"""
    try:
        # This would typically be stored in a sync status collection
        # For now, return a basic status
        return CalendarSyncStatus(
            user_id=current_user.id,
            sync_status="not_implemented",
            error_message="Apple Calendar sync not fully implemented yet"
        )
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync status"
        )