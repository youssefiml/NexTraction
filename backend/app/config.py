"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"
    log_level: str = "INFO"
    
    # API Keys
    openai_api_key: str = ""
    gemini_api_key: str = ""
    
    # Vector Store
    vector_store_path: str = "./data/vector_store"
    faiss_index_path: str = "./data/faiss_index"
    
    # Crawler Configuration
    max_pages: int = 100
    max_depth: int = 3
    request_timeout: int = 30
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 NexTraction/2.0"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    
    # Content Processing
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_length: int = 100
    
    # Answer Generation
    top_k_chunks: int = 5
    confidence_threshold: float = 0.7
    max_excerpt_length: int = 25
    
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "nextraction"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # CORS - Allow all origins for API-only service
    cors_origins: Union[List[str], str] = ["*"]
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )


settings = Settings()

