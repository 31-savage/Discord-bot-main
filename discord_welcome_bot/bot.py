"""Discord Welcome Bot - Main bot class with event handlers and commands."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import discord
from discord.ext import commands

from discord_welcome_bot.config import settings

logger = logging.getLogger(__name__)

# File to persist all bot config (uses configurable data directory)
CONFIG_FILE = settings.data_dir / "bot_config.json"


def load_config() -> dict[str, Any]:
    """Load all config from file."""
    logger.info(f"Loading config from {CONFIG_FILE.absolute()}")
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                logger.info(f"Loaded config: {data}")
                return data
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    else:
        logger.info("Config file does not exist, using defaults")
    return {}


def save_config(config: dict[str, Any]) -> None:
    """Save all config to file."""
    try:
        # Ensure the data directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to {CONFIG_FILE.absolute()}: {config}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


class WelcomeBot(commands.Bot):
    """Discord self-bot that sends welcome messages when users join."""

    def __init__(self) -> None:
        # Load config first
        self._config = load_config()

        # Get prefix from config or fall back to env/default
        prefix = self._config.get("prefix", settings.command_prefix)

        super().__init__(
            command_prefix=prefix,
            self_bot=True,
            # Subscribe to guild events automatically for guilds < 75k members
            guild_subscriptions=True,
            # Chunk guilds at startup to get full member list
            chunk_guilds_at_startup=True,
        )
        self._notification_channel: discord.GroupChannel | discord.TextChannel | None = None

        # Load settings from config file (with env var fallbacks)
        self._monitored_guilds: set[int] = set(self._config.get("monitored_guilds", []))
        self._monitor_all: bool = self._config.get("monitor_all", False)
        self._notification_channel_id: int = self._config.get(
            "notification_channel_id", settings.notification_channel_id
        )

    def _save_config(self) -> None:
        """Save current config to file."""
        self._config["monitored_guilds"] = list(self._monitored_guilds)
        self._config["monitor_all"] = self._monitor_all
        self._config["notification_channel_id"] = self._notification_channel_id
        self._config["prefix"] = self.command_prefix
        save_config(self._config)

    @property
    def monitored_guilds(self) -> set[int]:
        """Get the set of monitored guild IDs."""
        return self._monitored_guilds

    @property
    def monitor_all(self) -> bool:
        """Check if monitoring all servers."""
        return self._monitor_all

    @property
    def notification_channel_id(self) -> int:
        """Get the notification channel ID."""
        return self._notification_channel_id

    def is_guild_monitored(self, guild_id: int) -> bool:
        """Check if a guild is being monitored.

        If monitor_all is True, all guilds are monitored.
        Otherwise, only guilds in the monitored list are monitored.
        """
        if self._monitor_all:
            return True
        return guild_id in self._monitored_guilds

    def add_monitored_guild(self, guild_id: int) -> None:
        """Add a guild to the monitored list."""
        self._monitored_guilds.add(guild_id)
        self._save_config()

    def remove_monitored_guild(self, guild_id: int) -> None:
        """Remove a guild from the monitored list."""
        self._monitored_guilds.discard(guild_id)
        self._save_config()

    def clear_monitored_guilds(self) -> None:
        """Clear all monitored guilds and disable monitor all."""
        self._monitored_guilds.clear()
        self._monitor_all = False
        self._save_config()

    def set_monitor_all(self, enabled: bool) -> None:
        """Enable or disable monitoring all servers."""
        self._monitor_all = enabled
        self._save_config()

    def set_notification_channel_id(self, channel_id: int) -> None:
        """Set the notification channel ID."""
        self._notification_channel_id = channel_id
        self._save_config()

    def set_prefix(self, prefix: str) -> None:
        """Set the command prefix."""
        self.command_prefix = prefix
        self._save_config()

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        # Add commands
        self.add_command(cmd_servers)
        self.add_command(cmd_monitor)
        self.add_command(cmd_unmonitor)
        self.add_command(cmd_monitored)
        self.add_command(cmd_monitorall)
        self.add_command(cmd_clear)
        self.add_command(cmd_config)
        self.add_command(cmd_help_welcome)

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        if self.user is None:
            logger.error("Bot user is None after ready event")
            return

        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info(f"Data directory: {settings.data_dir.absolute()}")
        logger.info(f"Config file: {CONFIG_FILE.absolute()}")

        # Get notification channel
        await self._setup_notification_channel()

        # Log monitoring status
        if self._monitor_all:
            logger.info(f"Monitoring ALL guilds ({len(self.guilds)} servers)")
        elif self._monitored_guilds:
            logger.info(f"Monitoring {len(self._monitored_guilds)} specific guild(s)")
        else:
            logger.info("Not monitoring any guilds (use !monitor <guild_id> or !monitorall)")

    async def _setup_notification_channel(self) -> None:
        """Setup the notification channel."""
        try:
            channel = await self.fetch_channel(self._notification_channel_id)
            if isinstance(channel, (discord.GroupChannel, discord.TextChannel, discord.DMChannel)):
                self._notification_channel = channel  # type: ignore
                logger.info(
                    f"Notification channel set: {channel} (ID: {self._notification_channel_id})"
                )
            else:
                logger.error(f"Channel {self._notification_channel_id} is not a valid text channel")
        except Exception as e:
            logger.error(
                f"Failed to fetch notification channel {self._notification_channel_id}: {e}"
            )

    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins a guild."""
        # Check if this guild is being monitored
        if not self.is_guild_monitored(member.guild.id):
            logger.debug(f"Ignoring join in non-monitored guild: {member.guild.name}")
            return

        logger.info(f"New member joined: {member} in {member.guild.name}")

        try:
            if self._notification_channel is None:
                logger.error("Notification channel not available")
                return

            message = self._create_join_notification_text(member)
            await self._notification_channel.send(message)
            logger.debug(f"Join notification sent for {member}")
        except discord.Forbidden:
            logger.error("Cannot send to notification channel - forbidden")
        except Exception as e:
            logger.error(f"Error sending join notification: {e}")

    def _create_join_notification_text(self, member: discord.Member) -> str:
        """Create a plain text notification for a new member."""
        guild = member.guild
        member_count = guild.member_count or len(guild.members)

        account_created = member.created_at
        now = datetime.now(timezone.utc)
        account_age = now - account_created

        age_str = f"{account_age.days} days, {account_age.seconds // 3600} hours"

        # Build warning if new account
        warning = ""
        if account_age.days < 7:
            warning = f"\n:warning: **Warning:** New account - only {account_age.days} day(s) old!"

        message = f"""**New Member Joined**

**Server:** {guild.name}
**Username:** {member} ({member.mention})
**User ID:** `{member.id}`
**Member #:** {member_count}
**Account Created:** <t:{int(account_created.timestamp())}:F> (<t:{int(account_created.timestamp())}:R>)
**Account Age:** {age_str}{warning}

_Server ID: `{guild.id}`_"""

        return message

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the user joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        if self._notification_channel:
            try:
                message = f"""**Joined New Server**

**Server:** {guild.name}
**Server ID:** `{guild.id}`
**Members:** {guild.member_count}"""
                await self._notification_channel.send(message)
            except Exception as e:
                logger.error(f"Failed to send guild join notification: {e}")

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,  # type: ignore
    ) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
        else:
            logger.error(f"Command error: {error}")


