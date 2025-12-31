"""Tests for content processor."""
import pytest
from app.services.content_processor import ContentProcessor


def test_clean_html():
    """Test HTML cleaning."""
    processor = ContentProcessor()
    
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <nav>Navigation</nav>
            <main>
                <h1>Main Content</h1>
                <p>This is a paragraph.</p>
            </main>
            <footer>Footer</footer>
            <script>console.log('test');</script>
        </body>
    </html>
    """
    
    clean_text = processor.clean_html(html)
    
    assert "Main Content" in clean_text
    assert "This is a paragraph" in clean_text
    assert "Navigation" not in clean_text
    assert "Footer" not in clean_text
    assert "console.log" not in clean_text


def test_chunk_text():
    """Test text chunking."""
    processor = ContentProcessor(chunk_size=50, chunk_overlap=10)
    
    # Create text with exactly 100 words
    text = " ".join([f"word{i}" for i in range(100)])
    
    chunks = processor.chunk_text(text, "https://test.com", "Test Title")
    
    assert len(chunks) > 0
    assert all("url" in chunk for chunk in chunks)
    assert all("title" in chunk for chunk in chunks)
    assert all("content" in chunk for chunk in chunks)
    
    # Check overlap
    if len(chunks) > 1:
        # Some words from chunk 1 should appear in chunk 2
        chunk1_words = set(chunks[0]["content"].split())
        chunk2_words = set(chunks[1]["content"].split())
        overlap = chunk1_words & chunk2_words
        assert len(overlap) > 0


def test_process_page():
    """Test full page processing."""
    processor = ContentProcessor()
    
    # Need at least 50 words to pass the minimum content check
    page_data = {
        "url": "https://test.com",
        "title": "Test Page",
        "html_content": """
            <html>
                <body>
                    <h1>Test Title</h1>
                    <p>This is the first paragraph with some content that provides useful information to readers.</p>
                    <p>This is the second paragraph with more content that explains additional details about the topic.</p>
                    <p>This is the third paragraph with even more content that continues the explanation further.</p>
                    <p>This is the fourth paragraph with extra content to ensure we have enough words for processing.</p>
                    <p>This is the fifth paragraph that adds more substance to the page content for testing purposes.</p>
                    <p>Finally, this last paragraph ensures we have well over fifty words in total for the test.</p>
                </body>
            </html>
        """,
        "content_hash": "abc123",
        "fetch_timestamp": "2025-12-24T10:00:00"
    }
    
    result = processor.process_page(page_data)
    
    assert result is not None
    assert "chunks" in result
    assert len(result["chunks"]) > 0
    assert result["url"] == "https://test.com"


def test_skip_short_content():
    """Test that very short pages are skipped."""
    processor = ContentProcessor()
    
    page_data = {
        "url": "https://test.com",
        "title": "Short",
        "html_content": "<html><body>Short</body></html>",
        "content_hash": "abc123",
        "fetch_timestamp": "2025-12-24T10:00:00"
    }
    
    result = processor.process_page(page_data)
    
    assert result is None  # Too short, should be skipped

