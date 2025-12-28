"""Question answering API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import logging
import time

from ..models.schemas import AskRequest, AskResponse, Citation
from ..services.answer_generator import AnswerGenerator
from ..services.embeddings import EmbeddingsService
from ..services.vector_store import VectorStore
from ..utils.dependencies import (
    get_answer_generator,
    get_embeddings_service,
    get_vector_store,
    get_db
)

router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
    vector_store: VectorStore = Depends(get_vector_store),
    db = Depends(get_db)
):
    """
    Ask a question and get a grounded answer with citations.
    
    - **question**: The question to answer (3-500 characters)
    - **top_k**: Number of relevant chunks to retrieve (1-10)
    - **min_confidence**: Minimum confidence threshold (0.0-1.0)
    """
    start_time = time.time()
    
    try:
        # Check if index is empty
        stats = vector_store.get_stats()
        if stats["total_chunks"] == 0:
            raise HTTPException(
                status_code=400,
                detail="No content has been indexed yet. Please ingest content first."
            )
        
        # Generate query embedding
        logger.info(f"Processing question: {request.question}")
        query_embedding = await embeddings_service.embed_query(request.question)
        
        # Retrieve relevant chunks
        top_k = request.top_k or 5
        retrieved_chunks = vector_store.search(query_embedding, top_k=top_k)
        
        logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
        
        # Generate answer
        result = await answer_generator.generate_answer(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
            min_confidence=request.min_confidence or 0.7
        )
        
        # Calculate processing time
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Format citations
        citations = [
            Citation(**citation) for citation in result["citations"]
        ]
        
        # Log query to MongoDB
        query_log = {
            "question": request.question,
            "answer": result["answer"],
            "confidence": result["confidence"],
            "citation_count": len(citations),
            "processing_time_ms": processing_time_ms,
            "created_at": datetime.utcnow()
        }
        await db.query_logs.insert_one(query_log)
        
        logger.info(f"Answer generated with confidence {result['confidence']}")
        
        return AskResponse(
            answer=result["answer"],
            citations=citations,
            confidence=result["confidence"],
            missing_information=result.get("missing_information"),
            processing_time_ms=processing_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
