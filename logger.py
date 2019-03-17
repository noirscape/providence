import discord
import yaml
from sqlalchemy import create_engine, exists, and_
from sqlalchemy.orm import sessionmaker
import db
import datetime
import json

print("Starting Providence...")

with open("config.yml") as configfile:
    config = yaml.load(configfile)

print("Read config.")

engine = create_engine(config["database_url"])
print("Connected to database.")
db.Base.metadata.bind = engine

DBSession = sessionmaker(engine)


def print_initial_info():
    session = DBSession()
    total_channels = session.query(db.DMChannel).count() + session.query(db.GuildChannel).count()
    total_messages = session.query(db.GuildMessage).count() + session.query(db.PrivateMessage).count()
    print(f"Providence has kept track of {total_messages} messages across {total_channels} channels.")
    session.close()


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
    new_user = db.User(id=user.id, name=user.name, discriminator=user.discriminator, is_bot=user.bot,
                       avatar=user.avatar_url, created_at=user.created_at, last_updated=datetime.datetime.now())
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
                                    content=message.content, embed=get_rich_embed(message), created_at=message.created_at)
    session.merge(new_message)
    for attachment in message.attachments:
        new_attachment = db.PrivateMessageAttachments(attachment_id=attachment.id, message_id=message.id,
                                                      filename=attachment.filename, url=attachment.url,
                                                      filesize=attachment.filesize)
        session.merge(new_attachment)
    session.commit()
    session.close()


def store_private_message_edit(before: discord.Message, after: discord.Message):
    session = DBSession()
    if not session.query(exists().where(db.PrivateMessage.id == before.id)).scalar():
        store_private_message(before)

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


def delete_private_message(message):
    session = DBSession()
    if not session.query(exists().where(db.PrivateMessage.id == message.id)).scalar():
        store_private_message(message)

    new_delete = db.PrivateMessageDeletion(message_id=message.id, deletion_time=datetime.datetime.now())
    session.merge(new_delete)
    session.commit()
    session.close()


print_initial_info()

client = discord.Client()


@client.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        store_private_message(message)
    elif isinstance(message.channel, discord.TextChannel):
        pass


@client.event
async def on_message_edit(before, after):
    if isinstance(after.channel, discord.DMChannel):
        store_private_message_edit(before, after)
    elif isinstance(after.channel, discord.TextChannel):
        pass


@client.event
async def on_message_delete(message):
    if isinstance(message.channel, discord.DMChannel):
        delete_private_message(message)
    elif isinstance(message.channel, discord.TextChannel):
        pass


@client.event
async def on_private_channel_pins_update(channel, _):
    pins = await channel.pins()
    current_pins = []
    for message in pins:
        update_private_pin(message)
        current_pins.append(message.id)

    all_pins = get_all_dm_pins(channel)
    loopable_all_pins = [x[0] for x in all_pins]

    for idx, pin in enumerate(loopable_all_pins):
        if pin not in current_pins:
            remove_dm_pin(all_pins[idx][1])


client.run(config["token"], bot=config["bot"])
