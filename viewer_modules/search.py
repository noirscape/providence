import db
import viewer_modules.forms
from sqlalchemy import cast, Date

def search_messages_on_session(form_data: viewer_modules.forms.GeneralSearchForm, session):
    if form_data.search_choices.data == "DMs":
        query = session.query(db.PrivateMessage)
        class_type = db.PrivateMessage
    elif form_data.search_choices.data == "Guilds":
        query = session.query(db.GuildMessage)
        class_type = db.GuildMessage
    else:
        return form_data.search_choices.data

    if form_data.author.data != None:
        query = query.filter_by(author_id=form_data.author.data)


    if form_data.channel_id.data != None:
        query = query.filter_by(channel_id=form_data.channel_id.data)

    if form_data.text.data != "":
        query = query.filter(class_type.content.contains(form_data.text.data))

    if form_data.date.data != None:
        query = query.filter(cast(class_type.created_at, Date) == form_data.date.data)

    if form_data.guild_id.data != None:
        if class_type == db.GuildMessage:
            #query(FooBar).join(Bar).join(Foo).filter(Foo.name == "blah")
            query = query.join(db.GuildMessage.channel).filter(db.GuildChannel.guild_id == form_data.guild_id.data)

    query = query.limit(300)
    return query.all()

def search_users_on_session(form_data: viewer_modules.forms.UserSearchForm, session):
    query = session.query(db.User)

    if form_data.username.data != "":
        print(form_data.username.data)
        query = query.filter_by(name=form_data.username.data)

    if form_data.discriminator.data != None:
        query = query.filter_by(discriminator=form_data.discriminator.data)

    if form_data.id.data != None:
        print(form_data.id.data)
        query = query.filter_by(id=form_data.id.data)
    
    query = query.limit(300)
    return query.all()