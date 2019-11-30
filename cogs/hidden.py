from discord import Colour, Embed, Game
from discord.ext import commands
from cogs.assets.custom import CustomCog


class Hidden(CustomCog, command_attrs=dict(hidden=True)):
    """Congrats you have found the hidden commands for the bot *shudders*"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot

    @commands.command(aliases=["\N{SHORTCAKE}"])
    async def cake(self, ctx):
        """Lets sit down and have some cake"""
        try:
            await ctx.react("\N{SHORTCAKE}")
            await ctx.send("\N{SHORTCAKE}")
        except:
            pass  # Don't really care if missing permissions


def setup(bot: commands.Bot):
    bot.add_cog(Hidden(bot), hide=True)
