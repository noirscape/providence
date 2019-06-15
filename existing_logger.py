import logging

import discord
import yaml
from discord.ext import commands
import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import db
from logger_modules.existing_log import ExistingArchiveHandler
from logger_modules.existing_db_ops import ExistingDatabaseOperations

LOGGER = logging.getLogger(__name__)

@click.command()
@click.argument("ID")
@click.option("--log-type", required=True, type=click.Choice(['guild', 'dm', 'channel']), help="Type of object you are trying to archive.")
def main(id, log_type):
    """Log existing messages from the source ID to the database.
    
    Type must be passed in and indicates what you are trying to archive.
    
    Logging guild will also update the member list of that guild with any unlogged users."""
    with open("config.yml", "r") as configfile:
        config = yaml.safe_load(configfile)

    engine = create_engine(config["database_url"], pool_size=30)
    print("Connected to database.")
    db.Base.metadata.bind = engine

    session_factory = sessionmaker(engine)
    DBSession = scoped_session(session_factory)
    db_ops = ExistingDatabaseOperations(config, DBSession)

    client = discord.Client()
    handler = ExistingArchiveHandler(client, config, db_ops)

    LOGGER.warning("[%s][%s] Creating asyncio task", log_type, id)
    if log_type == 'guild':
        client.loop.create_task(handler.archive_guild(id))
    elif log_type == 'dm':
        client.loop.create_task(handler.archive_dm(id))
    elif log_type == 'channel':
        client.loop.create_task(handler.archive_channel(id))

    client.run(config["token"], bot=config["bot"])

if __name__ == "__main__":
    main()