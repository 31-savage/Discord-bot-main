"""Discord Welcome Bot - Main bot class with event handlers."""

import logging
from datetime import datetime, timezone

import discord

from discord_welcome_bot.config import settings

logger = logging.getLogger(__name__)


class WelcomeBot(discord.Client):
    """Discord self-bot that sends welcome messages when users join."""

    def __init__(self) -> None:
        super().__init__(
            # Subscribe to guild events automatically for guilds < 75k members
            guild_subscriptions=True,
            # Chunk guilds at startup to get full member list
            chunk_guilds_at_startup=True,
        )
        self._dm_channel: discord.DMChannel | None = None

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        if self.user is None:
            logger.error("Bot user is None after ready event")
            return

        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Create DM channel to self for notifications
        # We need to fetch ourselves as a User (not ClientUser) to create DM
        try:
            user = await self.fetch_user(self.user.id)
            self._dm_channel = await user.create_dm()
            logger.info("DM channel to self created successfully")
        except Exception as e:
            logger.error(f"Failed to create DM channel to self: {e}")

    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins a guild.

        Args:
            member: The member that joined.
        """
        logger.info(f"New member joined: {member} in {member.guild.name}")

        try:
            if self._dm_channel is None:
                logger.error("DM channel not available, cannot send notification")
                return

            embed = self._create_join_notification_embed(member)
            await self._dm_channel.send(embed=embed)
            logger.debug(f"Join notification sent to self for {member}")
        except discord.Forbidden:
            logger.error("Cannot send DM to self - forbidden")
        except Exception as e:
            logger.error(f"Error sending join notification: {e}")

    def _create_join_notification_embed(self, member: discord.Member) -> discord.Embed:
        """Create a notification embed with user info for a new member.

        Args:
            member: The member that joined.

        Returns:
            The notification embed with user details.
        """
        guild = member.guild
        member_count = guild.member_count or len(guild.members)

        # Calculate account age
        account_created = member.created_at
        now = datetime.now(timezone.utc)
        account_age = now - account_created

        embed = discord.Embed(
            title="New Member Joined",
            description=f"A new user has joined **{guild.name}**",
            color=discord.Color.green(),
            timestamp=now,
        )

        # Set the member's avatar as thumbnail
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        elif member.default_avatar:
            embed.set_thumbnail(url=member.default_avatar.url)

        # User info fields
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

        # Account age info
        age_str = f"{account_age.days} days, {account_age.seconds // 3600} hours"
        embed.add_field(name="Account Age", value=age_str, inline=True)

        # Add account age warning for very new accounts (< 7 days)
        if account_age.days < 7:
            embed.add_field(
                name="Warning",
                value=f"New account - only {account_age.days} day(s) old!",
                inline=False,
            )

        # Set footer with guild info
        if guild.icon:
            embed.set_footer(text=f"Server ID: {guild.id}", icon_url=guild.icon.url)
        else:
            embed.set_footer(text=f"Server ID: {guild.id}")

        return embed

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the user joins a new guild."""
        logger.info(f"Joined new guild: {guild.name}")