# ============ Commands ============
# Using plain text responses instead of embeds for better compatibility


@commands.command(name="servers")
async def cmd_servers(ctx: commands.Context) -> None:  # type: ignore
    """List all servers the bot is in."""
    bot: WelcomeBot = ctx.bot  # type: ignore

    if not bot.guilds:
        await ctx.send("Not in any servers.")
        return

    lines = [f"**Server List** - Connected to {len(bot.guilds)} server(s)\n"]

    for i, guild in enumerate(bot.guilds, 1):
        monitored = "Yes" if bot.is_guild_monitored(guild.id) else "No"
        lines.append(
            f"{i}. **{guild.name}** | ID: `{guild.id}` | Members: {guild.member_count} | Monitored: {monitored}"
        )

    message = "\n".join(lines)
    # Split into chunks if too long
    if len(message) > 2000:
        message = message[:1997] + "..."

    await ctx.send(message)


@commands.command(name="monitor")
async def cmd_monitor(ctx: commands.Context, guild_id: int) -> None:  # type: ignore
    """Add a server to the monitored list.

    Usage: !monitor <guild_id>
    """
    bot: WelcomeBot = ctx.bot  # type: ignore

    guild = bot.get_guild(guild_id)
    if guild is None:
        await ctx.send(
            f"Server with ID `{guild_id}` not found. Use `{bot.command_prefix}servers` to see available servers."
        )
        return

    bot.add_monitored_guild(guild_id)
    await ctx.send(f"Now monitoring **{guild.name}** (`{guild_id}`)")


@commands.command(name="unmonitor")
async def cmd_unmonitor(ctx: commands.Context, guild_id: int) -> None:  # type: ignore
    """Remove a server from the monitored list.

    Usage: !unmonitor <guild_id>
    """
    bot: WelcomeBot = ctx.bot  # type: ignore

    guild = bot.get_guild(guild_id)
    guild_name = guild.name if guild else "Unknown"

    bot.remove_monitored_guild(guild_id)
    await ctx.send(f"Stopped monitoring **{guild_name}** (`{guild_id}`)")


