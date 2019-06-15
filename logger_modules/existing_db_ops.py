import datetime
import logging
from typing import List

import discord
import requests
from sqlalchemy import exists, and_, Column

import db
import logger_modules.embed as embed
import logger_modules.db_ops as db_ops

LOGGER = logging.getLogger(__name__)


class ExistingDatabaseOperations:
    def __init__(self, config, sessionmanager):
        self.config = config
        self.sessionmanager = sessionmanager

    async def store_guild(self, guild: discord.Guild):
        # Stage 1: Create guild
        self.create_guild_if_not_exist(guild)
        # Stage 2: Store channels
        for channel in guild.text_channels:
            await self.store_guild_channel(channel)
        # Stage 3: Store members
        for member in guild.members:
            self.create_member_if_not_exist(member)

    async def store_guild_channel(self, channel: discord.TextChannel):
        # Stage 1: Create channel

        # Stage 2: Go over messages with create_message_if_not_exist
        pass

    async def store_dm_channel(self, user: discord.User):
        # Stage 1: Create channel

        # Stage 2: Go over messages with create_message_if_not_exist
        pass

    def create_guild_if_not_exist(self, guild: discord.Guild):
        # Stage 1: Create guild owner _USER_
        create_user_if_not_exist(guild.owner)
        # Stage 2: Create guild
        session = self.sessionmanager()
        if not session.query(exists().where(db.Guild.id == guild.id)).scalar():
            session.add(db.Guild(
                    db.Guild(id=guild.id, name=guild.name, icon_url=str(guild.icon_url), owner_id=guild.owner_id,
                             created_at=guild.created_at, last_updated=datetime.datetime.now())
            ))
        session.commit()
        session.close()

        # Stage 3: Create owner _MEMBER
        create_member_if_not_exist(guild.owner)

    def create_user_if_not_exist(self, user: discord.User):
        # Stage 1: Create user
        session = self.sessionmanager()
        if not session.query(exists().where(db.User.id == user.id)).scalar():
            # Stage 1.5 Download avatar
            if self.config["local_avatars"]:
                r = requests.get(user.avatar_url_as(format='png'))
                with open(f"static/avatars/{user.id}.png", 'wb') as avatarfile:
                    avatarfile.write(r.content)
                avatar_url = f"/static/avatars/{user.id}.png"
            else:
                avatar_url = user.avatar_url_as(format='png')
            session.add(db.User(id=user.id, name=user.name, discriminator=user.discriminator, is_bot=user.bot,
                        avatar=avatar_url, created_at=user.created_at, last_updated=datetime.datetime.now()
            ))
        session.commit()
        session.close()

    def create_member_if_not_exist(self, member: discord.Member):
        # Stage 1: Check if guild exists
        session = self.sessionmanager()
        if not session.query(exists().where(db.Guild.id == member.guild.id)):
            create_guild_if_not_exist(guild)
        session.commit()
        session.close()
        # Stage 2: Create user
        create_user_if_not_exist(user)
        # Stage 3: Create member
        session = self.sessionmanager()
        if not session.query(exists().where((db.GuildMember.guild_id == guild.id) & (db.GuildMember.user_id == member.id))).scalar():
            session.add(db.GuildMember(user_id=user.id, guild_id=guild.id, nickname=nickname,
                                    last_updated=datetime.datetime.now()))
        session.commit()
        session.close()
        # Stage 4: Fill member roles
        self.fill_member_roles(member)

    def create_text_channel_if_not_exist(self, channel: discord.TextChannel):
        # Stage 1: Create channel
        pass

    def create_message_if_not_exist(self, message: discord.Message, is_dm: bool):
        # Stage 1: Select appropriate object

        # Stage 2: Check if message is already stored

        # Stage 3: If stored with an edit, make empty content

        # Stage 4: Create attachments

        # Stage 5: Add edit if needed
        pass

    def create_attachment_if_not_exist(self, attachment: discord.Attachment):
        # Stage 1: Store attachments
        pass

    def create_role_if_not_exist(self, role: discord.Role):
        # Stage 1: Store role
        pass

    def fill_member_roles(self, member: discord.Member):
        # Stage 1: Create roles

        # Stage 2: Check role audits and only store roles that are active

        # Stage 3: Make new audits for roles that are not logged as active
        pass