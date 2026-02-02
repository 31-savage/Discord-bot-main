"""Discord Welcome Bot - Main bot class with event handlers and commands."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from discord_welcome_bot.config import settings

logger = logging.getLogger(__name__)

# File to persist monitored guilds
DATA_FILE = Path("monitored_guilds.json")


def load_monitored_guilds() -> set[int]:
    """Load monitored guild IDs from file."""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
                return set(data.get("guild_ids", []))
        except Exception as e:
            logger.error(f"Failed to load monitored guilds: {e}")
    return set()


def save_monitored_guilds(guild_ids: set[int]) -> None:
    """Save monitored guild IDs to file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"guild_ids": list(guild_ids)}, f)
    except Exception as e:
        logger.error(f"Failed to save monitored guilds: {e}")


class WelcomeBot(commands.Bot):
    """Discord self-bot that sends welcome messages when users join."""

    def __init__(self) -> None:
        super().__init__(
            command_prefix=settings.command_prefix,
            self_bot=True,
            # Subscribe to guild events automatically for guilds < 75k members
            guild_subscriptions=True,
            # Chunk guilds at startup to get full member list
            chunk_guilds_at_startup=True,
        )
        self._notification_channel: discord.GroupChannel | discord.TextChannel | None = None
        self._monitored_guilds: set[int] = load_monitored_guilds()

    @property
    def monitored_guilds(self) -> set[int]:
        """Get the set of monitored guild IDs."""
        return self._monitored_guilds

    def is_guild_monitored(self, guild_id: int) -> bool:
        """Check if a guild is being monitored.

        Only monitors guilds that are explicitly added.
        If no guilds are configured, nothing is monitored.
        """
        return guild_id in self._monitored_guilds

    def add_monitored_guild(self, guild_id: int) -> None:
        """Add a guild to the monitored list."""
        self._monitored_guilds.add(guild_id)
        save_monitored_guilds(self._monitored_guilds)

    def remove_monitored_guild(self, guild_id: int) -> None:
        """Remove a guild from the monitored list."""
        self._monitored_guilds.discard(guild_id)
        save_monitored_guilds(self._monitored_guilds)

    def clear_monitored_guilds(self) -> None:
        """Clear all monitored guilds (will monitor nothing)."""
        self._monitored_guilds.clear()
        save_monitored_guilds(self._monitored_guilds)

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        # Add commands
        self.add_command(cmd_servers)
        self.add_command(cmd_monitor)
        self.add_command(cmd_unmonitor)
        self.add_command(cmd_monitored)
        self.add_command(cmd_clear)
        self.add_command(cmd_help_welcome)

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        if self.user is None:
            logger.error("Bot user is None after ready event")
            return

        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Get notification channel
        try:
            channel = await self.fetch_channel(settings.notification_channel_id)
            if isinstance(channel, (discord.GroupChannel, discord.TextChannel, discord.DMChannel)):
                self._notification_channel = channel  # type: ignore
                logger.info(f"Notification channel set: {channel}")
            else:
                logger.error(
                    f"Channel {settings.notification_channel_id} is not a valid text channel"
                )
        except Exception as e:
            logger.error(f"Failed to fetch notification channel: {e}")

        # Log monitoring status
        if self._monitored_guilds:
            logger.info(f"Monitoring {len(self._monitored_guilds)} specific guild(s)")
        else:
            logger.info("Not monitoring any guilds (use !monitor <guild_id> to add)")

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
            f"Server with ID `{guild_id}` not found. Use `{settings.command_prefix}servers` to see available servers."
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

    if not bot.monitored_guilds:
        await ctx.send(
            "No servers configured. **Monitoring nothing.** Use `!monitor <guild_id>` to add servers."
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
    """Clear monitored list (will monitor nothing)."""
    bot: WelcomeBot = ctx.bot  # type: ignore
    bot.clear_monitored_guilds()
    await ctx.send("Cleared monitored list. **Now monitoring nothing.**")


@commands.command(name="whelp")
async def cmd_help_welcome(ctx: commands.Context) -> None:  # type: ignore
    """Show help for welcome bot commands."""
    prefix = settings.command_prefix

    help_text = f"""**Welcome Bot Commands**

`{prefix}servers` - List all servers the bot is in
`{prefix}monitor <guild_id>` - Add a server to the monitored list
`{prefix}unmonitor <guild_id>` - Remove a server from the monitored list
`{prefix}monitored` - List all monitored servers
`{prefix}clear` - Clear monitored list (monitor nothing)
`{prefix}whelp` - Show this help message

_By default, no servers are monitored. Use `{prefix}monitor` to add servers._"""

    await ctx.send(help_text)
