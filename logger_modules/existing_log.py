import discord
from logger_modules import existing_db_ops

import logging

LOGGER = logging.getLogger(__name__)

class ExistingArchiveHandler:
    def __init__(self, client: discord.Client, config: dict, db_ops: existing_db_ops.ExistingDatabaseOperations):
        self.client = client
        self.config = config
        self.db_ops = db_ops

    async def archive_guild(self, guild_id):
        await self.client.wait_until_ready()
        guild = self.client.get_guild(guild_id)
        if not guild:
            LOGGER.error("No such guild exists!")
        else:
            LOGGER.info("Logging guild %s (%s)", guild, guild.id)
            await self.db_ops.store_guild(guild)
        await self.client.logout()

    async def archive_channel(self, channel_id):
        await self.client.wait_until_ready()
        channel = self.client.get_channel(channel_id)
        if not channel:
            LOGGER.error("No such channel exists!")
        else:
            LOGGER.info("Logging channel %s (%s) in guild %s (%s)", channel, channel.id, channel.guild, channel.guild.id)
            await self.db_ops.store_guild_channel(channel)
        await self.client.logout()

    async def archive_dm(self, user_id):
        await self.client.wait_until_ready()
        user = self.client.get_user(user_id)
        if not user:
            LOGGER.error("No such user exists!")
        elif user.dm_channel:
            LOGGER.info("Logging DMs with %s (%s)", str(user), user.id)
            await self.db_ops.store_dm_channel(user)
        else:
            LOGGER.error("No DMs exists with %s (%s)!", str(user), user.id)
        await self.client.logout()