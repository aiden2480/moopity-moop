from random import randint
from typing import Optional

from discord import Colour, Embed, Member, User
from discord.ext import commands
from cogs.assets.custom import CustomCog


class Currency(CustomCog):
    """What's better than a currency system where all you can do is
    steal ingots from other people?"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db

    @commands.command(aliases=["bal"])
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def balance(self, ctx, member: Member="self"):
        """Find a user's balance"""
        member = ctx.author if member == "self" else member
        moolah = await self.db.get_user_money(member.id)
        await ctx.send(f"**{member}** has **{moolah} {self.bot.ingot}**")

    @commands.command(aliases=["lb", "topusers", "leaders"])
    async def leaderboard(self, ctx):
        """Shows who has the most amount of ingots in this server"""
        embed = Embed(colour=Colour.blue(), description="")
        if ctx.guild is None:
            embed.description=f"🔱 [Online global leaderboard]({self.bot.website_url}/leaderboard)"
            embed.set_author(name="Global bot leaderboard", icon_url=self.bot.user.avatar_url)
            return await ctx.send(embed=embed)

        embed.title = "The richest users in this server"
        lbdata = await self.db.get_leaderboard(ctx.guild, maxusers=10)
        if not lbdata:
            embed.description += "It seems that literally everyone in this server is broke 🤷\n"
            embed.description += f"Use {ctx.clean_prefix}daily to get started"
        
        for id_, money in lbdata.items():
            emoji = self.db.LEADERBOARD_EMOJI_KEY.get(
                len(embed.description.split("\n")),
            self.db.LEADERBOARD_DEFAULT_EMOJI)
            embed.description += f"\n{emoji} **{self.bot.get_user(id_)}** has **{money:,} {self.bot.ingot}**"
        
        url = f"{self.bot.website_url}/leaderboard?guild={ctx.guild.id}"
        embed.description += f"\n\nSee the online leaderboard [here]({url} \"{ctx.guild}'s leaderboard\")"
        embed.set_footer(text=f"Richest users in {ctx.guild}", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["freemoney"])
    @commands.cooldown(1, 60 * 60 * 4, commands.BucketType.user)
    async def daily(self, ctx):
        """Redeem your daily ingots
        Gives you a random amount of money between 300 and 375 ingots
        into your wallet"""
        amount = 300 + randint(0, 75)
        await ctx.send(f"Redeemed your daily cheque for **{amount} {self.bot.ingot}** 👍")
        await self.db.add_user_money(ctx.author.id, amount)

    @commands.command()
    async def give(self, ctx, member:Member, amount: int):
        """I don't know why you would want to give away your hard earned ingots but sure"""
        if amount < 0:
            return await ctx.send("That's illegal!")
        if member == ctx.author:
            return await ctx.send("Giving yourself ingots? 🤔")
        if member.bot:
            return await ctx.send("Trying to give bots ingots? 🤔")
        
        await ctx.send(f"Congrats, you just wasted a hard earned **{amount} {self.bot.ingot}**")
        await self.db.add_user_money(ctx.author.id, -amount)
        await self.db.add_user_money(member.id, amount)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 300, commands.BucketType.user)
    @commands.cooldown(3, 1200, commands.BucketType.user)
    async def steal(self, ctx, victim: Member):
        # FIXME: Change all the ratios for stealing and stoof
        """Attempts to steal from an unsuspecting victim\n
        Both you and the user you are attemping to
        steal from must have at least 75 ingots or this
        will fail

        There is a 35% chance that you will fail
        and, as compensation, give the user you
        attempted to steal from some ingots instead

        The only bot that you can steal from is this one.
        However, there is a 60% chance that you will fail,
        but also a 125% reward if you are successful"""
        you = await self.db.get_user_money(ctx.author.id, human_readable=False)
        vtm = await self.db.get_user_money(victim.id, human_readable=False)
        win = randint(0, 100) > 35
        amount = randint(round(vtm/8), round(vtm/3))

        if victim == ctx.author:
            return await ctx.send("Congratulations, you played yourself")
        if victim.bot and victim != ctx.guild.me:
            return await ctx.send(f"Uh oh, you can't steal from bots! 🤖 ~~except me~~")
        if you < 75:
            return await ctx.send(f"You must have at least **75 {self.bot.ingot}** to steal from someone. You still need another **{75-you} {self.bot.ingot}** 🤷")
        if vtm < 75 and victim != ctx.guild.me:
            return await ctx.send(f"Not worth it, **{victim}** only has **{vtm} {self.bot.ingot}**")
        if victim == ctx.guild.me:
            win = randint(0, 100) > 60
            amount = randint(0, 500)


        if win:
            while amount > vtm:
                amount = randint(20, amount)

            await ctx.send(f"Wow congrats **{ctx.author}**! You managed to steal **{amount} {self.bot.ingot}** from **{victim}**")
            try: await victim.send(f"Massive 🇫 {ctx.author.mention} just stole **{amount} {self.bot.ingot}** from you in `{ctx.guild}` 😕")
            except: pass
        else:
            while amount > you:
                amount = randint(20, amount)

            msg=await ctx.send(f"Massive 🇫 for **{ctx.author}** who tried (and failed) steal from **{victim}** and had to pay them **{amount} {self.bot.ingot}**")
            await ctx.react(msg, "🇫")
            amount=-amount

        # Transfer the money
        await self.db.add_user_money(ctx.author.id, amount)
        if not victim.bot:
            await self.db.add_user_money(victim.id, -amount)

    @commands.command()
    async def flip(self, ctx, headsortails: str = ""):
        """Flip a coin, who knows, you might get some money"""
        call = headsortails.lower()
        esp = "heads" if randint(0, 1) else "tails"

        if call not in ["heads", "tails"]:
            return await ctx.send("You need to call either `heads` or `tails`. It's that obvious")
        if call != esp:
            await ctx.send(f"massive 🇫 It was `{esp}` and you picked `{call}` {self.bot.ingot} Waste of an ingot lmao")
            return await self.db.add_user_money(ctx.author.id, -1)
        await ctx.send(f"Congrats you have ESP. As a result, you were rewarded with **1 {self.bot.ingot}**")
        await self.db.add_user_money(ctx.author.id, 1)


class AdminCurrency(CustomCog):
    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db

    @commands.command(aliases=["giveingots"])
    @commands.is_owner()
    async def givemoney(self, ctx, user: Optional[User]=None, amount=100):
        """Give a user sum ingots"""
        usr = user or ctx.author
        await self.db.add_user_money(usr.id, amount)
        await ctx.send(f"👍 Gave **{amount} {self.bot.ingot}** to **{usr}**")


def setup(bot: commands.Bot):
    bot.add_cog(Currency(bot))
    bot.add_cog(AdminCurrency(bot), hide=True)
