"""Vector store service using FAISS."""
import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for semantic search."""
    
    def __init__(self, index_path: str, dimension: int = 1536):
        self.index_path = Path(index_path)
        self.dimension = dimension
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict] = []
        self.id_to_index: Dict[str, int] = {}
        
        # Create directory if it doesn't exist
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing index
        self.load()
    
    def _get_index_file(self) -> Path:
        """Get index file path."""
        return self.index_path / "index.faiss"
    
    def _get_metadata_file(self) -> Path:
        """Get metadata file path."""
        return self.index_path / "metadata.pkl"
    
    def initialize_index(self):
        """Initialize a new FAISS index."""
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.id_to_index = {}
        logger.info(f"Initialized new FAISS index with dimension {self.dimension}")
    
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        chunks_metadata: List[Dict]
    ) -> int:
        """Add embeddings to the index."""
        if self.index is None:
            self.initialize_index()
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        start_idx = len(self.metadata)
        self.index.add(embeddings)
        
        # Store metadata
        for i, chunk_meta in enumerate(chunks_metadata):
            idx = start_idx + i
            self.metadata.append(chunk_meta)
            self.id_to_index[chunk_meta["id"]] = idx
        
        logger.info(f"Added {len(chunks_metadata)} embeddings to index")
        return len(chunks_metadata)
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5
    ) -> List[Tuple[Dict, float]]:
        """Search for similar chunks."""
        if self.index is None or len(self.metadata) == 0:
            logger.warning("Index is empty")
            return []
        
        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Search
        k = min(top_k, len(self.metadata))
        scores, indices = self.index.search(query_embedding, k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.metadata):
                results.append((self.metadata[idx], float(score)))
        
        return results
    
    def save(self):
        """Save index and metadata to disk."""
        if self.index is None:
            logger.warning("No index to save")
            return
        
        try:
            # Save FAISS index
            index_file = self._get_index_file()
            faiss.write_index(self.index, str(index_file))
            
            # Save metadata
            metadata_file = self._get_metadata_file()
            with open(metadata_file, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'id_to_index': self.id_to_index
                }, f)
            
            logger.info(f"Saved index with {len(self.metadata)} embeddings")
            
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
            raise
    
    def load(self):
        """Load index and metadata from disk."""
        index_file = self._get_index_file()
        metadata_file = self._get_metadata_file()
        
        if not index_file.exists() or not metadata_file.exists():
            logger.info("No existing index found, will create new one")
            return
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            
            # Load metadata
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
                self.metadata = data['metadata']
                self.id_to_index = data['id_to_index']
            
            logger.info(f"Loaded index with {len(self.metadata)} embeddings")
            
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            self.initialize_index()
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "total_chunks": len(self.metadata),
            "dimension": self.dimension,
            "is_trained": self.index.is_trained if self.index else False,
        }
    
    def clear(self):
        """Clear the index."""
        self.initialize_index()
        self.save()
        logger.info("Cleared index")

