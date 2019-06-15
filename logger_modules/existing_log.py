import discord
from logger_modules import existing_db_ops

class ExistingArchiveHandler:
    def __init__(self, client: discord.Client, config: dict, db_ops: existing_db_ops.ExistingDatabaseOperations):
        self.client = client
        self.config = config

    async def archive_guild(self, guild_id):
        await self.client.wait_until_ready()
        guild = self.client.get_guild(guild_id)
        await self.db_ops.store_guild(guild)

    async def archive_channel(self, channel_id):
        await self.client.wait_until_ready()
        channel = self.client.get_channel(channel_id)
        await self.db_ops.store_guild_channel(channel)

    async def archive_dm(self, user_id):
        await self.client.wait_until_ready()
        user = self.client.get_user(user_id)
        await self.db_ops.store_dm_channel(user)