from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        env_prefix="MONITE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 👈 ignora cualquier variable que no esté declarada
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./monite.db",
        description="SQLAlchemy database connection string."
    )

    # Telegram
    telegram_token: str | None = Field(default=None)
    telegram_chat_id: str | None = Field(default=None)
    telegram_cooldown_seconds: int = Field(default=900)

    # API
    api_base_path: str = Field(default="/api")

    # Scheduler
    scheduler_timezone: str = Field(default="UTC")

    # Health check interval in seconds. Controls how often the system
    # checks the online/offline status of all hosts. Default is 300
    # seconds (5 minutes).
    health_interval_seconds: int = Field(default=300, description="Interval between health checks in seconds")

    # Timeout in seconds for a health check operation. Not currently
    # used directly but reserved for future enhancements where a
    # TCP probe may be implemented.
    health_timeout_seconds: int = Field(default=3, description="Timeout for health check connection attempts")

    # Daily summary schedule. The report will be sent via Telegram
    # each day at the configured hour and minute (UTC). Values are
    # integers in 24-hour time. Defaults to 09:00.
    telegram_daily_summary_hour: int = Field(default=9, description="Hour (0-23) for daily summary")
    telegram_daily_summary_minute: int = Field(default=0, description="Minute (0-59) for daily summary")

settings = Settings()
