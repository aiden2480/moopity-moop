from discord import Embed, Colour
from discord.ext.commands import Cog, BucketType
from discord.ext.commands import command, is_owner, cooldown

from cogs.assets.custombot import CustomBot

class Currency(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.database = bot.database
    
    @command()
    @is_owner()
    @cooldown(1, 60*60*4, BucketType.user)
    async def givemoney(self, ctx):
        await ctx.send("Gave you $100 :thumbsup:")


def setup(bot):
    bot.add_cog(Currency(bot))
