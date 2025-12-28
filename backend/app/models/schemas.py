"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestRequest(BaseModel):
    """Request model for /ingest endpoint."""
    urls: List[HttpUrl] = Field(..., description="List of URLs to ingest")
    domain_allowlist: Optional[List[str]] = Field(
        default=None,
        description="Allowed domains for crawling"
    )
    max_pages: Optional[int] = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of pages to crawl"
    )
    max_depth: Optional[int] = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum crawl depth"
    )


class IngestResponse(BaseModel):
    """Response model for /ingest endpoint."""
    job_id: str
    status: JobStatus
    message: str
    created_at: datetime


class Citation(BaseModel):
    """Citation model with excerpt and source."""
    url: str
    title: str
    excerpt: str = Field(..., max_length=200)
    chunk_id: str
    relevance_score: float


class AskRequest(BaseModel):
    """Request model for /ask endpoint."""
    question: str = Field(..., min_length=3, max_length=500)
    top_k: Optional[int] = Field(default=5, ge=1, le=10)
    min_confidence: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)


class AskResponse(BaseModel):
    """Response model for /ask endpoint."""
    answer: str
    citations: List[Citation]
    confidence: float
    missing_information: Optional[List[str]] = None
    processing_time_ms: float


class JobStatusResponse(BaseModel):
    """Response model for job status check."""
    job_id: str
    status: JobStatus
    progress: float  # 0.0 to 1.0
    pages_processed: int
    total_pages: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, bool]


class MetricsResponse(BaseModel):
    """Metrics response."""
    total_ingestions: int
    total_queries: int
    avg_ingest_time_seconds: float
    avg_query_time_ms: float
    total_pages_indexed: int
    index_size_mb: float

