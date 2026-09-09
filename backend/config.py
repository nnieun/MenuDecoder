from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='backend/.env', extra='ignore')
    ai_provider: Literal['mock', 'openai'] = 'mock'
    openai_api_key: str = ''
    openai_model: str = 'gpt-5-mini'
    embedding_model: str = 'text-embedding-3-small'
    cors_origins: list[str] = ['http://127.0.0.1:5173', 'http://localhost:5173']
    session_ttl_seconds: int = 86400
    max_upload_bytes: int = 3145728
    max_image_pixels: int = 20000000
    max_items: int = 20
    max_sessions: int = 100
    max_steps: int = 100
    max_messages: int = 50
    max_provider_calls: int = 160
    global_provider_calls: int = 1000
    request_timeout_seconds: float = 45
    data_dir: Path = Path('backend/data')
    chroma_host: str = ''
    chroma_port: int = 8000
    collection_name: str = 'food-openai-512'
    langfuse_enabled: bool = False

