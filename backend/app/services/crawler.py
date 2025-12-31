"""Web crawler service."""
import httpx
import asyncio
from typing import List, Set, Optional, Dict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import logging
import hashlib

logger = logging.getLogger(__name__)


class WebCrawler:
    """Web crawler with domain restrictions and depth limits."""
    
    def __init__(
        self,
        domain_allowlist: Optional[List[str]] = None,
        max_pages: int = 50,
        max_depth: int = 2,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: str = "NexTraction/2.0"
    ):
        self.domain_allowlist = set(domain_allowlist) if domain_allowlist else None
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is in allowlist."""
        if not self.domain_allowlist:
            return True
        domain = urlparse(url).netloc
        return any(allowed in domain for allowed in self.domain_allowlist)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove fragment and trailing slash
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized
    
    async def fetch_page(self, url: str) -> Optional[Dict]:
        """Fetch a single page with retries."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")
                        if "text/html" not in content_type:
                            logger.warning(f"Skipping non-HTML content: {url}")
                            return None
                        
                        html_content = response.text
                        soup = BeautifulSoup(html_content, "lxml")
                        
                        # Extract title
                        title = soup.title.string if soup.title else url
                        
                        # Extract links for crawling
                        links = []
                        for link in soup.find_all("a", href=True):
                            absolute_url = urljoin(url, link["href"])
                            normalized = self._normalize_url(absolute_url)
                            if self._is_allowed_domain(normalized):
                                links.append(normalized)
                        
                        # Calculate content hash for deduplication
                        content_hash = hashlib.md5(html_content.encode()).hexdigest()
                        
                        return {
                            "url": url,
                            "title": title.strip() if title else "",
                            "html_content": html_content,
                            "links": links,
                            "content_hash": content_hash,
                            "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                            "status_code": response.status_code,
                        }
                    else:
                        logger.warning(f"HTTP {response.status_code} for {url}")
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{self.max_retries})")
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code} for {url}: {str(e)}")
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}", exc_info=True)
                
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        self.failed_urls.add(url)
        return None
    
    async def crawl(
        self,
        seed_urls: List[str],
        progress_callback=None
    ) -> List[Dict]:
        """Crawl starting from seed URLs."""
        results = []
        queue = [(url, 0) for url in seed_urls]  # (url, depth)
        seen_hashes = set()
        
        while queue and len(results) < self.max_pages:
            url, depth = queue.pop(0)
            
            # Skip if already visited or beyond max depth
            normalized_url = self._normalize_url(url)
            if normalized_url in self.visited_urls or depth > self.max_depth:
                continue
            
            # Check domain allowlist
            if not self._is_allowed_domain(normalized_url):
                continue
            
            self.visited_urls.add(normalized_url)
            
            # Fetch page
            logger.info(f"Fetching {normalized_url} (depth: {depth})")
            page_data = await self.fetch_page(normalized_url)
            
            if page_data:
                # Check for duplicate content
                if page_data["content_hash"] in seen_hashes:
                    logger.info(f"Duplicate content detected: {normalized_url}")
                    continue
                
                seen_hashes.add(page_data["content_hash"])
                results.append(page_data)
                
                # Add new links to queue if not at max depth
                if depth < self.max_depth and len(results) < self.max_pages:
                    for link in page_data["links"]:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
                
                # Progress callback
                if progress_callback:
                    await progress_callback(len(results), min(len(queue) + len(results), self.max_pages))
            
            # Polite crawling delay
            await asyncio.sleep(1)
        
        logger.info(f"Crawl completed: {len(results)} pages fetched, {len(self.failed_urls)} failed")
        return results

