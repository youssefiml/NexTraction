"""Database models for MongoDB."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class IngestJob(BaseModel):
    """Ingestion job tracking."""
    id: str = Field(..., alias="_id")
    status: str = "pending"
    urls: List[str]
    domain_allowlist: Optional[List[str]] = None
    max_pages: int
    max_depth: int
    pages_processed: int = 0
    total_pages: int = 0
    progress: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class WebPage(BaseModel):
    """Stored web page metadata."""
    id: str = Field(..., alias="_id")
    url: str
    title: str
    content_hash: str
    fetch_timestamp: datetime = Field(default_factory=datetime.utcnow)
    content_length: int
    chunk_count: int = 0
    is_indexed: bool = False
    job_id: str
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ContentChunk(BaseModel):
    """Content chunks for vector indexing."""
    id: str = Field(..., alias="_id")
    page_id: str
    url: str
    title: str
    content: str
    chunk_index: int
    embedding_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class QueryLog(BaseModel):
    """Query logging for analytics."""
    id: Optional[str] = Field(None, alias="_id")
    question: str
    answer: str
    confidence: float
    citation_count: int
    processing_time_ms: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
