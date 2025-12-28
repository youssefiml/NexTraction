"""Tests for web crawler."""
import pytest
from app.services.crawler import WebCrawler


@pytest.mark.asyncio
async def test_crawler_fetch_single_page():
    """Test fetching a single page."""
    crawler = WebCrawler(max_pages=1, max_depth=0)
    
    # Use a reliable test URL
    result = await crawler.fetch_page("https://example.com")
    
    assert result is not None
    assert "url" in result
    assert "html_content" in result
    assert "title" in result
    assert "Example Domain" in result["title"]


@pytest.mark.asyncio
async def test_crawler_domain_allowlist():
    """Test domain allowlist filtering."""
    crawler = WebCrawler(
        domain_allowlist=["example.com"],
        max_pages=5
    )
    
    assert crawler._is_allowed_domain("https://example.com/page")
    assert not crawler._is_allowed_domain("https://other.com/page")


@pytest.mark.asyncio
async def test_crawler_url_normalization():
    """Test URL normalization."""
    crawler = WebCrawler()
    
    url1 = crawler._normalize_url("https://example.com/page/")
    url2 = crawler._normalize_url("https://example.com/page")
    
    assert url1 == url2
    assert url1 == "https://example.com/page"


@pytest.mark.asyncio
async def test_crawler_respects_max_pages():
    """Test that crawler respects max_pages limit."""
    crawler = WebCrawler(max_pages=3, max_depth=1)
    
    results = await crawler.crawl(["https://example.com"])
    
    assert len(results) <= 3

