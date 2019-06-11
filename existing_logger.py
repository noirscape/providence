import discord
import yaml
from discord.ext import commands

with open("config.yml", "r") as configfile:
    config = yaml.safe_load(configfile)

class ExistingLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


bot = commands.Bot("-]", description="Existing logger.")
bot.add_cog(ExistingLogger(bot))
bot.run(config["token"], bot=config["bot"])
