"""Metrics and health check endpoints."""
from fastapi import APIRouter, Depends
from datetime import datetime
import os

from ..models.schemas import HealthResponse, MetricsResponse
from ..utils.dependencies import get_db, get_vector_store, get_mongodb_client
from ..services.vector_store import VectorStore
from .. import __version__

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Health check endpoint."""
    services = {
        "database": False,
        "vector_store": vector_store.index is not None
    }
    
    try:
        # Test MongoDB connection
        client = get_mongodb_client()
        await client.admin.command('ping')
        services["database"] = True
    except:
        services["database"] = False
    
    status = "healthy" if all(services.values()) else "degraded"
    
    return HealthResponse(
        status=status,
        version=__version__,
        timestamp=datetime.utcnow(),
        services=services
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Get system metrics (Prometheus-style)."""
    # Ingestion metrics
    total_ingestions = await db.ingest_jobs.count_documents({})
    
    # Calculate average ingestion time
    completed_jobs = await db.ingest_jobs.find({"status": "completed"}).to_list(length=None)
    avg_ingest_time = 0.0
    if completed_jobs:
        durations = []
        for job in completed_jobs:
            if job.get("completed_at") and job.get("created_at"):
                duration = (job["completed_at"] - job["created_at"]).total_seconds()
                durations.append(duration)
        avg_ingest_time = sum(durations) / len(durations) if durations else 0.0
    
    # Query metrics
    total_queries = await db.query_logs.count_documents({})
    
    # Calculate average query time
    query_logs = await db.query_logs.find().limit(100).to_list(length=100)
    avg_query_time = 0.0
    if query_logs:
        times = [log["processing_time_ms"] for log in query_logs if "processing_time_ms" in log]
        avg_query_time = sum(times) / len(times) if times else 0.0
    
    # Index metrics
    total_pages = await db.web_pages.count_documents({})
    vector_stats = vector_store.get_stats()
    
    # Calculate index size (approximate)
    index_size_mb = 0.0
    if vector_store.index:
        try:
            index_file = vector_store._get_index_file()
            if index_file.exists():
                index_size_mb = os.path.getsize(index_file) / (1024 * 1024)
        except:
            pass
    
    return MetricsResponse(
        total_ingestions=total_ingestions,
        total_queries=total_queries,
        avg_ingest_time_seconds=round(avg_ingest_time, 2),
        avg_query_time_ms=round(avg_query_time, 2),
        total_pages_indexed=total_pages,
        index_size_mb=round(index_size_mb, 2)
    )
