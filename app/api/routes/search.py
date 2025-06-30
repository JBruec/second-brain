from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.database import MongoDB
from app.core.memory_store import MemoryStore

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def unified_search(
    query: str,
    search_type: Optional[str] = "all",  # "all", "documents", "projects", "events", "reminders", "memories"
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Unified search across all content types"""
    try:
        results = {}
        
        if search_type in ["all", "documents"]:
            results["documents"] = await search_documents(query, current_user.id, limit)
        
        if search_type in ["all", "projects"]:
            results["projects"] = await search_projects(query, current_user.id, limit)
        
        if search_type in ["all", "events"]:
            results["events"] = await search_calendar_events(query, current_user.id, limit)
        
        if search_type in ["all", "reminders"]:
            results["reminders"] = await search_reminders(query, current_user.id, limit)
        
        if search_type in ["all", "memories"]:
            results["memories"] = await search_memories(query, current_user.id, limit)
        
        # Calculate total results
        total_results = sum(len(results.get(key, [])) for key in results)
        
        return {
            "query": query,
            "search_type": search_type,
            "total_results": total_results,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Unified search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

async def search_documents(query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Search documents"""
    try:
        collection = MongoDB.get_collection("documents")
        cursor = collection.find({
            "user_id": user_id,
            "$text": {"$search": query}
        }).limit(limit)
        
        documents = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "type": "document",
                "title": doc["title"],
                "content_preview": doc.get("content", "")[:200] + "..." if doc.get("content") else "",
                "document_type": doc.get("document_type"),
                "project_id": doc.get("project_id"),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"]
            }
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return []

async def search_projects(query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Search projects"""
    try:
        collection = MongoDB.get_collection("projects")
        cursor = collection.find({
            "user_id": user_id,
            "$text": {"$search": query}
        }).limit(limit)
        
        projects = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "type": "project",
                "title": doc["title"],
                "description": doc.get("description", ""),
                "tags": doc.get("tags", []),
                "document_count": doc.get("document_count", 0),
                "created_at": doc["created_at"],
                "updated_at": doc["updated_at"]
            }
            for doc in projects
        ]
        
    except Exception as e:
        logger.error(f"Project search failed: {e}")
        return []

async def search_calendar_events(query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Search calendar events"""
    try:
        collection = MongoDB.get_collection("calendar_events")
        cursor = collection.find({
            "user_id": user_id,
            "$text": {"$search": query}
        }).limit(limit)
        
        events = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "type": "calendar_event",
                "title": doc["title"],
                "description": doc.get("description", ""),
                "start_date": doc["start_date"],
                "end_date": doc["end_date"],
                "location": doc.get("location"),
                "created_at": doc["created_at"]
            }
            for doc in events
        ]
        
    except Exception as e:
        logger.error(f"Calendar event search failed: {e}")
        return []

async def search_reminders(query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Search reminders"""
    try:
        collection = MongoDB.get_collection("reminders")
        cursor = collection.find({
            "user_id": user_id,
            "$text": {"$search": query}
        }).limit(limit)
        
        reminders = await cursor.to_list(length=limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "type": "reminder",
                "title": doc["title"],
                "description": doc.get("description", ""),
                "due_date": doc.get("due_date"),
                "priority": doc["priority"],
                "status": doc["status"],
                "created_at": doc["created_at"]
            }
            for doc in reminders
        ]
        
    except Exception as e:
        logger.error(f"Reminder search failed: {e}")
        return []

async def search_memories(query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
    """Search memories using the memory store"""
    try:
        memories = await MemoryStore.search_memories(user_id, query, limit)
        
        return [
            {
                "id": memory["id"],
                "type": "memory",
                "content": memory["content"][:200] + "..." if len(memory["content"]) > 200 else memory["content"],
                "entities": memory.get("entities", []),
                "metadata": memory.get("metadata", {}),
                "created_at": memory["created_at"]
            }
            for memory in memories
        ]
        
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return []

@router.get("/suggestions")
async def get_search_suggestions(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Get search suggestions based on partial query"""
    try:
        suggestions = []
        
        # Get recent documents, projects, etc. that match the partial query
        if len(query) >= 2:
            # Search documents
            doc_collection = MongoDB.get_collection("documents")
            doc_cursor = doc_collection.find({
                "user_id": current_user.id,
                "title": {"$regex": query, "$options": "i"}
            }).limit(5)
            docs = await doc_cursor.to_list(length=5)
            
            for doc in docs:
                suggestions.append({
                    "text": doc["title"],
                    "type": "document",
                    "id": str(doc["_id"])
                })
            
            # Search projects
            proj_collection = MongoDB.get_collection("projects")
            proj_cursor = proj_collection.find({
                "user_id": current_user.id,
                "title": {"$regex": query, "$options": "i"}
            }).limit(5)
            projects = await proj_cursor.to_list(length=5)
            
            for proj in projects:
                suggestions.append({
                    "text": proj["title"],
                    "type": "project",
                    "id": str(proj["_id"])
                })
        
        return {
            "query": query,
            "suggestions": suggestions[:10]  # Limit to 10 suggestions
        }
        
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search suggestions"
        )

@router.get("/entities")
async def search_entities(
    entity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Search and list entities (people, places, organizations)"""
    try:
        collection = MongoDB.get_collection("entity_knowledge")
        
        query = {"user_id": current_user.id}
        if entity_type:
            query["entity_type"] = entity_type
        
        cursor = collection.find(query).sort("mention_count", -1).limit(50)
        entities = await cursor.to_list(length=50)
        
        return {
            "entity_type": entity_type,
            "entities": [
                {
                    "name": entity["entity_name"],
                    "type": entity["entity_type"],
                    "mention_count": entity["mention_count"],
                    "last_updated": entity["updated_at"]
                }
                for entity in entities
            ]
        }
        
    except Exception as e:
        logger.error(f"Entity search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search entities"
        )