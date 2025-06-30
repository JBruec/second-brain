from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
from typing import List, Optional
import asyncio

from app.core.config import settings
from app.api.routes import auth, projects, documents, memory, calendar, reminders, search
from app.core.database import MongoDB
from app.core.memory_store import MemoryStore

load_dotenv()

app = FastAPI(
    title="AI Second Brain",
    description="An intelligent personal assistant that manages documents, projects, and integrates with Apple ecosystem",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize databases
@app.on_event("startup")
async def startup_event():
    """Initialize database connections and services"""
    try:
        # Initialize MongoDB
        await MongoDB.connect()
        
        # Initialize Memory Store
        await MemoryStore.initialize()
        
        print("✅ Application startup complete")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connections"""
    await MongoDB.disconnect()
    print("✅ Application shutdown complete")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(memory.router, prefix="/api/memory", tags=["Memory"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(reminders.router, prefix="/api/reminders", tags=["Reminders"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])

@app.get("/")
async def root():
    return {
        "message": "AI Second Brain API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )