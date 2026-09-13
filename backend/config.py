from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='backend/.env', extra='ignore')
    ai_provider: Literal['mock', 'openai'] = 'mock'
    openai_api_key: str = ''
    openai_model: str = 'gpt-5-mini'
    embedding_model: str = 'text-embedding-3-small'
    cors_origins: list[str] = [
        'http://127.0.0.1:5173', 'http://localhost:5173',  # vite dev server
        'http://127.0.0.1:5179', 'http://localhost:5179',  # playwright e2e (separate port so it doesn't clash with dev)
    ]
    session_ttl_seconds: int = 86400
    max_upload_bytes: int = 3145728
    max_image_pixels: int = 20000000
    max_items: int = 20
    max_sessions: int = 100
    max_steps: int = 100
    max_messages: int = 50
    max_provider_calls: int = 160
    global_provider_calls: int = 1000
    # Vision extraction with detail='high' on a real (non-tiny) photo can take
    # well over 45s; a real upload timed out here in practice with the old
    # default and max_retries=0, failing the whole analysis with zero items.
    request_timeout_seconds: float = 90
    openai_max_retries: int = 2
    data_dir: Path = Path('backend/data')
    chroma_host: str = ''
    chroma_port: int = 8000
    collection_name: str = 'food-openai-512'
    langfuse_enabled: bool = False


    retrieval_mode: Literal['bm25', 'similarity', 'mmr', 'hybrid'] = 'bm25'
    reranker: Literal['none', 'bge'] = 'none'
    chunk_size: Literal[256, 512, 1024] = 512
    top_k: Literal[3, 5, 10] = 5
    bge_revision: str = 'main'
    reranker_revision: str = 'main'
    langfuse_public_key: str = ''
    langfuse_secret_key: str = ''
    langfuse_base_url: str = 'https://cloud.langfuse.com'
