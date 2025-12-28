"""Answer generation service with grounded responses and citations."""
from typing import List, Dict, Tuple, Optional
import logging
from openai import OpenAI
import google.generativeai as genai
import re

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generate grounded answers with citations."""
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: str = None,
        model: str = None,
        max_excerpt_length: int = 25
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.max_excerpt_length = max_excerpt_length
        
        if self.provider == "openai":
            self.model = model or "gpt-4o-mini"
            self.client = OpenAI(api_key=api_key) if api_key else None
        elif self.provider == "gemini":
            self.model = model or "gemini-pro"
            if api_key:
                genai.configure(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _create_context(self, chunks: List[Tuple[Dict, float]]) -> str:
        """Create context from retrieved chunks."""
        context_parts = []
        for i, (chunk, score) in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}] (URL: {chunk['url']}, Title: {chunk['title']})\n"
                f"{chunk['content']}\n"
            )
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build prompt for answer generation."""
        return f"""You are a research assistant that provides evidence-based answers. 

STRICT RULES:
1. Answer ONLY based on the provided sources below
2. Include at least one citation [Source N] per paragraph
3. If information is insufficient, explicitly state what's missing
4. Never fabricate or assume information not in the sources
5. Keep citations concise (max 25 words from source)

SOURCES:
{context}

QUESTION: {question}

Provide a well-structured answer with inline citations [Source N]. If you cannot fully answer the question, explain what information is missing."""
    
    async def generate_answer(
        self,
        question: str,
        retrieved_chunks: List[Tuple[Dict, float]],
        min_confidence: float = 0.7
    ) -> Dict:
        """Generate grounded answer with citations."""
        if not retrieved_chunks:
            return {
                "answer": "I don't have enough information to answer this question.",
                "citations": [],
                "confidence": 0.0,
                "missing_information": ["No relevant sources found"]
            }
        
        # Create context
        context = self._create_context(retrieved_chunks)
        prompt = self._build_prompt(question, context)
        
        # Generate answer
        try:
            if self.provider == "openai":
                answer_text = await self._generate_openai(prompt)
            elif self.provider == "gemini":
                answer_text = await self._generate_gemini(prompt)
            else:
                answer_text = "Error: Unsupported provider"
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return {
                "answer": "An error occurred while generating the answer.",
                "citations": [],
                "confidence": 0.0,
                "missing_information": ["Generation error"]
            }
        
        # Extract citations and verify
        citations = self._extract_citations(answer_text, retrieved_chunks)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            answer_text,
            citations,
            retrieved_chunks
        )
        
        # Identify missing information
        missing_info = None
        if confidence < min_confidence:
            missing_info = self._identify_missing_information(
                question,
                answer_text,
                retrieved_chunks
            )
        
        return {
            "answer": answer_text,
            "citations": citations,
            "confidence": confidence,
            "missing_information": missing_info
        }
    
    async def _generate_openai(self, prompt: str) -> str:
        """Generate answer using OpenAI."""
        if not self.client:
            return "OpenAI client not configured. Please add your API key."
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a research assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    async def _generate_gemini(self, prompt: str) -> str:
        """Generate answer using Gemini."""
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 1000}
        )
        return response.text
    
    def _extract_citations(
        self,
        answer: str,
        chunks: List[Tuple[Dict, float]]
    ) -> List[Dict]:
        """Extract and format citations from answer."""
        citations = []
        citation_pattern = r'\[Source (\d+)\]'
        
        # Find all citation references
        matches = re.finditer(citation_pattern, answer)
        cited_sources = set()
        
        for match in matches:
            source_num = int(match.group(1)) - 1
            if 0 <= source_num < len(chunks) and source_num not in cited_sources:
                chunk, score = chunks[source_num]
                
                # Extract excerpt (first N words)
                words = chunk['content'].split()
                excerpt_words = words[:self.max_excerpt_length]
                excerpt = " ".join(excerpt_words)
                if len(words) > self.max_excerpt_length:
                    excerpt += "..."
                
                citations.append({
                    "url": chunk['url'],
                    "title": chunk['title'],
                    "excerpt": excerpt,
                    "chunk_id": chunk['id'],
                    "relevance_score": score
                })
                cited_sources.add(source_num)
        
        return citations
    
    def _calculate_confidence(
        self,
        answer: str,
        citations: List[Dict],
        chunks: List[Tuple[Dict, float]]
    ) -> float:
        """Calculate confidence score."""
        if not chunks:
            return 0.0
        
        # Factors for confidence:
        # 1. Number of citations (more is better, up to a point)
        citation_score = min(len(citations) / 3.0, 1.0)  # Normalized to 3 citations
        
        # 2. Average relevance score of top chunks
        avg_relevance = sum(score for _, score in chunks[:3]) / min(len(chunks), 3)
        
        # 3. Answer length (too short may indicate insufficient info)
        word_count = len(answer.split())
        length_score = min(word_count / 100.0, 1.0)  # Normalized to 100 words
        
        # Combined confidence score
        confidence = (citation_score * 0.4 + avg_relevance * 0.4 + length_score * 0.2)
        
        return round(confidence, 2)
    
    def _identify_missing_information(
        self,
        question: str,
        answer: str,
        chunks: List[Tuple[Dict, float]]
    ) -> List[str]:
        """Identify what information is missing."""
        missing = []
        
        # Check for uncertainty markers in answer
        uncertainty_markers = [
            "i don't have", "insufficient", "unclear", "not enough",
            "missing", "cannot determine", "unable to"
        ]
        
        answer_lower = answer.lower()
        for marker in uncertainty_markers:
            if marker in answer_lower:
                # Extract the sentence containing the marker
                sentences = answer.split('.')
                for sentence in sentences:
                    if marker in sentence.lower():
                        missing.append(sentence.strip())
                break
        
        if not missing:
            missing.append("Coverage appears incomplete based on available sources")
        
        return missing

