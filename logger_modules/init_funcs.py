import db
import os

def print_initial_info(sessionmaker):
    session = sessionmaker()
    total_channels = session.query(db.DMChannel).count() + session.query(db.GuildChannel).count()
    total_messages = session.query(db.GuildMessage).count() + session.query(db.PrivateMessage).count()
    print(f"Providence has kept track of {total_messages} messages across {total_channels} channels.")
    session.close()


def make_static_dirs(config):
    if config["local_avatars"]:
        os.makedirs("static/avatars", exist_ok=True)
    if config["local_attachments"]:
        os.makedirs("static/attachments", exist_ok=True)
