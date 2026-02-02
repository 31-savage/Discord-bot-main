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

        If no guilds are configured, monitor ALL guilds.
        """
        if not self._monitored_guilds:
            return True  # Monitor all if none specified
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
        """Clear all monitored guilds (will monitor all)."""
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
            logger.info("Monitoring ALL guilds (no specific guilds configured)")

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

            embed = self._create_join_notification_embed(member)
            await self._notification_channel.send(embed=embed)
            logger.debug(f"Join notification sent for {member}")
        except discord.Forbidden:
            logger.error("Cannot send to notification channel - forbidden")
        except Exception as e:
            logger.error(f"Error sending join notification: {e}")

    def _create_join_notification_embed(self, member: discord.Member) -> discord.Embed:
        """Create a notification embed with user info for a new member."""
        guild = member.guild
        member_count = guild.member_count or len(guild.members)

        account_created = member.created_at
        now = datetime.now(timezone.utc)
        account_age = now - account_created

        embed = discord.Embed(
            title="New Member Joined",
            description=f"A new user has joined **{guild.name}**",
            color=discord.Color.green(),
            timestamp=now,
        )

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        elif member.default_avatar:
            embed.set_thumbnail(url=member.default_avatar.url)

        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(name="Mention", value=member.mention, inline=True)
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.add_field(name="Member #", value=str(member_count), inline=True)
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(account_created.timestamp())}:F>\n(<t:{int(account_created.timestamp())}:R>)",
            inline=True,
        )

        age_str = f"{account_age.days} days, {account_age.seconds // 3600} hours"
        embed.add_field(name="Account Age", value=age_str, inline=True)

        if account_age.days < 7:
            embed.add_field(
                name="Warning",
                value=f"New account - only {account_age.days} day(s) old!",
                inline=False,
            )

        if guild.icon:
            embed.set_footer(text=f"Server ID: {guild.id}", icon_url=guild.icon.url)
        else:
            embed.set_footer(text=f"Server ID: {guild.id}")

        return embed

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the user joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        if self._notification_channel:
            try:
                embed = discord.Embed(
                    title="Joined New Server",
                    description=f"You joined **{guild.name}**",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc),
                )
                embed.add_field(name="Server ID", value=str(guild.id), inline=True)
                embed.add_field(name="Members", value=str(guild.member_count), inline=True)
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                await self._notification_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send guild join notification: {e}")


# ============ Commands ============


@commands.command(name="servers")
async def cmd_servers(ctx: commands.Context) -> None:
    """List all servers the bot is in."""
    bot: WelcomeBot = ctx.bot  # type: ignore

    if not bot.guilds:
        await ctx.send("Not in any servers.")
        return

    embed = discord.Embed(
        title="Server List",
        description=f"Connected to {len(bot.guilds)} server(s)",
        color=discord.Color.blue(),
    )

    for i, guild in enumerate(bot.guilds, 1):
        monitored = "Yes" if bot.is_guild_monitored(guild.id) else "No"
        # Only show first 25 due to embed limits
        if i <= 25:
            embed.add_field(
                name=f"{i}. {guild.name}",
                value=f"ID: `{guild.id}`\nMembers: {guild.member_count}\nMonitored: {monitored}",
                inline=True,
            )

    if len(bot.guilds) > 25:
        embed.set_footer(text=f"Showing 25 of {len(bot.guilds)} servers")

    await ctx.send(embed=embed)


@commands.command(name="monitor")
async def cmd_monitor(ctx: commands.Context, guild_id: int) -> None:
    """Add a server to the monitored list.

    Usage: !monitor <guild_id>
    """
    bot: WelcomeBot = ctx.bot  # type: ignore

    # Check if guild exists
    guild = bot.get_guild(guild_id)
    if guild is None:
        await ctx.send(
            f"Server with ID `{guild_id}` not found. Use `{settings.command_prefix}servers` to see available servers."
        )
        return

    bot.add_monitored_guild(guild_id)
    await ctx.send(f"Now monitoring **{guild.name}** (`{guild_id}`)")


@commands.command(name="unmonitor")
async def cmd_unmonitor(ctx: commands.Context, guild_id: int) -> None:
    """Remove a server from the monitored list.

    Usage: !unmonitor <guild_id>
    """
    bot: WelcomeBot = ctx.bot  # type: ignore

    guild = bot.get_guild(guild_id)
    guild_name = guild.name if guild else "Unknown"

    bot.remove_monitored_guild(guild_id)
    await ctx.send(f"Stopped monitoring **{guild_name}** (`{guild_id}`)")


@commands.command(name="monitored")
async def cmd_monitored(ctx: commands.Context) -> None:
    """List all monitored servers."""
    bot: WelcomeBot = ctx.bot  # type: ignore

    if not bot.monitored_guilds:
        await ctx.send("No specific servers configured. **Monitoring ALL servers.**")
        return

    embed = discord.Embed(
        title="Monitored Servers",
        description=f"Monitoring {len(bot.monitored_guilds)} server(s)",
        color=discord.Color.green(),
    )

    for guild_id in bot.monitored_guilds:
        guild = bot.get_guild(guild_id)
        name = guild.name if guild else "Unknown (left server?)"
        embed.add_field(name=name, value=f"ID: `{guild_id}`", inline=True)

    await ctx.send(embed=embed)


@commands.command(name="clear")
async def cmd_clear(ctx: commands.Context) -> None:
    """Clear monitored list (will monitor ALL servers)."""
    bot: WelcomeBot = ctx.bot  # type: ignore
    bot.clear_monitored_guilds()
    await ctx.send("Cleared monitored list. Now monitoring **ALL servers**.")


@commands.command(name="whelp")
async def cmd_help_welcome(ctx: commands.Context) -> None:
    """Show help for welcome bot commands."""
    prefix = settings.command_prefix

    embed = discord.Embed(
        title="Welcome Bot Commands",
        color=discord.Color.blue(),
    )

    embed.add_field(
        name=f"{prefix}servers",
        value="List all servers the bot is in",
        inline=False,
    )
    embed.add_field(
        name=f"{prefix}monitor <guild_id>",
        value="Add a server to the monitored list",
        inline=False,
    )
    embed.add_field(
        name=f"{prefix}unmonitor <guild_id>",
        value="Remove a server from the monitored list",
        inline=False,
    )
    embed.add_field(
        name=f"{prefix}monitored",
        value="List all monitored servers",
        inline=False,
    )
    embed.add_field(
        name=f"{prefix}clear",
        value="Clear monitored list (monitor ALL servers)",
        inline=False,
    )
    embed.add_field(
        name=f"{prefix}whelp",
        value="Show this help message",
        inline=False,
    )

    embed.set_footer(text="If no servers are monitored, ALL servers are monitored by default.")

    await ctx.send(embed=embed)
