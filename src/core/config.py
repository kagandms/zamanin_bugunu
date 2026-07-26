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
    
    # Telegram API Credentials
    TELEGRAM_BOT_TOKEN: SecretStr
    TELEGRAM_CHANNEL_ID: str
    
    # Threads API Credentials
    THREADS_ACCESS_TOKEN: SecretStr
    THREADS_USER_ID: SecretStr
    
    # AI Provider (OpenRouter)
    OPENROUTER_API_KEY: SecretStr
    # Primary Model: Auto-routed to best available free model
    AI_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    # Backup Model: Auto-routed to best available free model
    BACKUP_MODEL: str = "google/gemini-2.0-pro-exp-02-05:free"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///bot_data.db"
    
    # Bot Configuration
    MAX_THREAD_LENGTH: int = 500
    TELEGRAM_MAX_CAPTION_LENGTH: int = 1024
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
