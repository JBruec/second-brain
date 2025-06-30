from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, date
import logging
from bson import ObjectId

from app.models.reminder import ReminderCreate, ReminderUpdate, Reminder, ReminderInDB, ReminderSyncStatus, ReminderPriority, ReminderStatus
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.database import MongoDB
from app.services.apple_integration import AppleRemindersService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Reminder)
async def create_reminder(
    reminder: ReminderCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new reminder"""
    try:
        collection = MongoDB.get_collection("reminders")
        
        # Create reminder document
        reminder_doc = ReminderInDB(
            **reminder.dict(),
            user_id=current_user.id
        )
        
        # Insert reminder
        result = await collection.insert_one(reminder_doc.dict(by_alias=True, exclude={"id"}))
        
        # Sync with Apple Reminders if enabled
        apple_service = AppleRemindersService()
        try:
            apple_reminder_id = await apple_service.create_reminder(reminder_doc)
            if apple_reminder_id:
                await collection.update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"apple_reminder_id": apple_reminder_id, "synced_at": datetime.utcnow()}}
                )
        except Exception as e:
            logger.warning(f"Failed to sync with Apple Reminders: {e}")
        
        # Get created reminder
        created_doc = await collection.find_one({"_id": result.inserted_id})
        
        logger.info(f"Reminder created: {reminder.title} by {current_user.username}")
        
        return Reminder(
            id=str(created_doc["_id"]),
            title=created_doc["title"],
            description=created_doc.get("description"),
            due_date=created_doc.get("due_date"),
            priority=created_doc["priority"],
            tags=created_doc.get("tags", []),
            user_id=created_doc["user_id"],
            project_id=created_doc.get("project_id"),
            related_document_id=created_doc.get("related_document_id"),
            status=created_doc["status"],
            apple_reminder_id=created_doc.get("apple_reminder_id"),
            completed_at=created_doc.get("completed_at"),
            created_at=created_doc["created_at"],
            updated_at=created_doc["updated_at"],
            synced_at=created_doc.get("synced_at")
        )
        
    except Exception as e:
        logger.error(f"Reminder creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reminder"
        )

@router.get("/", response_model=List[Reminder])
async def get_reminders(
    status: Optional[ReminderStatus] = None,
    priority: Optional[ReminderPriority] = None,
    project_id: Optional[str] = None,
    due_before: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get reminders"""
    try:
        collection = MongoDB.get_collection("reminders")
        
        # Build query
        query = {"user_id": current_user.id}
        
        if status:
            query["status"] = status
        
        if priority:
            query["priority"] = priority
        
        if project_id:
            query["project_id"] = project_id
        
        if due_before:
            query["due_date"] = {"$lte": datetime.combine(due_before, datetime.max.time())}
        
        # Get reminders
        cursor = collection.find(query).sort("due_date", 1).skip(skip).limit(limit)
        reminders = await cursor.to_list(length=limit)
        
        return [
            Reminder(
                id=str(doc["_id"]),
                title=doc["title"],
                description=doc.get("description"),
                due_date=doc.get("due_date"),
                priority=doc["priority"],
                tags=doc.get("tags", []),
                user_id=doc["user_id"],
                project_id=doc.get("project_id"),
                related_document_id=doc.get("related_document_id"),
                status=doc["status"],
                apple_reminder_id=doc.get("apple_reminder_id"),
                completed_at=doc.get("completed_at"),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"],
                synced_at=doc.get("synced_at")
            )
            for doc in reminders
        ]
        
    except Exception as e:
        logger.error(f"Failed to get reminders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reminders"
        )

@router.get("/{reminder_id}", response_model=Reminder)
async def get_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific reminder"""
    try:
        if not ObjectId.is_valid(reminder_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reminder ID"
            )
        
        collection = MongoDB.get_collection("reminders")
        doc = await collection.find_one({
            "_id": ObjectId(reminder_id),
            "user_id": current_user.id
        })
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found"
            )
        
        return Reminder(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc.get("description"),
            due_date=doc.get("due_date"),
            priority=doc["priority"],
            tags=doc.get("tags", []),
            user_id=doc["user_id"],
            project_id=doc.get("project_id"),
            related_document_id=doc.get("related_document_id"),
            status=doc["status"],
            apple_reminder_id=doc.get("apple_reminder_id"),
            completed_at=doc.get("completed_at"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            synced_at=doc.get("synced_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reminder"
        )

@router.put("/{reminder_id}", response_model=Reminder)
async def update_reminder(
    reminder_id: str,
    reminder_update: ReminderUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a reminder"""
    try:
        if not ObjectId.is_valid(reminder_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reminder ID"
            )
        
        collection = MongoDB.get_collection("reminders")
        
        # Check if reminder exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(reminder_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in reminder_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # Handle completion
        if update_data.get("status") == ReminderStatus.COMPLETED and not existing.get("completed_at"):
            update_data["completed_at"] = datetime.utcnow()
        elif update_data.get("status") != ReminderStatus.COMPLETED:
            update_data["completed_at"] = None
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await collection.update_one(
                {"_id": ObjectId(reminder_id)},
                {"$set": update_data}
            )
            
            # Sync with Apple Reminders if enabled
            apple_service = AppleRemindersService()
            try:
                if existing.get("apple_reminder_id"):
                    await apple_service.update_reminder(existing["apple_reminder_id"], update_data)
                    update_data["synced_at"] = datetime.utcnow()
                    await collection.update_one(
                        {"_id": ObjectId(reminder_id)},
                        {"$set": {"synced_at": update_data["synced_at"]}}
                    )
            except Exception as e:
                logger.warning(f"Failed to sync update with Apple Reminders: {e}")
        
        # Return updated reminder
        updated_doc = await collection.find_one({"_id": ObjectId(reminder_id)})
        
        logger.info(f"Reminder updated: {reminder_id} by {current_user.username}")
        
        return Reminder(
            id=str(updated_doc["_id"]),
            title=updated_doc["title"],
            description=updated_doc.get("description"),
            due_date=updated_doc.get("due_date"),
            priority=updated_doc["priority"],
            tags=updated_doc.get("tags", []),
            user_id=updated_doc["user_id"],
            project_id=updated_doc.get("project_id"),
            related_document_id=updated_doc.get("related_document_id"),
            status=updated_doc["status"],
            apple_reminder_id=updated_doc.get("apple_reminder_id"),
            completed_at=updated_doc.get("completed_at"),
            created_at=updated_doc["created_at"],
            updated_at=updated_doc["updated_at"],
            synced_at=updated_doc.get("synced_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reminder"
        )

@router.delete("/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a reminder"""
    try:
        if not ObjectId.is_valid(reminder_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reminder ID"
            )
        
        collection = MongoDB.get_collection("reminders")
        
        # Check if reminder exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(reminder_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found"
            )
        
        # Delete from Apple Reminders if synced
        if existing.get("apple_reminder_id"):
            apple_service = AppleRemindersService()
            try:
                await apple_service.delete_reminder(existing["apple_reminder_id"])
            except Exception as e:
                logger.warning(f"Failed to delete from Apple Reminders: {e}")
        
        # Delete reminder
        await collection.delete_one({"_id": ObjectId(reminder_id)})
        
        logger.info(f"Reminder deleted: {reminder_id} by {current_user.username}")
        
        return {"message": "Reminder deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reminder"
        )

@router.post("/{reminder_id}/complete", response_model=Reminder)
async def complete_reminder(
    reminder_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a reminder as completed"""
    try:
        return await update_reminder(
            reminder_id,
            ReminderUpdate(status=ReminderStatus.COMPLETED),
            current_user
        )
        
    except Exception as e:
        logger.error(f"Failed to complete reminder: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete reminder"
        )

@router.post("/sync")
async def sync_reminders(
    current_user: User = Depends(get_current_user)
):
    """Sync with Apple Reminders"""
    try:
        apple_service = AppleRemindersService()
        result = await apple_service.sync_reminders(current_user.id)
        
        logger.info(f"Reminders sync completed for user {current_user.username}")
        
        return result
        
    except Exception as e:
        logger.error(f"Reminders sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync reminders"
        )

@router.get("/sync/status", response_model=ReminderSyncStatus)
async def get_sync_status(
    current_user: User = Depends(get_current_user)
):
    """Get reminders sync status"""
    try:
        # This would typically be stored in a sync status collection
        # For now, return a basic status
        return ReminderSyncStatus(
            user_id=current_user.id,
            sync_status="not_implemented",
            error_message="Apple Reminders sync not fully implemented yet"
        )
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sync status"
        )