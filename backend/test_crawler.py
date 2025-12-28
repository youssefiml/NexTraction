"""Test crawler directly."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.crawler import WebCrawler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_crawler():
    """Test the crawler."""
    print("Testing crawler with example.com...")
    
    crawler = WebCrawler(
        max_pages=3,
        max_depth=1,
        timeout=30,
        max_retries=3
    )
    
    urls = ["https://example.com"]
    pages = await crawler.crawl(urls)
    
    print(f"\nResults: {len(pages)} pages fetched")
    for i, page in enumerate(pages, 1):
        print(f"\nPage {i}:")
        print(f"  URL: {page['url']}")
        print(f"  Title: {page['title']}")
        print(f"  Content length: {len(page['html_content'])} chars")
    
    print(f"\nFailed URLs: {crawler.failed_urls}")

if __name__ == "__main__":
    asyncio.run(test_crawler())