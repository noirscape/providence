import json
import discord

def get_rich_embed(message: discord.Message):
    if message.embeds:
        for e in message.embeds:  # type: discord.Embed
            if e.type == 'rich':
                return json.dumps(e.to_dict())
        else:
            return None
    else:
        return None
