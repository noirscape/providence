import discord
import yaml

print("Starting Providence...")

with open("config.yml") as configfile:
    config = yaml.safe_load(configfile)

print("Read config.")

from shared_logging import *

print_initial_info()
make_static_dirs()
client = discord.Client()


@client.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel):
        store_private_message(message)
    elif isinstance(message.channel, discord.TextChannel):
        store_guild_message(message)


@client.event
async def on_message_edit(before, after):
    if not after.edited_at:  # Apparently embed expansions trigger edits, but embed expansions dont set the edit date,
        # ergo embed expansions arent edits
        return
    if isinstance(after.channel, discord.DMChannel):
        store_private_message_edit(before, after)
    elif isinstance(after.channel, discord.TextChannel):
        store_guild_message_edit(before, after)


@client.event
async def on_message_delete(message):
    if isinstance(message.channel, discord.DMChannel):
        delete_private_message(message)
    elif isinstance(message.channel, discord.TextChannel):
        delete_guild_message(message)


@client.event
async def on_private_channel_pins_update(channel, _):
    pins = await channel.pins()
    current_pins = []
    for message in pins:
        update_private_pin(message)
        current_pins.append(message.id)

    all_pins = get_all_dm_pins(channel)
    loopable_all_pins = [x[0] for x in all_pins]

    for idx, pin in enumerate(loopable_all_pins):
        if pin not in current_pins:
            remove_dm_pin(all_pins[idx][1])


client.run(config["token"], bot=config["bot"])
