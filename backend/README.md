# NexTraction 2 Backend

FastAPI-based backend for NexTraction 2 RAG pipeline.

## Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set environment variables
copy .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload
```

### Production

```bash
# Using Gunicorn with Uvicorn workers
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

- `POST /api/ingest` - Start content ingestion
- `GET /api/ingest/{job_id}` - Get job status
- `POST /api/ask` - Ask a question
- `GET /api/health` - Health check
- `GET /api/metrics` - System metrics
- `GET /docs` - Interactive API documentation
- `GET /redoc` - ReDoc documentation

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_crawler.py -v
```

## Project Structure

```
app/
├── main.py              # Application entry point
├── config.py            # Configuration
├── routers/             # API endpoints
│   ├── ingest.py
│   ├── ask.py
│   └── metrics.py
├── services/            # Business logic
│   ├── crawler.py
│   ├── content_processor.py
│   ├── vector_store.py
│   ├── embeddings.py
│   ├── answer_generator.py
│   └── ingestion_service.py
├── models/              # Data models
│   ├── schemas.py
│   └── database.py
└── utils/               # Utilities
    ├── dependencies.py
    └── logging_config.py
```

## Configuration

Edit `app/config.py` or set environment variables:

```python
# Crawler
MAX_PAGES = 100
MAX_DEPTH = 3
REQUEST_TIMEOUT = 30

# Content Processing
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Answer Generation
TOP_K_CHUNKS = 5
CONFIDENCE_THRESHOLD = 0.7
```

## Database

MongoDB is used for storing jobs, pages, chunks, and query logs.

```bash
# .env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=nextraction
```

For installation and setup, see [MONGODB_SETUP.md](../MONGODB_SETUP.md)

## Monitoring

- Logs: JSON format in production, human-readable in development
- Metrics: Prometheus-compatible at `/api/metrics`
- Health: `/api/health` for liveness/readiness probes

## Dependencies

Key dependencies:
- FastAPI - Web framework
- Uvicorn - ASGI server
- FAISS - Vector search
- SQLAlchemy - ORM
- httpx - Async HTTP client
- BeautifulSoup4 - HTML parsing
- OpenAI/Google AI - Embeddings & generation

See `requirements.txt` for full list.

