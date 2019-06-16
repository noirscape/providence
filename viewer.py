from flask import Flask, render_template, request, flash, redirect
from flask_misaka import Misaka
import yaml
import db
from sqlalchemy import create_engine, func, and_, cast, Date
from sqlalchemy.orm import scoped_session, sessionmaker, aliased
from datetime import datetime, timedelta
import re
import json
import viewer_modules.jinja_formatters
import viewer_modules.forms as forms
import viewer_modules.search
import viewer_modules.session_filter as session_filter
from flask_breadcrumbs import Breadcrumbs, register_breadcrumb

app = Flask(__name__)

# Initialize flask extensions
Misaka(app)
Breadcrumbs(app=app)

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

# Register filters
app.jinja_env.filters['date'] = viewer_modules.jinja_formatters.date
app.jinja_env.filters['datetime'] = viewer_modules.jinja_formatters.datetime
app.jinja_env.filters['markdown_discord'] = viewer_modules.jinja_formatters.markdown_discord
app.config["SECRET_KEY"] = 'boop'

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

    return days

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@register_breadcrumb(app, '.', '#root')
@app.route('/')
def view_root():
    total_users = db_session.query(db.User).count()
    total_guilds = db_session.query(db.Guild).count()
    total_messages = db_session.query(db.GuildMessage).count() + db_session.query(db.PrivateMessage).count()
    total_deletions = db_session.query(db.GuildMessageDeletion).count() + db_session.query(db.PrivateMessageDeletion).count()

    return render_template("root.html", total_users=total_users, total_guilds=total_guilds, total_messages=total_messages, total_deletions=total_deletions)

@register_breadcrumb(app, '.guilds', 'Guilds')
@app.route('/guilds/')
def list_all_guilds():
    all_guilds = db_session.query(db.Guild).all()
    return render_template("guilds_list.html", guilds=all_guilds)

@register_breadcrumb(app, '.guilds.guild_id', 'Individual guild')
@app.route('/guilds/<int:guild_id>/')
def list_guild_channels(guild_id):
    channels = db_session.query(db.GuildChannel).filter_by(guild_id=guild_id).order_by(
        db.GuildChannel.created_at.asc()).all()
    return render_template("channel_list.html", channels=channels)

@register_breadcrumb(app, '.guilds.id.info', 'Guild info')
@app.route('/guilds/<int:guild_id>/info')
def show_single_guild(guild_id):
    guild = db_session.query(db.Guild).filter_by(id=guild_id).one()
    members = db_session.query(db.GuildMember).filter_by(guild_id=guild_id).all()
    roles = db_session.query(db.Role).filter_by(guild_id=guild_id).all()
    return render_template("guild_details.html", guild=guild, members=members, roles=roles)


@register_breadcrumb(app, '.users.id', 'User ID')
@app.route('/users/<int:user_id>/')
def show_single_user(user_id):
    user = db_session.query(db.User).filter_by(id=user_id).one()
    members = db_session.query(db.GuildMember).filter_by(user_id=user_id).all()
    return render_template("user_details.html", user=user, members=members)

@register_breadcrumb(app, '.users.id.guild_id', 'Membership info')
@app.route('/users/<int:user_id>/<int:guild_id>')
def show_single_member(user_id, guild_id):
    guild = db_session.query(db.Guild).filter_by(id=guild_id).one()
    member = db_session.query(db.GuildMember).filter_by(guild_id=guild.id, user_id=user_id).one()
    join_leave_audits = db_session.query(db.JoinLeaveAudit).filter_by(guild_id=guild.id, member_id=member.id).all()
    ban_audits = db_session.query(db.BanAudit).filter_by(member_id=member.id).all()
    roles_audit = db_session.query(db.RoleAudit).filter_by(member_id=member.id).all()
    current_roles = db_session.query(db.GuildMemberRoles).filter_by(member_id=member.id).all()
    return render_template("user_guild_history.html", guild=guild, join_leave_audits=join_leave_audits, ban_audits=ban_audits, roles_audit=roles_audit, current_roles=current_roles)

