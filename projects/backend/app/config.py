"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./b2b_growth.db"
    database_url_sync: str = "sqlite:///./b2b_growth.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # SerpAPI
    serpapi_key: str = ""

    # External APIs
    opencorporates_api_key: str = ""
    importyeti_api_key: str = ""

    # Proxy
    proxy_list: str = ""

    # App
    frontend_url: str = "http://localhost:3000"
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
