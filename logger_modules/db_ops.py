import datetime
import logging

import discord
import requests
from sqlalchemy import exists, and_

import db
import logger_modules.embed as embed

LOGGER = logging.getLogger(__name__)


class DatabaseOperations:
    def __init__(self, config, session_manager):
        """Instantiate DatabaseOperations class.

        Config: User config to pass in.
        session_manager: Manager for all sessions."""
        self.config = config
        self.session_manager = session_manager

    def create_user(self, user: discord.User):
        session = self.session_manager()

        if self.config["local_avatars"]:
            r = requests.get(user.avatar_url_as(format='png'))
            with open(f"static/avatars/{user.id}.png", 'wb') as avatarfile:
                avatarfile.write(r.content)
            avatar_url = f"/static/avatars/{user.id}.png"
        else:
            avatar_url = str(user.avatar_url)

        new_user = db.User(id=user.id, name=user.name, discriminator=user.discriminator, is_bot=user.bot,
                           avatar=avatar_url, created_at=user.created_at, last_updated=datetime.datetime.now())
        session.merge(new_user)

        session.commit()
        session.close()

    def create_dm_channel(self, channel: discord.DMChannel):
        session = self.session_manager()

        new_dm_channel = db.DMChannel(id=channel.id, remote_user_id=channel.recipient.id)
        session.merge(new_dm_channel)

        session.commit()
        session.close()


    def store_private_message(self, message: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(db.User.id == message.author.id)).scalar():
            self.create_user(message.author)
        if not session.query(exists().where(db.User.id == message.channel.recipient.id)).scalar():
            self.create_user(message.channel.recipient)
        if not session.query(exists().where(db.DMChannel.id == message.channel.id)).scalar():
            self.create_dm_channel(message.channel)

        new_message = db.PrivateMessage(id=message.id, channel_id=message.channel.id, author_id=message.author.id,
                                        content=message.clean_content, embed=embed.get_rich_embed(message),
                                        created_at=message.created_at)
        session.merge(new_message)
        session.commit()

        for attachment in message.attachments:
            if self.config["local_attachments"]:
                r = requests.get(str(attachment.url))
                with open(f"static/attachments/{attachment.id}-{attachment.filename}", 'wb') as attachmentfile:
                    attachmentfile.write(r.content)
                attachment_url = f"/static/attachments/{attachment.id}-{attachment.filename}"
            else:
                attachment_url = str(attachment.url)
            new_attachment = db.PrivateMessageAttachments(attachment_id=attachment.id, message_id=message.id,
                                                          filename=attachment.filename, url=attachment_url,
                                                          filesize=attachment.size)
            session.merge(new_attachment)
            session.commit()
        session.close()


    def store_private_message_edit(self, before: discord.Message, after: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(db.PrivateMessage.id == before.id)).scalar():
            self.store_private_message(before)

        if before.content == after.content:
            store_content = None
        else:
            store_content = after.content

        if embed.get_rich_embed(before) == embed.get_rich_embed(after):
            store_embed = None
        else:
            store_embed = embed.get_rich_embed(after)

        new_message_edit = db.PrivateMessageEdit(message_id=after.id, content=store_content, embed=store_embed,
                                                 edit_time=after.edited_at)
        session.merge(new_message_edit)

        session.commit()
        session.close()


    def update_private_pin(self, message: discord.Message):
        session = self.session_manager()

        if session.query(exists().where(and_(db.DMChannelPins.message_id == message.id, db.DMChannelPins.is_pinned == True))
                        ).scalar():
            pass
        else:
            if not session.query(exists().where(db.PrivateMessage.id == message.id)).scalar():
                self.store_private_message(message)
            new_pin = db.DMChannelPins(dm_channel_id=message.channel.id, message_id=message.id, is_pinned=True,
                                       pinned_at=datetime.datetime.now())
            session.add(new_pin)

        session.commit()
        session.close()


    def get_all_dm_pins(self, channel: discord.DMChannel) -> list:
        session = self.session_manager()

        pin_list = []
        for result in session.query(db.DMChannelPins).filter_by(dm_channel_id=channel.id):
            pin_list.append((result.message_id, result.pin_id))
        session.commit()
        session.close()
        return pin_list


    def remove_dm_pin(self, pin_id: int):
        session = self.session_manager()

        pin = session.query(db.DMChannelPins).filter_by(pin_id=pin_id).one()
        if pin.is_pinned:
            pin.is_pinned = False
            pin.unpinned_at = datetime.datetime.now()
        session.merge(pin)

        session.commit()
        session.close()


    def delete_private_message(self, message: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(db.PrivateMessage.id == message.id)).scalar():
            self.store_private_message(message)

        new_delete = db.PrivateMessageDeletion(message_id=message.id, deletion_time=datetime.datetime.now())
        session.merge(new_delete)

        session.commit()
        session.close()


    def create_member(self, user: discord.Member, guild: discord.Guild):
        """
        Create a new member in the database.

        Arguments:
            user: discord.Member object to put in the database.
            guild: Guild to put in database (required and separate to prevent freak accidents).
        """
        session = self.session_manager()

        if not session.query(exists().where(db.User.id == user.id)).scalar():
            self.create_user(user)
        if not session.query(exists().where(db.Guild.id == guild.id)).scalar():
            self.create_guild(guild)
            if user.id == guild.owner_id: # Prevents cyclical creation of guild and owner!
                return
        if hasattr(user, "nick"):
            nickname = user.nick
        else:
            nickname = None
        new_member = db.GuildMember(user_id=user.id, guild_id=guild.id, nickname=nickname,
                                    last_updated=datetime.datetime.now())
        session.merge(new_member)

        if hasattr(user, "roles"):
            for role in user.roles:
                self.create_role(role)

        session.commit()
        session.close()


    def create_guild(self, guild: discord.Guild):
        session = self.session_manager()

        if not session.query(exists().where(db.User.id == guild.owner.id)).scalar():
            self.create_user(guild.owner)

        new_guild = db.Guild(id=guild.id, name=guild.name, icon_url=str(guild.icon_url), owner_id=guild.owner_id,
                             created_at=guild.created_at, last_updated=datetime.datetime.now())

        session.merge(new_guild)

        if not session.query(exists().where(and_(db.GuildMember.user_id == guild.owner_id,
                                                 db.GuildMember.guild_id == guild.id))).scalar():
            self.create_member(guild.owner, guild)

        session.commit()
        session.close()


    def create_guild_channel(self, channel: discord.TextChannel):
        session = self.session_manager()

        if not session.query(exists().where(db.Guild.id == channel.guild.id)).scalar():
            self.create_guild(channel.guild)
            session.close()
        new_guild_channel = db.GuildChannel(id=channel.id, guild_id=channel.guild.id, name=channel.name,
                                            topic=channel.topic,
                                            created_at=channel.created_at, last_updated=datetime.datetime.now())
        session.merge(new_guild_channel)

        session.commit()
        session.close()


    def create_role(self, role: discord.Role):
        session = self.session_manager()

        LOGGER.info("Creating new role %s (%d)", role.name, role.id)
        if not session.query(exists().where(db.Guild.id == role.guild.id)).scalar():
            self.create_guild(role.guild)
        new_role = db.Role(id=role.id,
                           guild_id=role.guild.id,
                           name=role.name,
                           created_at=role.created_at)
        session.merge(new_role)
        LOGGER.info("Role creation succesfull!")

        session.commit()
        session.close()


    def store_guild_message(self, message: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(
                and_(db.GuildMember.user_id == message.author.id, db.GuildMember.guild_id == message.guild.id))).scalar():
            self.create_member(message.author, message.guild)
        if not session.query(exists().where(db.GuildChannel.id == message.channel.id)).scalar():
            self.create_guild_channel(message.channel)
        new_message = db.GuildMessage(id=message.id, channel_id=message.channel.id, author_id=message.author.id,
                                      content=message.clean_content, embed=embed.get_rich_embed(message), created_at=message.created_at)
        session.merge(new_message)
        session.commit()

        for attachment in message.attachments:
            if self.config["local_attachments"]:
                r = requests.get(str(attachment.url))
                with open(f"static/attachments/{attachment.id}-{attachment.filename}", 'wb') as attachmentfile:
                    attachmentfile.write(r.content)
                attachment_url = f"/static/attachments/{attachment.id}-{attachment.filename}"
            else:
                attachment_url = str(attachment.url)
            new_attachment = db.GuildMessageAttachments(attachment_id=attachment.id, message_id=message.id,
                                                        filename=attachment.filename, url=attachment_url,
                                                        filesize=attachment.size)
            session.merge(new_attachment)
            session.commit()

        session.close()


    def store_guild_message_edit(self, before: discord.Message, after: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(db.GuildMessage.id == before.id)).scalar():
            self.store_guild_message(before)

        if before.content == after.content:
            store_content = None
        else:
            store_content = after.clean_content

        if embed.get_rich_embed(before) == embed.get_rich_embed(after):
            store_embed = None
        else:
            store_embed = embed.get_rich_embed(after)

        new_message_edit = db.GuildMessageEdit(message_id=after.id, content=store_content, 
                                               embed=store_embed, edit_time=after.edited_at)
        session.merge(new_message_edit)
        session.commit()
        session.close()


    def delete_guild_message(self, message: discord.Message):
        session = self.session_manager()

        if not session.query(exists().where(db.GuildMessage.id == message.id)).scalar():
            self.store_guild_message(message)

        new_delete = db.GuildMessageDeletion(message_id=message.id, 
                                             deletion_time=datetime.datetime.now())
        session.merge(new_delete)
        session.commit()
        session.close()


    def get_all_guild_channel_pins(self, channel: discord.TextChannel) -> list:
        session = self.session_manager()

        pin_list = []
        for result in session.query(db.GuildChannel).filter_by(id=channel.id):
            pin_list.append((result.message_id, result.pin_id))
        return pin_list

        session.commit()
        session.close()


    def remove_guild_channel_pin(self, pin_id: int):
        session = self.session_manager()

        pin = session.query(db.GuildChannelPins).filter_by(pin_id=pin_id).one()
        if pin.is_pinned:
            pin.is_pinned = False
            pin.unpinned_at = datetime.datetime.now()
        session.merge(pin)
        session.commit()
        session.close()


    def update_guild_channel_pin(self, message: discord.Message):
        session = self.session_manager()

        if session.query(exists().where(and_(db.GuildChannelPins.message_id == message.id, db.GuildChannelPins.is_pinned == True))
                        ).scalar():
            pass
        else:
            if not session.query(exists().where(db.GuildMessage.id == message.id)).scalar():
                self.store_guild_message(message)
            new_pin = db.GuildChannelPins(guild_channel_id=message.channel.id, message_id=message.id, is_pinned=True,
                                          pinned_at=datetime.datetime.now())
            session.add(new_pin)

        session.commit()
        session.close()


    def update_user(self, before: discord.User, after: discord.User):
        session = self.session_manager()

        if not session.query(exists().where(db.User.id == before.id)).scalar():
            self.create_user(before)

        user_model = session.query(db.User).filter_by(id=before.id).one()

        if before.avatar_url_as(format='png') != after.avatar_url_as(format='png'):
            if self.config["local_avatars"]:
                r = requests.get(after.avatar_url_as(format='png'))
                with open(f"static/avatars/{after.id}.png", 'wb') as avatarfile:
                    avatarfile.write(r.content)
                new_avatar = f"/static/avatars/{after.id}.png"
            else:
                new_avatar = str(after.avatar_url)
        else:
            new_avatar = str(before.avatar_url)

        # This probably could be done more efficient but fuck it, my mind needs to understand whats going on.
        old_user = db.UserEdit(user_id=user_model.id, 
                               name=user_model.name,
                               discriminator=user_model.discriminator,
                               avatar=user_model.avatar,
                               edit_time=datetime.datetime.now())

        session.add(old_user)
        user_model.name = after.name
        user_model.discriminator = after.discriminator
        user_model.avatar = new_avatar
        session.merge(user_model)

        session.commit()
        session.close()


    def update_member(self, before: discord.Member, after: discord.Member):
        session = self.session_manager()

        if not session.query(exists().where(and_(db.GuildMember.user_id == before.id,
                                                 db.GuildMember.guild_id == before.guild.id))).scalar():
            self.create_member(before, before.guild)

        member_model = session.query(db.GuildMember).filter_by(user_id=before.id, guild_id=before.guild.id).one()

        # Register nickname change
        if member_model.nickname != after.nick:
            LOGGER.info("User ID: %d\nGuild ID: %d", before.id, before.guild.id)
            LOGGER.info("Nickname changed: %s became %s", member_model.nickname, after.nick)
            member_edit = db.GuildMemberEdit(member_id=member_model.id,
                                             edit_time=datetime.datetime.now(),
                                             nickname=member_model.nickname)
            member_model.nickname = after.nick
            session.add(member_edit)
            session.merge(member_edit)

        # Role stuff
        added_roles = []
        removed_roles = []

        for role in before.roles:
            if role not in after.roles:
                removed_roles.append(role)
            if not session.query(exists().where(db.Role.id == role.id)).scalar():
                self.create_role(role)

        for role in after.roles:
            if role not in before.roles:
                added_roles.append(role)
            if not session.query(exists().where(db.Role.id == role.id)).scalar():
                self.create_role(role)

        if added_roles or after.id == 126747960972279808:
            LOGGER.info("User ID: %s\nGuild ID: %s", before.id, before.guild.id)
            LOGGER.info("added roles: %s", added_roles)
        if removed_roles or after.id == 126747960972279808:
            LOGGER.info("User ID: %s\nGuild ID: %s", before.id, before.guild.id)
            LOGGER.info("removed roles: %s", added_roles)

        member_model = session.query(db.GuildMember).filter_by(user_id=before.id, guild_id=before.guild.id).one()

        for role in added_roles:
            list_change = db.GuildMemberRoles(member_id=member_model.id, role_id=role.id)
            session.delete(list_change)
            role_add = db.RoleAudit(member_id=member_model.id,
                                    role_id=role.id,
                                    role_was_added=True,
                                    event_at=datetime.datetime.now())
            session.add(role_add)

        for role in removed_roles:
            list_change = db.GuildMemberRoles(member_id=member_model.id, role_id=role.id)
            session.delete(list_change)
            role_remove = db.RoleAudit(member_id=member_model.id,
                                       role_id=role.id,
                                       role_was_added=False,
                                       event_at=datetime.datetime.now())
            session.add(role_remove)

        session.commit()
        session.close()

    def update_guild(self, before: discord.Guild, after: discord.Guild):
        session = self.session_manager()

        if not session.query(exists().where(db.Guild.id == before.id)).scalar():
            self.create_guild(before)
            session.commit()

        guild_model = session.query(db.Guild).filter_by(id=before.id).one()

        changes = False
        old_name = None
        old_owner = guild_model.owner_id
        old_icon = None

        if before.name != after.name:
            old_name = before.name
            guild_model.name = after.name
            LOGGER.info("Guild ID:%s:Name changed from %s to %s", before.id, before.name, after.name)
            changes = True
        if before.owner.id != after.owner.id:
            old_owner = before.owner.id
            guild_model.owner_id = after.owner.id
            LOGGER.info("Guild ID:%s:Owner changed from %s to %s", before.id, before.owner.name, after.owner.name)
            changes = True
        if before.icon_url != after.icon_url:
            old_icon = before.icon_url
            guild_model.icon_url = after.icon_url
            LOGGER.info("Guild ID:%s:Icon URL changed from %s to %s", before.id, before.icon_url, after.icon_url)
            changes = True

        if changes:
            new_guild_edit = db.GuildEdit(
                guild_id=guild_model.id,
                name=old_name,
                owner_id=old_owner,
                edit_time=datetime.datetime.now(),
                icon_url=old_icon
            )
            session.add(new_guild_edit)

        session.merge(guild_model)
        session.commit()
        session.close()

    def update_role(self, before: discord.Role, after: discord.Role):
        session = self.session_manager()

        if not session.query(exists().where(db.Role.id == before.id)).scalar():
            self.create_role(before)
            session.commit()

        role_model = session.query(db.Guild).filter_by(id=before.id).one()

        changes = False
        old_name = None

        if before.name != after.name:
            old_name = before.name
            role_model.name = after.name
            LOGGER.info("Role ID:%s:Name changed from %s to %s", before.id, before.name, after.name)
            changes = True

        if changes:
            new_role_edit = db.RoleEdit(
                role_id=role_model.id,
                name=old_name,
                edit_time=datetime.datetime.now()
            )
            session.add(new_role_edit)

        session.merge(role_model)
        session.commit()
        session.close()

    def update_guild_channel(self, before: discord.TextChannel, after: discord.TextChannel):
        session = self.session_manager()

        channel_model = session.query(db.GuildChannel).filter_by(id=before.id).one()

        changes = False
        old_name = None
        old_topic = None

        if before.name != after.name:
            old_name = before.name
            channel_model.name = after.name
            LOGGER.info("Channel ID:%s:Name changed from %s to %s", before.id, before.name, after.name)
            changes = True
        if before.topic != after.topic:
            old_topic = before.topic
            channel_model.topic = after.topic
            LOGGER.info("Channel ID:%s:Topic changed from %s to %s", before.id, before.topic, after.topic)
            changes = True

        if changes:
            new_guild_channel_edit = db.GuildChannelEdit(
                guild_channel_id=before.id,
                name=old_name,
                topic=old_topic,
                edit_time=datetime.datetime.now()
            )
            session.add(new_guild_channel_edit)

        session.merge(channel_model)
        session.commit()
        session.close()