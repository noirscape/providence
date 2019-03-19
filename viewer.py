from flask import Flask, render_template
import yaml
import db
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

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


if __name__ == '__main__':
    app.run()
