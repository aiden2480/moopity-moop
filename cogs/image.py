from io import BytesIO
from urllib.parse import urlencode

from discord import Embed, Colour, File
from discord.ext import commands
from cogs.assets.custom import CustomCog

BASE_URL="https://memegen.chocolatejade42.repl.co"
conv = dict(
    grass=1, diamond=2, diamondsword=3, sword=3, creeper=4, pig=5,
    tnt=6, cookie=7, heart=8, bed=9, cake=10, sign=11,
    rail=12, crafting=13, redstone=14, fire=15, cobweb=16, chest=17,
    furnace=18, book=19, stone=20, woodenplanks=21, ingot=22, ironingot=22,
    goldingot=23, door=24, irondoor=25, diamondchestplate=26, flintandsteel=27,
    bottle=28, splashpotion=29, spawnegg=30, egg=30, charcoal=31, ironsword=32,
    bow=33, arrow=34, iconchestplate=35, chestplate=35, bucket=36, waterbucket=37,
    lavabucket=38, milkbucket=39,
)

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
            return await ctx.send(f"You must send text in the format `{ctx.clean_prefix}{ctx.command} first | second`")
        first = args[0].strip()
        second = args[1].strip()
        embed.set_image(url=f"{BASE_URL}/catmeme.jpg?{urlencode({'first':first, 'second':second})}")
        await ctx.send(embed=embed)
    
    @commands.command()
    async def achievement(self, ctx, *, msg=""):
        """Create an achievement in the Minecraft format"""
        args = msg.split("|", maxsplit=2)
        if len(args) not in [2, 3]:
            return await ctx.send(embed=Embed(colour=Colour.blue(), description=
                f"You must send text in the format `{ctx.clean_prefix}{ctx.command} <title> | <description> | [icon]`\nIf supplied, the icon must be one of the icons below, otherwise a default cake will be used"
            ).add_field(name="Icons", value=f"`{'`, `'.join(conv.keys())}`"))
        title = args[0].strip()
        descrip = args[1].strip()
        icon = args[2].strip() if len(args) == 3 else "cake"

        await ctx.trigger_typing()
        async with self.sess.get(f"https://minecraftskinstealer.com/achievement/{conv.get(icon)}/{title}/{descrip}") as resp:
            file=File(BytesIO(await resp.content.read()), filename="achievement.png")
            await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Image(bot))