@register_breadcrumb(app, '.guilds.guild_id.channel_id', 'Channel days')
@app.route('/guilds/<int:guild_id>/<int:channel_id>/')
def list_all_logged_days_for_channel(guild_id, channel_id):
    days = request_days(db.GuildMessage, channel_id)
    days.sort()

    channel = db_session.query(db.GuildChannel).filter_by(id=channel_id).one()
    return render_template("guild_days_list.html", channel=channel, days=days)


@register_breadcrumb(app, '.guilds.guild_id.channel_id.info', 'Channel info')
@app.route('/guilds/<int:guild_id>/<int:channel_id>/info')
def list_channel_info(guild_id, channel_id):
    channel = db_session.query(db.GuildChannel).filter_by(id=channel_id).one()
    channel_edits = db_session.query(db.GuildChannelEdit).filter_by(guild_channel_id=channel_id).all()
    return render_template("channel_details.html", channel=channel, channel_edits=channel_edits)


@app.route('/guilds/<int:guild_id>/<int:channel_id>/<date>')
def list_all_messages_per_day(guild_id, channel_id, date):
    channel, messages, total_messages = process_messages(db.GuildMessage, db.GuildMessageAttachments, db.GuildMessageEdit, db.GuildMessageDeletion, channel_id, date)

    return render_template("messages.html", channel=channel, all_messages_grouped=messages, message_length=total_messages)

@register_breadcrumb(app, '.dms', 'DMs')
@app.route('/dms/')
def list_all_dms():
    all_dms = db_session.query(db.DMChannel).all()
    return render_template("dm_list.html", dms=all_dms)


@register_breadcrumb(app, '.dms.id', 'Individual DM')
@app.route('/dms/<int:dm_id>/')
def list_all_logged_days_for_dm(dm_id):
    days = request_days(db.PrivateMessage, dm_id)
    days.sort()
    channel = db_session.query(db.DMChannel).filter_by(id=dm_id).one()
    return render_template("dm_days_list.html", channel=channel, days=days)


@app.route('/dms/<int:dm_id>/<date>')
def list_all_dms_per_day(dm_id, date):
    channel, messages, total_messages = process_messages(db.PrivateMessage, db.PrivateMessageAttachments, db.PrivateMessageEdit, db.PrivateMessageDeletion, dm_id, date)
    channel.guild = channel.remote_user # STUPID AND HACKY BUT IT WORKS!

    return render_template("messages.html", channel=channel, all_messages_grouped=messages, message_length=total_messages)

@register_breadcrumb(app, '.roles', 'Roles list')
@app.route('/roles/')
def show_all_roles():
    all_roles = db_session.query(db.Role).all()

    for role in all_roles:
        role.total_members = len(session_filter.get_all_user_ids_with_role(db_session, role.id))

    return render_template("role_list.html", roles=all_roles)

@register_breadcrumb(app, '.roles.id', 'Individual roles')
@app.route('/roles/<int:role_id>')
def show_role_info(role_id):
    role = db_session.query(db.Role).filter_by(id=role_id).one()
    role_users = session_filter.get_all_user_ids_with_role(db_session, role_id)

    return render_template("role_details.html", role=role, role_users=role_users)


@register_breadcrumb(app, '.search', 'Search')
@app.route('/search/')
def search_overview():
    return render_template("search.html")


@register_breadcrumb(app, '.search.messages', 'Search Messages')
@app.route('/search/messages', methods=['GET', 'POST'])
def message_search():
    form = forms.GeneralSearchForm(request.form)
    results = []
    if request.method == 'POST' and form.validate_on_submit():
        return message_results(form)
    return render_template("search_messages.html", form=form, results=results)


@register_breadcrumb(app, '.search.users', 'Search users')
@app.route('/search/users', methods=['GET', 'POST'])
def user_search():
    form = forms.UserSearchForm(request.form)
    results = []
    if request.method == 'POST' and form.validate_on_submit():
        return user_results(form)
    return render_template("search_user.html", form=form, results=results)


def user_results(form):
    results = []
    results = viewer_modules.search.search_users_on_session(form, db_session)
    print(results)
    return render_template("search_user.html", form=form, results=results)


def message_results(form):
    results = []
    results = viewer_modules.search.search_messages_on_session(form, db_session)
    return render_template("search_messages.html", form=form, results=results)

if __name__ == '__main__':
    app.run()
