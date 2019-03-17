import discord
import yaml
from sqlalchemy import create_engine, exists
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


print_initial_info()

client = discord.Client()


@client.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        store_private_message(message)
    elif isinstance(message.channel, discord.TextChannel):
        pass

client.run(config["token"], bot=config["bot"])
