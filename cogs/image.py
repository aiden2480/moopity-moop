from io import BytesIO
from urllib.parse import urlencode
from datetime import datetime as dt

from discord import Embed, Colour
from discord.ext import commands
from cogs.assets.custom import CustomCog

BASE_URL="https://memegen.chocolatejade42.repl.co"

class Image(CustomCog):
    """Image generation commands"""
    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.sess = bot.session
    
    @commands.command(aliases=["clubp"])
    async def clubpenguin(self, ctx, *, msg):
        """The generic club penguin ban message"""
        embed=Embed(colour=Colour.blue())
        embed.set_image(url=f"{BASE_URL}/clubpenguin.jpg?{urlencode({'msg':msg})}")
        await ctx.send(embed=embed)

    @commands.command()
    async def zero(self, ctx, *, msg):
        """Pimples? Zero! Blackheads? Zero!"""
        embed=Embed(colour=Colour.blue())
        embed.set_image(url=f"{BASE_URL}/zero.jpg?{urlencode({'msg':msg})}")
        await ctx.send(embed=embed)

    @commands.command()
    async def mario(self, ctx, *, msg):
        """Suicidal mario"""
        embed=Embed(colour=Colour.blue())
        embed.set_image(url=f"{BASE_URL}/mario.jpg?{urlencode({'msg':msg})}")
        await ctx.send(embed=embed)

    @commands.command()
    async def catmeme(self, ctx, *, msg):
        """Why tf she so mad at that cat though"""
        embed=Embed(colour=Colour.blue())
        args = msg.split("|", maxsplit=1)
        if len(args) != 2:
            return await ctx.send(f"You must send text in the format `{ctx.prefix}{ctx.command} first | second`")
        first = args[0].strip()
        second = args[1].strip()
        embed.set_image(url=f"{BASE_URL}/catmeme.jpg?{urlencode({'first':first, 'second':second})}")
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Image(bot))
