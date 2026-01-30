"""Discord Welcome Bot - Main entry point."""

import logging
import signal
import sys

from discord_welcome_bot.bot import WelcomeBot
from discord_welcome_bot.config import settings


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Reduce noise from discord.py internals
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)


def main() -> None:
    """Main entry point for the Discord Welcome Bot."""
    setup_logging()
    logger = logging.getLogger(__name__)

    bot = WelcomeBot()

    # Handle graceful shutdown
    def shutdown_handler(signum: int, frame: object) -> None:
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        bot.loop.create_task(bot.close())

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Starting Discord Welcome Bot...")

    try:
        bot.run(settings.discord_token, log_handler=None)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
