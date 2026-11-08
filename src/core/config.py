import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Tarihte Bugün Botu (Elite Edition)"
    VERSION: str = "4.1.0"
    DEBUG: bool = False
    DRY_RUN: bool = False  # If True, no tweets will be sent
    
    # Telegram API Credentials
    TELEGRAM_BOT_TOKEN: Optional[SecretStr] = None
    TELEGRAM_CHANNEL_ID: Optional[str] = None
    
    # Threads API Credentials
    THREADS_ACCESS_TOKEN: Optional[SecretStr] = None
    THREADS_USER_ID: Optional[SecretStr] = None
    
    # AI Provider (OpenRouter)
    OPENROUTER_API_KEY: Optional[SecretStr] = None
    # Free-model cascade for source-bound generation (Gemini first when GEMINI_API_KEY is set).
    AI_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    BACKUP_MODEL: str = "google/gemma-4-31b-it:free"
    # Comma-separated models that reject the "reasoning" request parameter
    MODELS_WITHOUT_REASONING_PARAM: str = ""
    # Google AI Studio (Gemini). Key is read from GEMINI_API_KEY; without it the provider is skipped.
    GEMINI_API_KEY: Optional[SecretStr] = None
    # Empty means Gemini is skipped. Set to a model id verified to return Turkish text.
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # Thinking control for Gemini 3.x models (thinkingLevel); Gemini 2.x uses thinkingBudget 0.
    GEMINI_THINKING_LEVEL: str = "minimal"
    
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

settings = Settings(_env_file=None if os.getenv("ZAMANIN_ANALYTICS_CLI") == "1" else ".env")
