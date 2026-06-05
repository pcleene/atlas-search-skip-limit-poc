"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # MongoDB
    mongodb_uri: str = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>"
    mongodb_db_name: str = "PartsDistributor"
    atlas_search_index_name: str = "parts_search_index"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8001  # V2 uses port 8001
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080", "http://localhost:8081", "http://127.0.0.1:8080", "http://127.0.0.1:8081"]

    # Pricing defaults
    default_forex_rate: float = 4.2432
    default_markup: float = 0.2
    default_user_currency: str = "MYR"
    default_user_location: str = "MY"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
