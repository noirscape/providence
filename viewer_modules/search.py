import db
import viewer_modules.forms

def search_on_session(form_data: viewer_modules.forms.GeneralSearchForm, session):
    if form_data.search_choices.data == "DMs":
        query = session.query(db.PrivateMessage)
    elif form_data.search_choices.data == "Guilds":
        query = session.query(db.GuildMessage)
    else:
        return False

    if form_data.author:
        query.filter_by(author_id=form_data.author.data)


    query = query.limit(20)
    return query.all()