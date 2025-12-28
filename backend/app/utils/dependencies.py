"""Dependency injection for FastAPI."""
from motor.motor_asyncio import AsyncIOMotorClient
from functools import lru_cache
import os

from ..config import settings
from ..services.embeddings import EmbeddingsService
from ..services.vector_store import VectorStore
from ..services.answer_generator import AnswerGenerator
from ..services.ingestion_service import IngestionService

# MongoDB client
_mongodb_client: AsyncIOMotorClient = None


def get_mongodb_client() -> AsyncIOMotorClient:
    """Get MongoDB client singleton."""
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
    return _mongodb_client


def get_database():
    """Get MongoDB database."""
    client = get_mongodb_client()
    return client[settings.mongodb_db_name]


async def close_mongodb_connection():
    """Close MongoDB connection."""
    global _mongodb_client
    if _mongodb_client is not None:
        _mongodb_client.close()
        _mongodb_client = None


def get_db():
    """Get database dependency for FastAPI."""
    return get_database()


@lru_cache()
def get_embeddings_service() -> EmbeddingsService:
    """Get embeddings service singleton."""
    # Determine provider based on available API keys
    if settings.openai_api_key:
        return EmbeddingsService(
            provider="openai",
            api_key=settings.openai_api_key
        )
    elif settings.gemini_api_key:
        return EmbeddingsService(
            provider="gemini",
            api_key=settings.gemini_api_key
        )
    else:
        # Return service without API key (will use zero vectors as fallback)
        return EmbeddingsService(provider="openai", api_key=None)


@lru_cache()
def get_vector_store() -> VectorStore:
    """Get vector store singleton."""
    embeddings_service = get_embeddings_service()
    return VectorStore(
        index_path=settings.faiss_index_path,
        dimension=embeddings_service.dimension
    )


@lru_cache()
def get_answer_generator() -> AnswerGenerator:
    """Get answer generator singleton."""
    if settings.openai_api_key:
        return AnswerGenerator(
            provider="openai",
            api_key=settings.openai_api_key,
            max_excerpt_length=settings.max_excerpt_length
        )
    elif settings.gemini_api_key:
        return AnswerGenerator(
            provider="gemini",
            api_key=settings.gemini_api_key,
            max_excerpt_length=settings.max_excerpt_length
        )
    else:
        return AnswerGenerator(provider="openai", api_key=None)


def get_ingestion_service(db = None) -> IngestionService:
    """Get ingestion service."""
    if db is None:
        db = get_database()
    
    config = {
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "min_chunk_length": settings.min_chunk_length,
        "request_timeout": settings.request_timeout,
        "max_retries": settings.max_retries,
        "user_agent": settings.user_agent
    }
    
    return IngestionService(
        embeddings_service=get_embeddings_service(),
        vector_store=get_vector_store(),
        db=db,
        config=config
    )
