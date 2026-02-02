"""Discord Welcome Bot - Configuration settings."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Discord user token (required)
    discord_token: str

    # Group DM channel ID for notifications (required)
    # Create a group DM and get its ID
    notification_channel_id: int

    # Log level
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Command prefix for text commands
    command_prefix: str = "!"


settings = Settings()  # type: ignore[call-arg]
