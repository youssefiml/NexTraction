"""MongoDB index creation script."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_indexes(mongodb_url: str, db_name: str):
    """Create recommended indexes for better performance."""
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]
    
    try:
        # Ingest jobs indexes
        await db.ingest_jobs.create_index("status")
        await db.ingest_jobs.create_index([("created_at", -1)])
        logger.info("✅ Created indexes for ingest_jobs")
        
        # Web pages indexes
        await db.web_pages.create_index("url", unique=True)
        await db.web_pages.create_index("job_id")
        await db.web_pages.create_index("is_indexed")
        logger.info("✅ Created indexes for web_pages")
        
        # Content chunks indexes
        await db.content_chunks.create_index("page_id")
        await db.content_chunks.create_index("url")
        logger.info("✅ Created indexes for content_chunks")
        
        # Query logs indexes
        await db.query_logs.create_index([("created_at", -1)])
        logger.info("✅ Created indexes for query_logs")
        
        logger.info("✅ All indexes created successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python mongodb_indexes.py <mongodb_url> <db_name>")
        print("Example: python mongodb_indexes.py mongodb://localhost:27017 nextraction")
        sys.exit(1)
    
    mongodb_url = sys.argv[1]
    db_name = sys.argv[2]
    
    asyncio.run(create_indexes(mongodb_url, db_name))

