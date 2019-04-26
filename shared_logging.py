from sqlalchemy import create_engine, exists, and_
from sqlalchemy.orm import sessionmaker
import yaml
from sqlalchemy import create_engine, exists, and_
from sqlalchemy.orm import sessionmaker
import db
import datetime
import json
import os
import requests
import shutil
import discord

with open("config.yml") as configfile:
    config = yaml.safe_load(configfile)

engine = create_engine(config["database_url"], pool_size=30)
print("Connected to database.")
db.Base.metadata.bind = engine

DBSession = sessionmaker(engine)

def print_initial_info():
    session = DBSession()
    total_channels = session.query(db.DMChannel).count() + session.query(db.GuildChannel).count()
    total_messages = session.query(db.GuildMessage).count() + session.query(db.PrivateMessage).count()
    print(f"Providence has kept track of {total_messages} messages across {total_channels} channels.")
    session.close()


def make_static_dirs():
    if config["local_avatars"]:
        os.makedirs("static/avatars", exist_ok=True)
    if config["local_attachments"]:
        os.makedirs("static/attachments", exist_ok=True)


def get_rich_embed(message: discord.Message):
    if message.embeds:
        for e in message.embeds:  # type: discord.Embed
            if e.type == 'rich':
                return json.dumps(e.to_dict())
        else:
            return None
    else:
        return None


def create_user(user: discord.User):
    if config["local_avatars"]:
        r = requests.get(user.avatar_url_as(format='png'))
        with open(f"static/avatars/{user.id}.png", 'wb') as avatarfile:
            avatarfile.write(r.content)
        avatar_url = f"/static/avatars/{user.id}.png"
    else:
        avatar_url = str(user.avatar_url)

    new_user = db.User(id=user.id, name=user.name, discriminator=user.discriminator, is_bot=user.bot,
                       avatar=avatar_url, created_at=user.created_at, last_updated=datetime.datetime.now())
    session = DBSession()
    session.merge(new_user)
    session.commit()
    session.close()


def create_dm_channel(channel: discord.DMChannel):
    new_dm_channel = db.DMChannel(id=channel.id, remote_user_id=channel.recipient.id)
    session = DBSession()
    session.merge(new_dm_channel)
    session.commit()
    session.close()


def store_private_message(message: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.User.id == message.author.id)).scalar():
        create_user(message.author)
        session.close()
        session = DBSession()
    if not session.query(exists().where(db.User.id == message.channel.recipient.id)).scalar():
        create_user(message.channel.recipient)
        session.close()
        session = DBSession()
    if not session.query(exists().where(db.DMChannel.id == message.channel.id)).scalar():
        create_dm_channel(message.channel)
        session.close()
        session = DBSession()
    new_message = db.PrivateMessage(id=message.id, channel_id=message.channel.id, author_id=message.author.id,
                                    content=message.clean_content, embed=get_rich_embed(message),
                                    created_at=message.created_at)
    session.merge(new_message)
    for attachment in message.attachments:
        if config["local_attachments"]:
            r = requests.get(str(attachment.url))
            with open(f"static/attachments/{attachment.id}-{attachment.filename}", 'wb') as attachmentfile:
                attachmentfile.write(r.content)
            attachment_url = f"/static/attachments/{attachment.id}-{attachment.filename}.png"
        else:
            attachment_url = str(attachment.url)
        new_attachment = db.PrivateMessageAttachments(attachment_id=attachment.id, message_id=message.id,
                                                      filename=attachment.filename, url=attachment_url,
                                                      filesize=attachment.size)
        session.merge(new_attachment)
    session.commit()
    session.close()


def store_private_message_edit(before: discord.Message, after: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.PrivateMessage.id == before.id)).scalar():
        store_private_message(before)
        session.close()
        session = DBSession()

    if before.content == after.content:
        store_content = None
    else:
        store_content = after.content

    if get_rich_embed(before) == get_rich_embed(after):
        store_embed = None
    else:
        store_embed = get_rich_embed(after)

    new_message_edit = db.PrivateMessageEdit(message_id=after.id, content=store_content, embed=store_embed,
                                             edit_time=after.edited_at)
    session.merge(new_message_edit)
    session.commit()
    session.close()


def update_private_pin(message: discord.Message):
    session = DBSession()
    if session.query(exists().where(and_(db.DMChannelPins.message_id == message.id, db.DMChannelPins.is_pinned == True))
                     ).scalar():
        pass
    else:
        if not session.query(exists().where(db.PrivateMessage.id == message.id)).scalar():
            store_private_message(message)
        new_pin = db.DMChannelPins(dm_channel_id=message.channel.id, message_id=message.id, is_pinned=True,
                                   pinned_at=datetime.datetime.now())
        session.add(new_pin)
    session.commit()
    session.close()


def get_all_dm_pins(channel: discord.DMChannel) -> list:
    session = DBSession()
    pin_list = []
    for result in session.query(db.DMChannelPins).filter_by(dm_channel_id=channel.id):
        pin_list.append((result.message_id, result.pin_id))
    session.commit()
    session.close()
    return pin_list