@commands.command(name="monitored")
async def cmd_monitored(ctx: commands.Context) -> None:  # type: ignore
    """List all monitored servers."""
    bot: WelcomeBot = ctx.bot  # type: ignore

    if bot.monitor_all:
        await ctx.send(f"**Monitoring ALL servers** ({len(bot.guilds)} servers)")
        return

    if not bot.monitored_guilds:
        await ctx.send(
            "No servers configured. **Monitoring nothing.** Use `!monitor <guild_id>` or `!monitorall` to start."
        )
        return

    lines = [f"**Monitored Servers** - {len(bot.monitored_guilds)} server(s)\n"]

    for guild_id in bot.monitored_guilds:
        guild = bot.get_guild(guild_id)
        name = guild.name if guild else "Unknown (left server?)"
        lines.append(f"- **{name}** | ID: `{guild_id}`")

    await ctx.send("\n".join(lines))


@commands.command(name="clear")
async def cmd_clear(ctx: commands.Context) -> None:  # type: ignore
    """Clear monitored list and disable monitor all."""
    bot: WelcomeBot = ctx.bot  # type: ignore
    bot.clear_monitored_guilds()
    await ctx.send("Cleared monitored list. **Now monitoring nothing.**")


@commands.command(name="monitorall")
async def cmd_monitorall(ctx: commands.Context) -> None:  # type: ignore
    """Monitor all servers."""
    bot: WelcomeBot = ctx.bot  # type: ignore
    bot.set_monitor_all(True)
    await ctx.send(f"**Now monitoring ALL servers** ({len(bot.guilds)} servers)")


@commands.command(name="config")
async def cmd_config(
    ctx: commands.Context, action: str = None, key: str = None, *, value: str = None
) -> None:  # type: ignore
    """Show or set configuration.

    Usage:
        !config - Show current config
        !config set prefix /
        !config set channel 123456789
    """
    bot: WelcomeBot = ctx.bot  # type: ignore

    # If no action, show current config
    if action is None:
        monitor_status = (
            f"**ALL servers** ({len(bot.guilds)})"
            if bot.monitor_all
            else f"**{len(bot.monitored_guilds)} specific server(s)**"
            if bot.monitored_guilds
            else "**Nothing**"
        )

        config_text = f"""**Current Configuration**

**Monitoring:** {monitor_status}
**Command Prefix:** `{bot.command_prefix}`
**Notification Channel:** `{bot.notification_channel_id}`
**Data Directory:** `{settings.data_dir.absolute()}`
**Config File:** `{CONFIG_FILE.absolute()}`
**Connected Servers:** {len(bot.guilds)}

**To change settings:**
`{bot.command_prefix}config set prefix <new_prefix>`
`{bot.command_prefix}config set channel <channel_id>`"""

        await ctx.send(config_text)
        return

    # Handle "set" action
    if action.lower() == "set":
        if key is None or value is None:
            await ctx.send(
                f"Usage: `{bot.command_prefix}config set <key> <value>`\nKeys: `prefix`, `channel`"
            )
            return

        key = key.lower()

        if key == "prefix":
            old_prefix = bot.command_prefix
            bot.set_prefix(value)
            await ctx.send(
                f"Prefix changed from `{old_prefix}` to `{value}`\nUse `{value}config` for future commands."
            )

        elif key == "channel":
            try:
                channel_id = int(value)
                old_channel = bot.notification_channel_id
                bot.set_notification_channel_id(channel_id)
                # Try to fetch the new channel
                await bot._setup_notification_channel()
                if bot._notification_channel:
                    await ctx.send(
                        f"Notification channel changed from `{old_channel}` to `{channel_id}`"
                    )
                else:
                    await ctx.send(
                        f"Channel ID set to `{channel_id}` but could not fetch channel. Please verify the ID."
                    )
            except ValueError:
                await ctx.send(f"Invalid channel ID: `{value}`. Must be a number.")

        else:
            await ctx.send(f"Unknown config key: `{key}`\nAvailable keys: `prefix`, `channel`")

    else:
        await ctx.send(
            f"Unknown action: `{action}`\nUse `{bot.command_prefix}config` to view or `{bot.command_prefix}config set <key> <value>` to change."
        )


@commands.command(name="whelp")
async def cmd_help_welcome(ctx: commands.Context) -> None:  # type: ignore
    """Show help for welcome bot commands."""
    bot: WelcomeBot = ctx.bot  # type: ignore
    prefix = bot.command_prefix

    help_text = f"""**Welcome Bot Commands**

**Monitoring:**
`{prefix}servers` - List all servers with monitoring status
`{prefix}monitor <guild_id>` - Monitor a specific server
`{prefix}unmonitor <guild_id>` - Stop monitoring a server
`{prefix}monitorall` - Monitor ALL servers
`{prefix}monitored` - List currently monitored servers
`{prefix}clear` - Stop monitoring everything

**Configuration:**
`{prefix}config` - Show current configuration
`{prefix}config set prefix <new_prefix>` - Change command prefix
`{prefix}config set channel <channel_id>` - Change notification channel

**Help:**
`{prefix}whelp` - Show this help message

_By default, no servers are monitored. Use `{prefix}monitor` or `{prefix}monitorall` to start._"""

    await ctx.send(help_text)
