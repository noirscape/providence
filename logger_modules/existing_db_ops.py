import datetime
import logging
from typing import List

import discord
import requests
from sqlalchemy import exists, and_, Column

import db
import logger_modules.embed as embed
import logger_modules.db_ops as db_ops
from logger_modules.context_manager_session import session_scope

LOGGER = logging.getLogger(__name__)


class ExistingDatabaseOperations:
    def __init__(self, config, sessionmaker):
        self.config = config
        self.sessionmaker = sessionmaker

    async def store_guild(self, guild: discord.Guild):
        # Stage 1: Create guild
        self.create_guild_if_not_exist(guild)

        # Stage 2: Store channels
        for channel in guild.text_channels:
            await self.store_guild_channel(channel)

        # Stage 3: Store members
        for member in guild.members:
            self.create_member_if_not_exist(member, guild)

    async def store_guild_channel(self, channel: discord.TextChannel):
        # Stage 1: Create channel
        self.create_text_channel_if_not_exist(channel)

        # Stage 2: Go over messages with create_message_if_not_exist
        if channel.permissions_for(channel.guild.me).read_message_history and channel.permissions_for(channel.guild.me).read_messages:
            async for message in channel.history(limit=None):
                self.create_message_if_not_exist(message, False)

    async def store_dm_channel(self, user: discord.User):
        # Stage 1: Create user
        self.create_user_if_not_exist(user)
        # Stage 2: Create channel
        self.create_dm_channel_if_not_exist(user.dm_channel)
        # Stage 3: Go over messages with create_message_if_not_exist
        async for message in user.dm_channel.history(limit=None):
            self.create_message_if_not_exist(message, True)

    def create_guild_if_not_exist(self, guild: discord.Guild):
        # Stage 1: Create guild owner _USER_
        self.create_user_if_not_exist(guild.owner)

        # Stage 2: Create guild
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(db.Guild.id == guild.id)).scalar():
                LOGGER.info("Storing new Guild: %s (%s)", guild.name, guild.id)
                session.add(db.Guild(id=guild.id, name=guild.name, icon_url=str(guild.icon_url), owner_id=guild.owner_id,
                                created_at=guild.created_at, last_updated=datetime.datetime.now(), localized_url=False)
                )

                # Stage 3: Create owner _MEMBER_
                self.create_member_if_not_exist(guild.owner, guild)

    def create_user_if_not_exist(self, user: discord.User):
        # Stage 1: Create user
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(db.User.id == user.id)).scalar():

                # Stage 1.5 Download avatar
                if self.config["local_avatars"]:
                    LOGGER.info("Downloading avatar for user: %s (%s)", str(user), user.id)
                    r = requests.get(user.avatar_url_as(format='png'))
                    with open(f"static/avatars/{user.id}.png", 'wb') as avatarfile:
                        avatarfile.write(r.content)
                    avatar_url = f"avatars/{user.id}.png"
                    localized = True
                else:
                    LOGGER.info("Not downloading avatar for user: %s (%s)", str(user), user.id)
                    avatar_url = user.avatar_url_as(format='png')
                    localized = False
                LOGGER.info("Storing new user: %s (%s)", str(user), user.id)
                session.add(db.User(id=user.id, name=user.name, discriminator=user.discriminator, is_bot=user.bot,
                            avatar=avatar_url, created_at=user.created_at, last_updated=datetime.datetime.now(), localized_avatar=localized
                ))

    def create_member_if_not_exist(self, member: discord.Member, guild: discord.Guild):
        # Stage 1: Check if guild exists
        self.create_guild_if_not_exist(guild)

        # Stage 2: Create user
        self.create_user_if_not_exist(member)

        # Stage 3: Create member
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where((db.GuildMember.guild_id == guild.id) & (db.GuildMember.user_id == member.id))).scalar():
                LOGGER.info("Storing new member: %s (%s) - Belongs to guild %s (%s)", str(member), member.id, guild, guild.id)
                if hasattr(member, "nick"):
                    nickname = member.nick
                else:
                    nickname = None
                session.add(db.GuildMember(user_id=member.id, guild_id=guild.id, nickname=nickname,
                                           last_updated=datetime.datetime.now()))

        # Stage 4: Fill member roles
        if type(member) == discord.Member: # I STILL DONT KNOW WHAT IS CAUSING THIS???
            self.fill_member_roles(member, guild)

    def create_text_channel_if_not_exist(self, channel: discord.TextChannel):
        # Stage 1: Create guild
        self.create_guild_if_not_exist(channel.guild)

        # Stage 2: Create channel
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(db.GuildChannel.id == channel.id)).scalar():
                LOGGER.info("Storing new Guild Channel: %s (%s) - Belongs to guild %s (%s)", channel.name, channel.id, channel.guild, channel.guild.id)
                session.add(db.GuildChannel(id=channel.id, guild_id=channel.guild.id, name=channel.name,
                                topic=channel.topic,
                                created_at=channel.created_at, last_updated=datetime.datetime.now()))

    def create_dm_channel_if_not_exist(self, channel: discord.DMChannel):
        # Stage 1: Create recipient
        self.create_user_if_not_exist(channel.recipient)

        # Stage 2: Create channel
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(db.DMChannel.id == channel.id)).scalar():
                LOGGER.info("Storing new DM Channel with %s (%s)", str(channel.recipient), channel.recipient.id)
                session.add(db.DMChannel(id=channel.id, remote_user_id=channel.recipient.id))

    def create_message_if_not_exist(self, message: discord.Message, is_dm: bool):
        # Stage 1: Select appropriate objects
        if is_dm:
            msg_object = db.PrivateMessage
            msg_edit = db.PrivateMessageEdit
        else:
            msg_object = db.GuildMessage
            msg_edit = db.GuildMessageEdit

        # Stage 2: Check if message is already stored
        with session_scope(self.sessionmaker) as session:
            stored = session.query(exists().where(msg_object.id == message.id)).scalar()
            LOGGER.info("Message with ID %s stored status: %s", message.id, stored)

        # Stage 3: If edited, check if edit with our content already exists
        msg_embed = embed.get_rich_embed(message)
        if message.edited_at:
            with session_scope(self.sessionmaker) as session:
                edited_exists = session.query(exists().where((msg_edit.content == message.clean_content) & (msg_edit.message_id == message.id))).scalar()
                LOGGER.info("Message with ID %s stored edit message status: %s", message.id, edited_exists)
        else:
            edited_exists = True
            LOGGER.info("Message with ID %s was never edited.", message.id)

        # Stage 4: Store author
        if is_dm:
            self.create_user_if_not_exist(message.author)
        else:
            self.create_member_if_not_exist(message.author, message.guild)

        # Stage 5: Store message
        if not stored:
            with session_scope(self.sessionmaker) as session:
                if not edited_exists:
                    content = "[THIS IS PLACEHOLDER (WAS EDITED LATER)]"
                    LOGGER.info("Message with ID %s received placeholder text.", message.id)
                else:
                    content = message.clean_content
                    LOGGER.info("Message with ID %s did not receive placeholder text.", message.id)
                LOGGER.info("Storing message with ID %s.", message.id)
                session.add(msg_object(id=message.id, channel_id=message.channel.id, author_id=message.author.id,
                            content=content, embed=msg_embed,
                            created_at=message.created_at))

        # Stage 5: Create attachments
        for attachment in message.attachments:
            self.create_attachment_if_not_exist(attachment, is_dm, message.id)
        # Stage 6: Add edit if needed
        if not edited_exists:
            with session_scope(self.sessionmaker) as session:
                LOGGER.info("Message with ID %s a dummy edit.", message.id)
                session.add(msg_edit(message_id=message.id, content=message.clean_content, embed=msg_embed,
                                                    edit_time=message.edited_at))

    def create_attachment_if_not_exist(self, attachment: discord.Attachment, is_dm: bool, message_id: int):
        # Stage 1: Select appropriate objects
        if is_dm:
            msg_attach = db.PrivateMessageAttachments
        else:
            msg_attach = db.GuildMessageAttachments

        # Stage 2: Store attachments
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(msg_attach.attachment_id == attachment.id)).scalar():
                if self.config["local_attachments"]:
                    LOGGER.info("Downloading attachment with ID %s", attachment.id)
                    r = requests.get(str(attachment.url))
                    with open(f"static/attachments/{attachment.id}-{attachment.filename}", 'wb') as attachmentfile:
                        attachmentfile.write(r.content)
                    attachment_url = f"attachments/{attachment.id}-{attachment.filename}"
                    localized = True
                else:
                    LOGGER.info("Not downloading attachment with ID %s", attachment.id)
                    attachment_url = str(attachment.url)
                    localized = False
                LOGGER.info("Storing attachment with ID %s", attachment.id)
                new_attachment = msg_attach(attachment_id=attachment.id, message_id=message_id,
                                                                filename=attachment.filename, url=attachment_url,
                                                                filesize=attachment.size,
                                                                localized_url=localized)
                session.add(new_attachment)

    def create_role_if_not_exist(self, role: discord.Role):
        # Stage 1: Create guild
        self.create_guild_if_not_exist(role.guild)
        # Stage 2: Store role
        with session_scope(self.sessionmaker) as session:
            if not session.query(exists().where(db.Role.id == role.id)).scalar():
                session.add(db.Role(id=role.id,
                            guild_id=role.guild.id,
                            name=role.name,
                            created_at=role.created_at))


    def fill_member_roles(self, member: discord.Member, guild: discord.Guild):
        # Stage 1: Create roles
        for role in member.roles:
            self.create_role_if_not_exist(role)

        with session_scope(self.sessionmaker) as session:
            # Stage 2: Clean out role list for member
            member_model = session.query(db.GuildMember).filter_by(user_id=member.id, guild_id=guild.id).one()
            for role in session.query(db.GuildMemberRoles).filter_by(member_id=member_model.id).all():
                session.delete(role)

            # Stage 3: Rebuild role list for member
            for role in member.roles:
                list_change = db.GuildMemberRoles(member_id=member_model.id, role_id=role.id)
                session.add(list_change)