def remove_dm_pin(pin_id: int):
    session = DBSession()
    pin = session.query(db.DMChannelPins).filter_by(pin_id=pin_id).one()
    if pin.is_pinned:
        pin.is_pinned = False
        pin.unpinned_at = datetime.datetime.now()
    session.merge(pin)
    session.commit()
    session.close()


def delete_private_message(message: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.PrivateMessage.id == message.id)).scalar():
        store_private_message(message)
        session.close()
        session = DBSession()

    new_delete = db.PrivateMessageDeletion(message_id=message.id, deletion_time=datetime.datetime.now())
    session.merge(new_delete)
    session.commit()
    session.close()


def create_member(user: discord.Member):
    session = DBSession()
    if not session.query(exists().where(db.User.id == user.id)).scalar():
        create_user(user)
        session.close()
        session = DBSession()
    if not session.query(exists().where(db.Guild.id == user.guild.id)).scalar():
        create_guild(user.guild)
        session.close()
        if user.id == user.guild.owner_id:
            return
        session = DBSession()
    new_member = db.GuildMember(user_id=user.id, guild_id=user.guild.id, nickname=user.nick,
                                last_updated=datetime.datetime.now())
    session.merge(new_member)
    session.commit()
    session.close()


def create_guild(guild: discord.Guild):
    session = DBSession()
    if not session.query(exists().where(db.User.id == guild.owner.id)).scalar():
        create_user(guild.owner)
        session.close()
        session = DBSession()
    new_guild = db.Guild(id=guild.id, name=guild.name, icon_url=str(guild.icon_url), owner_id=guild.owner_id,
                         created_at=guild.created_at, last_updated=datetime.datetime.now())
    session.merge(new_guild)
    session.commit()
    if not session.query(exists().where(and_(db.GuildMember.user_id == guild.owner_id,
                                             db.GuildMember.guild_id == guild.id))).scalar():
        create_member(guild.owner)
        session.close()
        session = DBSession()
    session.commit()
    session.close()


def create_guild_channel(channel: discord.TextChannel):
    session = DBSession()
    if not session.query(exists().where(db.Guild.id == channel.guild.id)).scalar():
        create_guild(channel.guild)
        session.close()
        session = DBSession()
    new_guild_channel = db.GuildChannel(id=channel.id, guild_id=channel.guild.id, name=channel.name,
                                        topic=channel.topic,
                                        created_at=channel.created_at, last_updated=datetime.datetime.now())
    session.merge(new_guild_channel)
    session.commit()
    session.close()


def store_guild_message(message: discord.Message):
    session = DBSession()
    if not session.query(exists().where(
            and_(db.GuildMember.user_id == message.author.id, db.GuildMember.guild_id == message.guild.id))).scalar():
        create_member(message.author)
        session.close()
        session = DBSession()
    if not session.query(exists().where(db.DMChannel.id == message.channel.id)).scalar():
        create_guild_channel(message.channel)
        session.close()
        session = DBSession()
    new_message = db.GuildMessage(id=message.id, channel_id=message.channel.id, author_id=message.author.id,
                                  content=message.clean_content, embed=get_rich_embed(message), created_at=message.created_at)
    session.merge(new_message)
    for attachment in message.attachments:
        if config["local_attachments"]:
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


def store_guild_message_edit(before: discord.Message, after: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.GuildMessage.id == before.id)).scalar():
        store_guild_message(before)

    if before.content == after.content:
        store_content = None
    else:
        store_content = after.clean_content

    if get_rich_embed(before) == get_rich_embed(after):
        store_embed = None
    else:
        store_embed = get_rich_embed(after)

    new_message_edit = db.GuildMessageEdit(message_id=after.id, content=store_content, embed=store_embed,
                                           edit_time=after.edited_at)
    session.merge(new_message_edit)
    session.commit()
    session.close()


def delete_guild_message(message: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.GuildMessage.id == message.id)).scalar():
        store_guild_message(message)

    new_delete = db.GuildMessageDeletion(message_id=message.id, deletion_time=datetime.datetime.now())
    session.merge(new_delete)
    session.commit()
    session.close()


def get_all_guild_channel_pins(channel: discord.TextChannel) -> list:
    session = DBSession()
    pin_list = []
    for result in session.query(db.GuildChannel).filter_by(id=channel.id):
        pin_list.append((result.message_id, result.pin_id))
    session.commit()
    session.close()
    return pin_list


def remove_guild_channel_pin(pin_id: int):
    session = DBSession()
    pin = session.query(db.GuildChannelPins).filter_by(pin_id=pin_id).one()
    if pin.is_pinned:
        pin.is_pinned = False
        pin.unpinned_at = datetime.datetime.now()
    session.merge(pin)
    session.commit()
    session.close()


def update_guild_channel_pin(message: discord.Message):
    session = DBSession()
    if session.query(exists().where(and_(db.GuildChannelPins.message_id == message.id, db.GuildChannelPins.is_pinned == True))
                     ).scalar():
        pass
    else:
        if not session.query(exists().where(db.GuildMessage.id == message.id)).scalar():
            store_private_message(message)
        new_pin = db.GuildChannelPins(dm_channel_id=message.channel.id, message_id=message.id, is_pinned=True,
                                   pinned_at=datetime.datetime.now())
        session.add(new_pin)
    session.commit()
    session.close()
