from discord import Colour, Embed, Game
from discord.ext import commands


class Hidden(commands.Cog, command_attrs=dict(hidden=True)):
    """Congrats you have found the hidden commands for the bot *shudders*"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["\N{SHORTCAKE}"])
    async def cake(self, ctx):
        """Lets sit down and have some cake"""
        try:
            await ctx.message.add_reaction("\N{SHORTCAKE}")
            await ctx.send("\N{SHORTCAKE}")
        except:
            pass  # Don't really care if missing permissions


def setup(bot: commands.Bot):
    bot.add_cog(Hidden(bot), hide=True)
