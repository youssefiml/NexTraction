"""NexTraction 2 - FastAPI Application."""
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings
from .routers import ingest, ask, metrics
from .utils.dependencies import get_mongodb_client, close_mongodb_connection
from .utils.logging_config import setup_logging

# Setup logging
setup_logging(
    log_level=settings.log_level,
    use_json=settings.environment == "production"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting NexTraction 2 application")
    
    # Initialize MongoDB connection
    try:
        client = get_mongodb_client()
        # Test connection
        await client.admin.command('ping')
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NexTraction 2 application")
    await close_mongodb_connection()
    logger.info("MongoDB connection closed")


# Create FastAPI app
app = FastAPI(
    title="NexTraction 2",
    description="Production-grade RAG pipeline for web content extraction and question answering",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(ingest.router)
app.include_router(ask.router)
app.include_router(metrics.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NexTraction 2",
        "version": "2.0.0",
        "description": "Production-grade RAG pipeline for web content",
        "endpoints": {
            "docs": "/docs",
            "health": "/api/health",
            "metrics": "/api/metrics",
            "ingest": "/api/ingest",
            "ask": "/api/ask"
        }
    }


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint - returns 204 No Content to prevent 404 errors."""
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )
