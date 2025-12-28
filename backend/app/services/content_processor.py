"""Content processing and chunking service."""
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import logging
import hashlib

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process and chunk HTML content."""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_length: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length
    
    def clean_html(self, html_content: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html_content, "lxml")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text(self, text: str, url: str, title: str) -> List[Dict]:
        """Split text into overlapping chunks."""
        sentences = self._split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            # If adding this sentence exceeds chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                
                if len(chunk_text) >= self.min_chunk_length:
                    chunk_id = self._generate_chunk_id(url, chunk_index)
                    chunks.append({
                        "id": chunk_id,
                        "url": url,
                        "title": title,
                        "content": chunk_text,
                        "chunk_index": chunk_index,
                        "word_count": current_length
                    })
                    chunk_index += 1
                
                # Keep overlap
                overlap_words = self.chunk_overlap
                overlap_sentences = []
                overlap_length = 0
                
                for s in reversed(current_chunk):
                    s_length = len(s.split())
                    if overlap_length + s_length <= overlap_words:
                        overlap_sentences.insert(0, s)
                        overlap_length += s_length
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_length:
                chunk_id = self._generate_chunk_id(url, chunk_index)
                chunks.append({
                    "id": chunk_id,
                    "url": url,
                    "title": title,
                    "content": chunk_text,
                    "chunk_index": chunk_index,
                    "word_count": current_length
                })
        
        return chunks
    
    def _generate_chunk_id(self, url: str, chunk_index: int) -> str:
        """Generate stable chunk ID."""
        content = f"{url}_{chunk_index}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def process_page(self, page_data: Dict) -> Dict:
        """Process a single page: clean and chunk."""
        try:
            clean_text = self.clean_html(page_data["html_content"])
            
            # Skip pages with too little content
            word_count = len(clean_text.split())
            if word_count < 50:
                logger.warning(f"Page too short, skipping: {page_data['url']}")
                return None
            
            chunks = self.chunk_text(
                clean_text,
                page_data["url"],
                page_data["title"]
            )
            
            return {
                "url": page_data["url"],
                "title": page_data["title"],
                "content_hash": page_data["content_hash"],
                "fetch_timestamp": page_data["fetch_timestamp"],
                "clean_text": clean_text,
                "word_count": word_count,
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Error processing page {page_data.get('url')}: {str(e)}")
            return None

