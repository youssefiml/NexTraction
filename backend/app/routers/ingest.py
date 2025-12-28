"""Ingestion API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from datetime import datetime
import logging

from ..models.schemas import IngestRequest, IngestResponse, JobStatusResponse, JobStatus
from ..services.ingestion_service import IngestionService
from ..utils.dependencies import get_db, get_ingestion_service

router = APIRouter(prefix="/api", tags=["ingestion"])
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_content(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Start content ingestion from provided URLs.
    
    - **urls**: List of seed URLs to crawl
    - **domain_allowlist**: Optional list of allowed domains
    - **max_pages**: Maximum number of pages to crawl (1-500)
    - **max_depth**: Maximum crawl depth (1-5)
    """
    try:
        # Convert HttpUrl to strings
        urls = [str(url) for url in request.urls]
        
        # Start ingestion
        job_id = await ingestion_service.start_ingestion(
            urls=urls,
            domain_allowlist=request.domain_allowlist,
            max_pages=request.max_pages or 50,
            max_depth=request.max_depth or 2
        )
        
        logger.info(f"Created ingestion job {job_id}")
        
        return IngestResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Ingestion job started successfully",
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error starting ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingest/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Get the status of an ingestion job.
    
    - **job_id**: The ID of the ingestion job
    """
    status = await ingestion_service.get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(**status)
