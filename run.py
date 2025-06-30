#!/usr/bin/env python3
"""
Development startup script for AI Second Brain
"""
import uvicorn
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Configuration
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    
    print(f"🧠 Starting AI Second Brain on {host}:{port}")
    print(f"📖 API docs will be available at: http://localhost:{port}/docs")
    print(f"🔄 Auto-reload: {reload}")
    
    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )