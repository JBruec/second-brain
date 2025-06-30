from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime
import logging
from bson import ObjectId

from app.models.project import ProjectCreate, ProjectUpdate, Project, ProjectInDB, ProjectStats
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.core.database import MongoDB

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Project)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new project"""
    try:
        collection = MongoDB.get_collection("projects")
        
        # Create project document
        project_doc = ProjectInDB(
            **project.dict(),
            user_id=current_user.id
        )
        
        # Insert project
        result = await collection.insert_one(project_doc.dict(by_alias=True, exclude={"id"}))
        
        # Return created project
        created_doc = await collection.find_one({"_id": result.inserted_id})
        
        logger.info(f"Project created: {project.title} by {current_user.username}")
        
        return Project(
            id=str(created_doc["_id"]),
            title=created_doc["title"],
            description=created_doc.get("description"),
            instructions=created_doc.get("instructions"),
            tags=created_doc.get("tags", []),
            color=created_doc.get("color", "#3498db"),
            user_id=created_doc["user_id"],
            is_archived=created_doc["is_archived"],
            document_count=created_doc["document_count"],
            last_activity=created_doc["last_activity"],
            created_at=created_doc["created_at"],
            updated_at=created_doc["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Project creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

@router.get("/", response_model=List[Project])
async def get_projects(
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get user's projects"""
    try:
        collection = MongoDB.get_collection("projects")
        
        # Build query
        query = {"user_id": current_user.id}
        if not include_archived:
            query["is_archived"] = {"$ne": True}
        
        # Get projects
        cursor = collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        projects = await cursor.to_list(length=limit)
        
        return [
            Project(
                id=str(doc["_id"]),
                title=doc["title"],
                description=doc.get("description"),
                instructions=doc.get("instructions"),
                tags=doc.get("tags", []),
                color=doc.get("color", "#3498db"),
                user_id=doc["user_id"],
                is_archived=doc.get("is_archived", False),
                document_count=doc.get("document_count", 0),
                last_activity=doc.get("last_activity", doc["created_at"]),
                created_at=doc["created_at"],
                updated_at=doc["updated_at"]
            )
            for doc in projects
        ]
        
    except Exception as e:
        logger.error(f"Failed to get projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )

@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific project"""
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID"
            )
        
        collection = MongoDB.get_collection("projects")
        doc = await collection.find_one({
            "_id": ObjectId(project_id),
            "user_id": current_user.id
        })
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return Project(
            id=str(doc["_id"]),
            title=doc["title"],
            description=doc.get("description"),
            instructions=doc.get("instructions"),
            tags=doc.get("tags", []),
            color=doc.get("color", "#3498db"),
            user_id=doc["user_id"],
            is_archived=doc.get("is_archived", False),
            document_count=doc.get("document_count", 0),
            last_activity=doc.get("last_activity", doc["created_at"]),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )

@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a project"""
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID"
            )
        
        collection = MongoDB.get_collection("projects")
        
        # Check if project exists and belongs to user
        existing = await collection.find_one({
            "_id": ObjectId(project_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Prepare update data
        update_data = {}
        for field, value in project_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            # Update last_activity if content changed
            if any(field in update_data for field in ["title", "description", "instructions"]):
                update_data["last_activity"] = datetime.utcnow()
            
            await collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": update_data}
            )
        
        # Return updated project
        updated_doc = await collection.find_one({"_id": ObjectId(project_id)})
        
        logger.info(f"Project updated: {project_id} by {current_user.username}")
        
        return Project(
            id=str(updated_doc["_id"]),
            title=updated_doc["title"],
            description=updated_doc.get("description"),
            instructions=updated_doc.get("instructions"),
            tags=updated_doc.get("tags", []),
            color=updated_doc.get("color", "#3498db"),
            user_id=updated_doc["user_id"],
            is_archived=updated_doc.get("is_archived", False),
            document_count=updated_doc.get("document_count", 0),
            last_activity=updated_doc.get("last_activity", updated_doc["created_at"]),
            created_at=updated_doc["created_at"],
            updated_at=updated_doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a project (and optionally its documents)"""
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID"
            )
        
        projects_collection = MongoDB.get_collection("projects")
        documents_collection = MongoDB.get_collection("documents")
        
        # Check if project exists and belongs to user
        existing = await projects_collection.find_one({
            "_id": ObjectId(project_id),
            "user_id": current_user.id
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Update documents to remove project reference (don't delete documents)
        await documents_collection.update_many(
            {"project_id": project_id},
            {"$unset": {"project_id": ""}}
        )
        
        # Delete the project
        await projects_collection.delete_one({"_id": ObjectId(project_id)})
        
        logger.info(f"Project deleted: {project_id} by {current_user.username}")
        
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )

@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get project statistics"""
    try:
        if not ObjectId.is_valid(project_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project ID"
            )
        
        projects_collection = MongoDB.get_collection("projects")
        documents_collection = MongoDB.get_collection("documents")
        
        # Check if project exists and belongs to user
        project = await projects_collection.find_one({
            "_id": ObjectId(project_id),
            "user_id": current_user.id
        })
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get document statistics
        pipeline = [
            {"$match": {"project_id": project_id, "user_id": current_user.id}},
            {"$group": {
                "_id": None,
                "document_count": {"$sum": 1},
                "total_words": {"$sum": "$word_count"},
                "last_modified": {"$max": "$updated_at"}
            }}
        ]
        
        result = await documents_collection.aggregate(pipeline).to_list(length=1)
        
        if result:
            stats = result[0]
            return ProjectStats(
                project_id=project_id,
                document_count=stats.get("document_count", 0),
                total_words=stats.get("total_words", 0),
                last_modified=stats.get("last_modified", project["created_at"])
            )
        else:
            return ProjectStats(
                project_id=project_id,
                document_count=0,
                total_words=0,
                last_modified=project["created_at"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get project stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project statistics"
        )