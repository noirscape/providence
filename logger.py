import discord
import yaml
import logging

import logger_modules.db_ops
import logger_modules.embed
import logger_modules.init_funcs
from logger_modules.context_manager_session import session_scope

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import db
import concurrent.futures

logging.basicConfig(level=logging.WARN)

print("Starting Providence...")

with open("config.yml") as configfile:
    config = yaml.safe_load(configfile)

print("Read config.")

engine = create_engine(config["database_url"], pool_size=30)
print("Connected to database.")
db.Base.metadata.bind = engine

session_factory = sessionmaker(engine, autocommit=True)
DBSession = scoped_session(session_factory)

logger_modules.init_funcs.print_initial_info(DBSession)
logger_modules.init_funcs.make_static_dirs(config)

operations = logger_modules.db_ops.DatabaseOperations(config)
pool = concurrent.futures.ThreadPoolExecutor()
client = discord.Client()

@client.event
async def on_message(message):
    def store():
        with session_scope(DBSession) as session:
            if isinstance(message.channel, discord.DMChannel):
                operations.store_private_message(message, session)
            elif isinstance(message.channel, discord.TextChannel):
                operations.store_guild_message(message, session)
    await client.loop.run_in_executor(pool, store)

@client.event
async def on_message_edit(before, after):
    def store():
        if not after.edited_at:  # Apparently embed expansions trigger edits, but embed expansions dont set the edit date,
            # ergo embed expansions arent edits
            return
        with session_scope(DBSession) as session:
            if isinstance(after.channel, discord.DMChannel):
                operations.store_private_message_edit(before, after, session)
            elif isinstance(after.channel, discord.TextChannel):
                operations.store_guild_message_edit(before, after, session)

    await client.loop.run_in_executor(pool, store)


@client.event
async def on_message_delete(message):
    def store():
        with session_scope(DBSession) as session:
            if isinstance(message.channel, discord.DMChannel):
                operations.delete_private_message(message, session)
            elif isinstance(message.channel, discord.TextChannel):
                operations.delete_guild_message(message, session)

    await client.loop.run_in_executor(pool, store)


@client.event
async def on_private_channel_pins_update(channel, _):
    pins = await channel.pins()
    def store():
        with session_scope(DBSession) as session:
            current_pins = []
            for message in pins:
                operations.update_private_pin(message, session)
                current_pins.append(message.id)

            all_pins = operations.get_all_dm_pins(channel, session)
            loopable_all_pins = [x[0] for x in all_pins]

            for idx, pin in enumerate(loopable_all_pins):
                if pin not in current_pins:
                    operations.remove_dm_pin(all_pins[idx][1], session)
    await client.loop.run_in_executor(pool, store)


@client.event
async def on_guild_channel_pins_update(channel, _):
    pins = await channel.pins()
    def store():
        with session_scope(DBSession) as session:
            current_pins = []
            for message in pins:
                operations.update_guild_channel_pin(message, session)
                current_pins.append(message.id)

            all_pins = operations.get_all_guild_channel_pins(channel, session)
            loopable_all_pins = [x[0] for x in all_pins]

            for idx, pin in enumerate(loopable_all_pins):
                if pin not in current_pins:
                    operations.remove_guild_channel_pin(all_pins[idx][1], session)
    await client.loop.run_in_executor(pool, store)


@client.event
async def on_user_update(before, after):
    def store():
        with session_scope(DBSession) as session:
            operations.update_user(before, after, session)
    await client.loop.run_in_executor(pool, store)


@client.event
async def on_member_update(before, after):
    def store():
        with session_scope(DBSession) as session:
            operations.update_member(before, after, session)
    await client.loop.run_in_executor(pool, store)


@client.event
async def on_ready():
    print("Ready to log messages!")

client.run(config["token"], bot=config["bot"])
