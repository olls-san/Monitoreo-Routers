"""Application settings for MoniTe Web.

This module defines configuration using Pydantic's `BaseSettings` class. All
configuration can be supplied via environment variables, ensuring sensible
defaults for local development while allowing values to be overridden in
production environments. Settings are instantiated once at import time.

Notable settings include:
    * `database_url` – the SQLAlchemy database URL. Defaults to an in-memory
      SQLite database for development.
    * `scheduler_timezone` – timezone string used by APScheduler. Defaults
      to the user's locale (America/New_York) as specified in the requirements.
    * `telegram_token` & `telegram_chat_id` – credentials used to send
      notifications. If unset the Telegram integration is effectively
      disabled.
    * `telegram_cooldown_seconds` – minimum seconds between identical
      notifications per host.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./monite.db",
        description="SQLAlchemy database URL. Uses SQLite by default.",
    )
    database_echo: bool = Field(
        default=False,
        description="If true, SQLAlchemy will log all generated SQL statements.",
    )

    # APScheduler configuration
    scheduler_timezone: str = Field(
        default="America/New_York",
        description="Timezone used for scheduling automation rules.",
    )

    # HTTP client timeouts
    request_timeout: float = Field(
        default=10.0,
        description="Default timeout in seconds for outgoing HTTP requests.",
    )

    # Telegram notifications
    telegram_token: str | None = Field(
        default=None,
        description="Bot token for sending Telegram alerts. If unset, alerts are disabled.",
    )
    telegram_chat_id: str | None = Field(
        default=None,
        description="Chat ID to which Telegram alerts should be sent.",
    )
    telegram_cooldown_seconds: int = Field(
        default=300,
        description="Minimum number of seconds between duplicate Telegram alerts per host and alert type.",
    )

    class Config:
        env_prefix = "MONITE_"


# Instantiate a singleton of settings for import throughout the app
settings = Settings()