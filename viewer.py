from flask import Flask, render_template
import yaml
import db
from sqlalchemy import create_engine, func, and_, cast, Date
from sqlalchemy.orm import scoped_session, sessionmaker, aliased
from datetime import datetime, timedelta
import re
import json
import viewer_modules.jinja_formatters

app = Flask(__name__)

with open("config.yml") as configfile:
    config = yaml.safe_load(configfile)

print("Read config.")

engine = create_engine(config["database_url"])
print("Connected to database.")
db.Base.metadata.bind = engine
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
db.Base.query = db_session.query_property()

# Register date filter
app.jinja_env.filters['date'] = viewer_modules.jinja_formatters.date


def process_messages(message_cls, attachment_cls, edit_cls, delete_cls, channel_id, date):
    """
    Function that like, gets messages from the database on a specific date.

    Used to prevent a lot of code repetition.

    Pass in references to the classes, not instantiated versions.

    Arguments:
        message_cls: Message model class used for the message type.
        attachment_cls: Attachment model class
        edit_cls: Message edits model class.
        channel_id: Channel ID to fetch messages from.
        date: Date to filter on.
    """

    date = datetime.strptime(date, "%Y-%m-%d")

    r_image = re.compile(r".*\.(jpg|jpeg|png|gif|webp)$")

    all_messages = db_session.query(message_cls).filter(message_cls.channel_id == channel_id).all()
    all_messages = [x for x in all_messages if x.created_at.date() == date.date()]

    all_messages.sort(key=lambda message: message.created_at)

    for message in all_messages:
        edit_list = db_session.query(edit_cls).filter_by(message_id=message.id).all()
        edit_list.sort(key=lambda edit: edit.edit_time)
        message.edits = edit_list
        message.real_content = message.content if len(edit_list) == 0 else message.edits[-1].content

        attachment_list = db_session.query(attachment_cls).filter_by(message_id=message.id).all()
        message.attachments = attachment_list

        for attachment in message.attachments:
            attachment.is_image = r_image.match(attachment.url)

        if message.embed:
            message.embed = json.loads(message.embed)

        if db_session.query(delete_cls).filter_by(message_id=message.id).scalar():
            message.deleted = True
        else:
            message.deleted = False

    all_messages_grouped = []
    previous_author = all_messages[0].author.id
    temp_list = []
    for message in all_messages:
        if message.author.id == previous_author:
            temp_list.append(message)
        else:
            all_messages_grouped.append(temp_list)
            temp_list = [message]
        previous_author = message.author.id
    all_messages_grouped.append(temp_list)

    return all_messages[0].channel, all_messages_grouped, len(all_messages)


def request_days(message_cls, channel_id):
    """
    Function that gets a list of all dates at which a message was send.

    Arguments:
        message_cls: Pass this in as a reference. Message model to use for fetching.
        channel_id: Channel ID to get dates from.
    """
    days = db_session.query(cast(message_cls.created_at, Date)).filter_by(channel_id=channel_id).distinct().all()
    days = [day[0] for day in days]
    channel = db_session.query(message_cls).filter_by(channel_id=channel_id).first().channel

    return channel, days

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/')
def view_root():
    return render_template("root.html")

@app.route('/guilds/')
def list_all_guilds():
    all_guilds = db_session.query(db.Guild).all()
    return render_template("guilds_list.html", guilds=all_guilds)


@app.route('/guilds/<guild_id>/')
def list_guild_channels(guild_id):
    channels = db_session.query(db.GuildChannel).filter_by(guild_id=guild_id).order_by(
        db.GuildChannel.created_at.asc()).all()
    return render_template("channel_list.html", channels=channels)

@app.route('/guilds/<guild_id>/info')
def show_single_guild(guild_id):
    guild = db_session.query(db.Guild).filter_by(id=guild_id).one()
    members = db_session.query(db.GuildMember).filter_by(guild_id=guild_id).all()
    return render_template("guild_details.html", guild=guild, members=members)


@app.route('/users/<user_id>/')
def show_single_user(user_id):
    user = db_session.query(db.User).filter_by(id=user_id).one()
    members = db_session.query(db.GuildMember).filter_by(user_id=user_id).all()
    return render_template("user_details.html", user=user, members=members)


@app.route('/channels/<channel_id>/')
def list_all_logged_days_for_channel(channel_id):
    channel, days = request_days(db.GuildMessage, channel_id)

    return render_template("days_list.html", channel=channel, days=days)


@app.route('/channels/<channel_id>/info')
def list_channel_info(channel_id):
    return "Not implemented."


@app.route('/channels/<channel_id>/<date>')
def list_all_messages_per_day(channel_id, date):
    channel, messages, total_messages = process_messages(db.GuildMessage, db.GuildMessageAttachments, db.GuildMessageEdit, db.GuildMessageDeletion, channel_id, date)

    return render_template("messages.html", channel=channel, all_messages_grouped=messages, message_length=total_messages)

@app.route('/dms/')
def list_all_dms():
    all_dms = db_session.query(db.DMChannel).all()
    return render_template("dm_list.html", dms=all_dms)


@app.route('/dms/<dm_id>/')
def list_all_logged_days_for_dm(dm_id):
    channel, days = request_days(db.PrivateMessage, dm_id)
    return render_template("days_list.html", channel=channel, days=days)


@app.route('/dms/<dm_id>/<date>')
def list_all_dms_per_day(dm_id, date):
    channel, messages, total_messages = process_messages(db.PrivateMessage, db.PrivateMessageAttachments, db.PrivateMessageEdit, db.PrivateMessageDeletion, dm_id, date)
    channel.guild = channel.remote_user # STUPID AND HACKY BUT IT WORKS!

    return render_template("messages.html", channel=channel, all_messages_grouped=messages, message_length=total_messages)


if __name__ == '__main__':
    app.run()
