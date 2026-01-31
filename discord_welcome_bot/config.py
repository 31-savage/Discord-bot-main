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

    # Log level
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Whether to subscribe to member events for large guilds (>75k members)
    # See: https://discordpy-self.readthedocs.io/en/latest/guild_subscriptions.html
    subscribe_to_member_events: bool = True


settings = Settings()  # type: ignore[call-arg]
