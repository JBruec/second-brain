from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import logging

from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.memory_store import MemoryStore

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/add")
async def add_memory(
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """Add a new memory"""
    try:
        result = await MemoryStore.add_memory(
            user_id=current_user.id,
            content=content,
            metadata=metadata or {}
        )
        
        logger.info(f"Memory added for user {current_user.username}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add memory"
        )

@router.get("/search")
async def search_memories(
    query: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Search memories"""
    try:
        results = await MemoryStore.search_memories(
            user_id=current_user.id,
            query=query,
            limit=limit
        )
        
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memories"
        )

@router.get("/entity/{entity_name}")
async def get_entity_knowledge(
    entity_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get all knowledge about a specific entity (person, place, etc.)"""
    try:
        result = await MemoryStore.get_entity_knowledge(
            user_id=current_user.id,
            entity_name=entity_name
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get entity knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entity knowledge"
        )