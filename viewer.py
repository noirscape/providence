from flask import Flask, render_template
import yaml
import db
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import scoped_session, sessionmaker, aliased
from datetime import datetime, timedelta
import re

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


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.route('/')
@app.route('/guilds/')
def list_all_guilds():
    all_guilds = db_session.query(db.Guild).all()
    return render_template("guilds_list.html", guilds=all_guilds)


@app.route('/guilds/<guild_id>/')
def list_guild_channels(guild_id):
    channels = db_session.query(db.GuildChannel).filter_by(guild_id=guild_id).order_by(
        db.GuildChannel.created_at.asc()).all()
    return render_template("channel_list.html", channels=channels)


@app.route('/users/<user_id>')
def show_single_user(user_id):
    user = db_session.query(db.User).filter_by(id=user_id).one()
    members = db_session.query(db.GuildMember).filter_by(user_id=user_id).all()
    return render_template("user_details.html", user=user, members=members)


@app.route('/channels/<channel_id>')
def list_all_logged_days_for_channel(channel_id):
    all_messages = db_session.query(db.GuildMessage).filter_by(channel_id=channel_id).all()

    # This should probably be a part of the query lol
    days = []
    prev_day = None
    for message in all_messages:
        if prev_day is None:
            days.append(message.created_at.date())
            prev_day = message.created_at
            continue
        if prev_day.date() != message.created_at.date():
            prev_day = message.created_at
            days.append(message.created_at.date())

    return render_template("days_list.html", channel=all_messages[0].channel, days=days)


@app.route('/channels/<channel_id>/<date>')
def list_all_messages_per_day(channel_id, date):
    date = datetime.strptime(date, "%Y-%m-%d")

    r_image = re.compile(r".*\.(jpg|jpeg|png|gif|webp)$")

    all_messages = db_session.query(db.GuildMessage).filter(db.GuildMessage.channel_id == channel_id).all()
    all_messages = [x for x in all_messages if x.created_at.date() == date.date()]

    all_messages.sort(key=lambda message: message.created_at)

    for message in all_messages:
        edit_list = db_session.query(db.GuildMessageEdit).filter_by(message_id=message.id).all()
        edit_list.sort(key=lambda edit: edit.edit_time)
        message.edits = edit_list
        message.real_content = message.content if len(edit_list) == 0 else message.edits[-1].content

        attachment_list = db_session.query(db.GuildMessageAttachments).filter_by(message_id=message.id).all()
        message.attachments = attachment_list

        for attachment in message.attachments:
            attachment.is_image = r_image.match(attachment.url)
        

    return render_template("messages.html", channel=all_messages[0].channel, messages=all_messages, message_length=len(all_messages))


if __name__ == '__main__':
    app.run()
