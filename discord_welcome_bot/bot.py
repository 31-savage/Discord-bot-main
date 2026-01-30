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

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        if self.user is None:
            logger.error("Bot user is None after ready event")
            return

        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Subscribe to member events for all guilds if enabled
        if settings.subscribe_to_member_events:
            await self._subscribe_to_guilds()

    async def _subscribe_to_guilds(self) -> None:
        """Subscribe to member events for all guilds.

        This is important for receiving on_member_join events.
        See: https://discordpy-self.readthedocs.io/en/latest/guild_subscriptions.html
        """
        for guild in self.guilds:
            try:
                # Subscribe to the guild with member events enabled
                await guild.subscribe(
                    typing=False,
                    threads=False,
                    member_updates=True,  # Required for on_member_join
                )
                logger.debug(f"Subscribed to member events for guild: {guild.name}")
            except Exception as e:
                logger.warning(f"Failed to subscribe to guild {guild.name}: {e}")

    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins a guild.

        Args:
            member: The member that joined.
        """
        logger.info(f"New member joined: {member} in {member.guild.name}")

        try:
            channel = await self._find_welcome_channel(member.guild)
            if channel is None:
                logger.warning(
                    f"No suitable welcome channel found in {member.guild.name}. "
                    "Set WELCOME_CHANNEL_ID or create a channel named 'welcome' or 'general'."
                )
                return

            embed = self._create_welcome_embed(member)
            await channel.send(embed=embed)
            logger.debug(f"Welcome message sent for {member} in #{channel.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to send message in {member.guild.name}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")

    async def _find_welcome_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:
        """Find the appropriate channel to send welcome messages.

        Priority order:
        1. Configured WELCOME_CHANNEL_ID
        2. Channel named "welcome"
        3. Channel named "general"
        4. System channel (where Discord sends default messages)

        Args:
            guild: The guild to search for a welcome channel.

        Returns:
            The text channel to use, or None if not found.
        """
        # Priority 1: Use configured channel ID
        if settings.welcome_channel_id:
            channel = guild.get_channel(settings.welcome_channel_id)
            if isinstance(channel, discord.TextChannel):
                return channel

        # Priority 2: Find channel named "welcome"
        for channel in guild.text_channels:
            if channel.name.lower() == "welcome":
                return channel

        # Priority 3: Find channel named "general"
        for channel in guild.text_channels:
            if channel.name.lower() == "general":
                return channel

        # Priority 4: Use system channel
        if guild.system_channel is not None:
            return guild.system_channel

        return None

    def _create_welcome_embed(self, member: discord.Member) -> discord.Embed:
        """Create a welcome embed for a new member.

        Args:
            member: The member that joined.

        Returns:
            The welcome embed.
        """
        guild = member.guild
        member_count = guild.member_count or len(guild.members)

        # Calculate account age
        account_created = member.created_at
        now = datetime.now(timezone.utc)
        account_age = now - account_created

        embed = discord.Embed(
            title="Welcome to the Server!",
            description=(
                f"Hey {member.mention}, welcome to **{guild.name}**!\n\n"
                f"You are member #{member_count}. We're glad to have you here!"
            ),
            color=discord.Color.blurple(),
            timestamp=now,
        )

        # Set the member's avatar as thumbnail
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        elif member.default_avatar:
            embed.set_thumbnail(url=member.default_avatar.url)

        # Add fields
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="Member #", value=str(member_count), inline=True)
        embed.add_field(
            name="Account Created",
            value=f"<t:{int(account_created.timestamp())}:R>",
            inline=True,
        )

        # Add account age warning for very new accounts (< 7 days)
        if account_age.days < 7:
            embed.add_field(
                name="New Account",
                value=f"Account is only {account_age.days} day(s) old",
                inline=False,
            )

        # Set footer with guild info
        if guild.icon:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_footer(text=guild.name)

        return embed

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the user joins a new guild.

        Subscribe to member events for the new guild.
        """
        logger.info(f"Joined new guild: {guild.name}")

        if settings.subscribe_to_member_events:
            try:
                await guild.subscribe(
                    typing=False,
                    threads=False,
                    member_updates=True,
                )
                logger.debug(f"Subscribed to member events for new guild: {guild.name}")
            except Exception as e:
                logger.warning(f"Failed to subscribe to new guild {guild.name}: {e}")
