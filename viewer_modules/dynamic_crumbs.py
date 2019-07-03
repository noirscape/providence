from flask import request
import db

def user_id(*args, **kwargs):
    user_id = request.view_args['user_id']
    user = db.User.query.get(user_id)
    return [{'text': user.name + '#' + '{0:04d}'.format(user.discriminator), 'url': ''}]

def guild_id(*args, **kwargs):
    guild_id = request.view_args['guild_id']
    guild = db.Guild.query.get(guild_id)
    return [{'text': guild.name, 'url': ''}]

def guild_channel_id(*args, **kwargs):
    channel_id = request.view_args['channel_id']
    channel = db.GuildChannel.query.get(channel_id)
    return [{'text': '#' +  channel.name, 'url': ''}]

def dm_id(*args, **kwargs):
    dm_id = request.view_args['dm_id']
    dm = db.DMChannel.query.get(dm_id)
    user = dm.remote_user
    return [{'text': user.name + '#' + '{0:04d}'.format(user.discriminator), 'url': ''}]