"""
Configuration settings for the Cardano Index API
"""

from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""
    
    # API Configuration
    app_name: str = "Cardano Index API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Authentication
    api_keys: List[str] = ["demo-api-key-please-change"]  # Default key for development
    
    # External API Configuration
    muesliswap_base_url: str = "https://api-v2.muesliswap.com"
    muesliswap_timeout: int = 30
    
    # Data Configuration
    index_config_path: str = "config/indexes.json"
    cache_ttl_seconds: int = 300  # 5 minutes cache for price data
    
    # Database Configuration
    database_url: str = "sqlite:///./cardano_index_data.db"
    
    # Historical Data Querier Configuration
    querier_enabled: bool = True
    querier_interval_minutes: int = 15  # How often to collect historical data
    querier_startup_delay_seconds: int = 30  # Wait before starting querier
    querier_retry_attempts: int = 3
    querier_timeout_seconds: int = 300  # 5 minutes timeout for each run
    
    class Config:
        env_file = ".env"
        env_prefix = "CARDANO_INDEX_"

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
