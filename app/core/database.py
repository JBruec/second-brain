from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, TEXT
from typing import Optional
import logging
from .config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    database = None

    @classmethod
    async def connect(cls):
        """Create database connection"""
        try:
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
            cls.database = cls.client[settings.mongodb_db_name]
            
            # Test connection
            await cls.client.admin.command('ping')
            logger.info("✅ Successfully connected to MongoDB")
            
            # Create indexes
            await cls.create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        """Close database connection"""
        if cls.client:
            cls.client.close()
            logger.info("✅ Disconnected from MongoDB")

    @classmethod
    async def create_indexes(cls):
        """Create necessary database indexes"""
        try:
            # Users collection indexes
            await cls.database.users.create_index("email", unique=True)
            await cls.database.users.create_index("username", unique=True)
            
            # Projects collection indexes
            await cls.database.projects.create_index([("user_id", 1), ("name", 1)])
            await cls.database.projects.create_index([("title", TEXT), ("description", TEXT)])
            
            # Documents collection indexes
            await cls.database.documents.create_index([("user_id", 1), ("project_id", 1)])
            await cls.database.documents.create_index([("title", TEXT), ("content", TEXT)])
            await cls.database.documents.create_index("created_at")
            
            # Memory collection indexes
            await cls.database.memories.create_index([("user_id", 1), ("entity_type", 1)])
            await cls.database.memories.create_index([("entity_name", TEXT), ("content", TEXT)])
            await cls.database.memories.create_index("updated_at")
            
            # Calendar events collection indexes
            await cls.database.calendar_events.create_index([("user_id", 1), ("start_date", 1)])
            await cls.database.calendar_events.create_index([("title", TEXT), ("description", TEXT)])
            
            # Reminders collection indexes
            await cls.database.reminders.create_index([("user_id", 1), ("due_date", 1)])
            await cls.database.reminders.create_index([("title", TEXT), ("description", TEXT)])
            await cls.database.reminders.create_index("completed")
            
            logger.info("✅ Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            raise

    @classmethod
    def get_collection(cls, name: str):
        """Get a collection from the database"""
        if not cls.database:
            raise RuntimeError("Database not connected")
        return cls.database[name]

    @classmethod
    async def get_database_stats(cls):
        """Get database statistics"""
        if not cls.database:
            raise RuntimeError("Database not connected")
        
        stats = await cls.database.command("dbStats")
        return {
            "collections": stats.get("collections", 0),
            "objects": stats.get("objects", 0),
            "data_size": stats.get("dataSize", 0),
            "storage_size": stats.get("storageSize", 0)
        }