import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Tarihte Bugün Botu (Elite Edition)"
    VERSION: str = "4.0.0"
    DEBUG: bool = False
    DRY_RUN: bool = False  # If True, no tweets will be sent
    
    # Twitter API Credentials (V1 & V2)
    API_KEY: SecretStr
    API_SECRET: SecretStr
    ACCESS_TOKEN: SecretStr
    ACCESS_TOKEN_SECRET: SecretStr
    BEARER_TOKEN: Optional[SecretStr] = None
    
    # AI Provider (OpenRouter)
    OPENROUTER_API_KEY: SecretStr
    # Primary Model: Nous Hermes 3 405B (Uncensored & Powerful)
    AI_MODEL: str = "nousresearch/hermes-3-llama-3.1-405b:free"
    # Backup Model: Llama 3.3 70B (Free)
    BACKUP_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///bot_data.db"
    
    # Bot Configuration
    MAX_TWEET_LENGTH: int = 280
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5
    
    # Target Timezone
    TIMEZONE: str = "Europe/Istanbul"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

settings = Settings()
