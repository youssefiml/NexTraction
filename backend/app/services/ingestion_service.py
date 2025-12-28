"""Main ingestion orchestration service."""
import asyncio
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.database import IngestJob, WebPage, ContentChunk
from .crawler import WebCrawler
from .content_processor import ContentProcessor
from .embeddings import EmbeddingsService
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates the complete ingestion pipeline."""
    
    def __init__(
        self,
        embeddings_service: EmbeddingsService,
        vector_store: VectorStore,
        db: AsyncIOMotorDatabase,
        config: Dict
    ):
        self.embeddings_service = embeddings_service
        self.vector_store = vector_store
        self.db = db
        self.config = config
        
        # Initialize components
        self.content_processor = ContentProcessor(
            chunk_size=config.get("chunk_size", 500),
            chunk_overlap=config.get("chunk_overlap", 50),
            min_chunk_length=config.get("min_chunk_length", 100)
        )
    
    async def start_ingestion(
        self,
        urls: List[str],
        domain_allowlist: Optional[List[str]] = None,
        max_pages: int = 50,
        max_depth: int = 2
    ) -> str:
        """Start an ingestion job."""
        # Create job record
        job_id = str(uuid.uuid4())
        job_data = {
            "_id": job_id,
            "status": "pending",
            "urls": urls,
            "domain_allowlist": domain_allowlist,
            "max_pages": max_pages,
            "max_depth": max_depth,
            "pages_processed": 0,
            "total_pages": max_pages,
            "progress": 0.0,
            "error_message": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "completed_at": None
        }
        
        await self.db.ingest_jobs.insert_one(job_data)
        
        # Start processing in background
        asyncio.create_task(self._process_ingestion(job_id))
        
        return job_id
    
    async def _process_ingestion(self, job_id: str):
        """Process ingestion job."""
        job = await self.db.ingest_jobs.find_one({"_id": job_id})
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            # Update status
            await self.db.ingest_jobs.update_one(
                {"_id": job_id},
                {"$set": {"status": "running", "updated_at": datetime.utcnow()}}
            )
            
            # Step 1: Crawl pages
            logger.info(f"Starting crawl for job {job_id}")
            crawler = WebCrawler(
                domain_allowlist=job.get("domain_allowlist"),
                max_pages=job["max_pages"],
                max_depth=job["max_depth"],
                timeout=self.config.get("request_timeout", 30),
                max_retries=self.config.get("max_retries", 3),
                user_agent=self.config.get("user_agent", "NexTraction/2.0")
            )
            
            async def progress_callback(processed, total):
                await self.db.ingest_jobs.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "pages_processed": processed,
                            "total_pages": total,
                            "progress": processed / total if total > 0 else 0,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            
            pages = await crawler.crawl(job["urls"], progress_callback)
            logger.info(f"Crawled {len(pages)} pages for job {job_id}")
            
            if len(pages) == 0:
                logger.warning(f"No pages were crawled for job {job_id}. This might be due to:")
                logger.warning("  - Network issues or timeouts")
                logger.warning("  - Website blocking crawlers")
                logger.warning("  - Invalid URLs")
                logger.warning(f"  - Failed URLs: {crawler.failed_urls}")
            
            # Step 2: Process and chunk content
            logger.info(f"Processing content for job {job_id}")
            all_chunks = []
            for page_data in pages:
                processed = self.content_processor.process_page(page_data)
                if processed:
                    # Save page metadata
                    page_id = str(uuid.uuid4())
                    page_doc = {
                        "_id": page_id,
                        "url": processed["url"],
                        "title": processed["title"],
                        "content_hash": processed["content_hash"],
                        "fetch_timestamp": datetime.fromisoformat(processed["fetch_timestamp"]),
                        "content_length": processed["word_count"],
                        "chunk_count": len(processed["chunks"]),
                        "is_indexed": False,
                        "job_id": job_id
                    }
                    await self.db.web_pages.insert_one(page_doc)
                    
                    # Save chunks
                    chunks_to_insert = []
                    for chunk_data in processed["chunks"]:
                        chunk_doc = {
                            "_id": chunk_data["id"],
                            "page_id": page_id,
                            "url": chunk_data["url"],
                            "title": chunk_data["title"],
                            "content": chunk_data["content"],
                            "chunk_index": chunk_data["chunk_index"],
                            "embedding_id": None,
                            "created_at": datetime.utcnow()
                        }
                        chunks_to_insert.append(chunk_doc)
                        all_chunks.append(chunk_data)
                    
                    if chunks_to_insert:
                        await self.db.content_chunks.insert_many(chunks_to_insert)
            
            logger.info(f"Created {len(all_chunks)} chunks for job {job_id}")
            
            # Step 3: Generate embeddings
            if all_chunks:
                logger.info(f"Generating embeddings for job {job_id}")
                chunk_texts = [chunk["content"] for chunk in all_chunks]
                embeddings = await self.embeddings_service.embed_texts(chunk_texts)
                
                # Step 4: Add to vector store
                logger.info(f"Adding to vector store for job {job_id}")
                self.vector_store.add_embeddings(embeddings, all_chunks)
                self.vector_store.save()
                
                # Update page indexed status
                await self.db.web_pages.update_many(
                    {"job_id": job_id},
                    {"$set": {"is_indexed": True}}
                )
            
            # Mark job as completed
            await self.db.ingest_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "progress": 1.0,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
            await self.db.ingest_jobs.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "error_message": f"{str(e)}",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status."""
        job = await self.db.ingest_jobs.find_one({"_id": job_id})
        if not job:
            return None
        
        return {
            "job_id": job["_id"],
            "status": job["status"],
            "progress": job["progress"],
            "pages_processed": job["pages_processed"],
            "total_pages": job["total_pages"],
            "error_message": job.get("error_message"),
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "completed_at": job.get("completed_at")
        }
