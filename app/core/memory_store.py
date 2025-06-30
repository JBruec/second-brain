# from mem0 import Memory  # Placeholder for Mem0 integration
# from voyage import VoyageEmbeddings  # Placeholder for Voyage AI integration
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json
from .config import settings
from .database import MongoDB

logger = logging.getLogger(__name__)

class MemoryStore:
    _instance = None
    mem0_client = None
    voyage_embeddings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls):
        """Initialize Mem0 and Voyage AI clients"""
        try:
            # Initialize Mem0 (placeholder)
            if settings.mem0_api_key:
                # cls.mem0_client = Memory(api_key=settings.mem0_api_key)
                logger.info("✅ Mem0 client initialized (placeholder)")
            else:
                logger.warning("⚠️ Mem0 API key not provided")

            # Initialize Voyage embeddings (placeholder)
            if settings.voyage_api_key:
                # cls.voyage_embeddings = VoyageEmbeddings(api_key=settings.voyage_api_key)
                logger.info("✅ Voyage AI embeddings initialized (placeholder)")
            else:
                logger.warning("⚠️ Voyage AI API key not provided")

        except Exception as e:
            logger.error(f"❌ Failed to initialize memory store: {e}")
            raise

    @classmethod
    async def add_memory(cls, user_id: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add a new memory with entity extraction and relationship building"""
        try:
            # Extract entities and relationships from content
            entities = await cls.extract_entities(content)
            
            # Store in Mem0 if available (placeholder)
            mem0_result = None
            if cls.mem0_client:
                # mem0_result = await cls.mem0_client.add(
                #     content,
                #     user_id=user_id,
                #     metadata=metadata or {}
                # )
                mem0_result = {"id": "placeholder_mem0_id"}

            # Store in MongoDB for persistence and search
            memory_doc = {
                "user_id": user_id,
                "content": content,
                "entities": entities,
                "metadata": metadata or {},
                "mem0_id": mem0_result.get("id") if mem0_result else None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Generate embedding for semantic search (placeholder)
            if cls.voyage_embeddings:
                # embedding = await cls.voyage_embeddings.embed_query(content)
                # memory_doc["embedding"] = embedding
                pass

            # Insert into MongoDB
            collection = MongoDB.get_collection("memories")
            result = await collection.insert_one(memory_doc)
            memory_doc["_id"] = result.inserted_id

            # Update entity knowledge graphs
            await cls.update_entity_knowledge(user_id, entities, content)

            return {
                "id": str(result.inserted_id),
                "mem0_id": mem0_result.get("id") if mem0_result else None,
                "entities": entities,
                "created_at": memory_doc["created_at"]
            }

        except Exception as e:
            logger.error(f"❌ Failed to add memory: {e}")
            raise

    @classmethod
    async def extract_entities(cls, content: str) -> List[Dict[str, Any]]:
        """Extract entities (people, places, organizations, etc.) from content"""
        try:
            # This would typically use NER (Named Entity Recognition)
            # For now, we'll implement a simple keyword-based approach
            # In production, you'd use spaCy, NLTK, or a service like Abacus.ai
            
            entities = []
            
            # Simple patterns for common entities
            import re
            
            # People names (capitalized words, common patterns)
            name_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
            for name in name_patterns:
                if len(name.split()) <= 3:  # Reasonable name length
                    entities.append({
                        "name": name,
                        "type": "person",
                        "confidence": 0.7
                    })

            # Organizations (patterns like "Company Inc.", "LLC", etc.)
            org_patterns = re.findall(r'\b[A-Z][a-zA-Z\s]*(?:Inc|LLC|Corp|Company|Organization)\b', content)
            for org in org_patterns:
                entities.append({
                    "name": org,
                    "type": "organization", 
                    "confidence": 0.8
                })

            # Locations (cities, states, countries - would need a more sophisticated approach)
            # This is a simplified version
            location_keywords = ['City', 'State', 'Country', 'Street', 'Avenue', 'Road']
            for keyword in location_keywords:
                if keyword.lower() in content.lower():
                    # Extract surrounding context
                    pattern = rf'\b\w+\s+{keyword}\b'
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        entities.append({
                            "name": match,
                            "type": "location",
                            "confidence": 0.6
                        })

            return entities

        except Exception as e:
            logger.error(f"❌ Failed to extract entities: {e}")
            return []

    @classmethod
    async def update_entity_knowledge(cls, user_id: str, entities: List[Dict], content: str):
        """Update knowledge graphs for extracted entities"""
        try:
            collection = MongoDB.get_collection("entity_knowledge")
            
            for entity in entities:
                entity_name = entity["name"]
                entity_type = entity["type"]
                
                # Check if entity already exists
                existing = await collection.find_one({
                    "user_id": user_id,
                    "entity_name": entity_name,
                    "entity_type": entity_type
                })

                if existing:
                    # Update existing entity knowledge
                    await collection.update_one(
                        {"_id": existing["_id"]},
                        {
                            "$push": {"mentions": {
                                "content": content,
                                "timestamp": datetime.utcnow()
                            }},
                            "$set": {"updated_at": datetime.utcnow()},
                            "$inc": {"mention_count": 1}
                        }
                    )
                else:
                    # Create new entity knowledge
                    entity_doc = {
                        "user_id": user_id,
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "mentions": [{
                            "content": content,
                            "timestamp": datetime.utcnow()
                        }],
                        "mention_count": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    await collection.insert_one(entity_doc)

        except Exception as e:
            logger.error(f"❌ Failed to update entity knowledge: {e}")

    @classmethod
    async def get_entity_knowledge(cls, user_id: str, entity_name: str) -> Dict[str, Any]:
        """Get all knowledge about a specific entity"""
        try:
            collection = MongoDB.get_collection("entity_knowledge")
            
            entity_data = await collection.find_one({
                "user_id": user_id,
                "entity_name": {"$regex": entity_name, "$options": "i"}
            })

            if not entity_data:
                return {"entity_name": entity_name, "mentions": [], "summary": "No information found"}

            # Generate a summary of the entity
            mentions = entity_data.get("mentions", [])
            summary = await cls.generate_entity_summary(entity_name, mentions)

            return {
                "entity_name": entity_data["entity_name"],
                "entity_type": entity_data["entity_type"],
                "mention_count": entity_data["mention_count"],
                "mentions": mentions,
                "summary": summary,
                "last_updated": entity_data["updated_at"]
            }

        except Exception as e:
            logger.error(f"❌ Failed to get entity knowledge: {e}")
            return {"error": str(e)}

    @classmethod
    async def generate_entity_summary(cls, entity_name: str, mentions: List[Dict]) -> str:
        """Generate a summary of all information about an entity"""
        try:
            if not mentions:
                return f"No information available about {entity_name}"

            # Combine all mentions
            all_content = " ".join([mention["content"] for mention in mentions])
            
            # This would typically use an LLM to generate a proper summary
            # For now, return a simple aggregation
            return f"Based on {len(mentions)} mentions, here's what I know about {entity_name}: {all_content[:500]}..."

        except Exception as e:
            logger.error(f"❌ Failed to generate entity summary: {e}")
            return f"Error generating summary for {entity_name}"

    @classmethod
    async def search_memories(cls, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search memories using semantic similarity"""
        try:
            collection = MongoDB.get_collection("memories")
            
            # If we have embeddings, do semantic search (placeholder)
            if cls.voyage_embeddings:
                # query_embedding = await cls.voyage_embeddings.embed_query(query)
                
                # MongoDB vector search (requires MongoDB Atlas or vector search setup)
                # For now, we'll fall back to text search
                pass
                
            # Text search fallback
            results = await collection.find({
                "user_id": user_id,
                "$text": {"$search": query}
            }).limit(limit).to_list(length=limit)

            return [
                {
                    "id": str(doc["_id"]),
                    "content": doc["content"],
                    "entities": doc.get("entities", []),
                    "metadata": doc.get("metadata", {}),
                    "created_at": doc["created_at"]
                }
                for doc in results
            ]

        except Exception as e:
            logger.error(f"❌ Failed to search memories: {e}")
            return []