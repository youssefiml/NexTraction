"""Embeddings service supporting multiple providers."""
import numpy as np
from typing import List
import logging
from openai import OpenAI
import google.generativeai as genai

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating embeddings."""
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: str = None,
        model: str = None
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        
        if self.provider == "openai":
            self.model = model or "text-embedding-3-small"
            self.dimension = 1536
            self.client = OpenAI(api_key=api_key) if api_key else None
        elif self.provider == "gemini":
            self.model = model or "models/embedding-001"
            self.dimension = 768
            if api_key:
                genai.configure(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def embed_texts(self, texts: List[str], batch_size: int = 100) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                if self.provider == "openai":
                    embeddings = await self._embed_openai(batch)
                elif self.provider == "gemini":
                    embeddings = await self._embed_gemini(batch)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                all_embeddings.extend(embeddings)
                
            except Exception as e:
                logger.error(f"Error generating embeddings: {str(e)}")
                # Return zero vectors as fallback
                zero_embeddings = [[0.0] * self.dimension] * len(batch)
                all_embeddings.extend(zero_embeddings)
        
        return np.array(all_embeddings, dtype=np.float32)
    
    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        if not self.client:
            logger.warning("OpenAI client not configured, returning zero vectors")
            return [[0.0] * self.dimension] * len(texts)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}")
            return [[0.0] * self.dimension] * len(texts)
    
    async def _embed_gemini(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Gemini."""
        try:
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini embedding error: {str(e)}")
            return [[0.0] * self.dimension] * len(texts)
    
    async def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        try:
            if self.provider == "openai":
                if not self.client:
                    return np.zeros(self.dimension, dtype=np.float32)
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=query
                )
                embedding = response.data[0].embedding
                
            elif self.provider == "gemini":
                result = genai.embed_content(
                    model=self.model,
                    content=query,
                    task_type="retrieval_query"
                )
                embedding = result['embedding']
            else:
                return np.zeros(self.dimension, dtype=np.float32)
            
            return np.array(embedding, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            return np.zeros(self.dimension, dtype=np.float32)

