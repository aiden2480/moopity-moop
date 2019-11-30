from random import randint, shuffle
from typing import Optional

from discord import Colour, Embed, Member, User
from discord.ext import commands
from cogs.assets.custom import CustomCog

MIN_STEAL_AMOUNT = 30
MAX_STEAL_AMOUNT = 2000


class Currency(CustomCog):
    """What's better than a currency system where all you can do is
    steal money from other people?"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db

    @commands.command(aliases=["bal"])
    @commands.cooldown(3, 10, commands.BucketType.user)
    async def balance(self, ctx, member: Member = "self"):
        """Find a user's balance"""
        member = ctx.author if member == "self" else member
        moolah = await self.db.get_user_money(member.id)
        await ctx.send(f"**{member}** has `${moolah}`")

    @commands.command(aliases=["lb", "topusers", "leaders"])
    async def leaderboard(self, ctx):
        """Shows who has the most amount of money in this server"""
        embed = Embed(colour=Colour.blue(), description="")
        if ctx.guild is None:
            embed.description=f"\N{TRIDENT EMBLEM} [Online global leaderboard]({self.bot.website_url}/leaderboard)"
            embed.set_author(name="Global bot leaderboard", icon_url=self.bot.user.avatar_url)
            return await ctx.send(embed=embed)

        embed.title = "The richest users in this server"
        lbdata = await self.db.get_leaderboard(ctx.guild, maxusers=10)
        if not lbdata:
            embed.description += "It seems that literally everyone in this server is broke \N{SHRUG}\n"
            embed.description += f"Use {ctx.prefix}daily to get started"
        
        for id_, money in lbdata.items():
            emoji = self.db.LEADERBOARD_EMOJI_KEY.get(
                len(embed.description.split("\n")),
            self.db.LEADERBOARD_DEFAULT_EMOJI)
            embed.description += f"\n{emoji} **{self.bot.get_user(id_)}** has `${money:,}`"
        
        url = f"{self.bot.website_url}/leaderboard?guild={ctx.guild.id}"
        embed.description += f"\n\nSee the online leaderboard [here]({url} \"{ctx.guild}'s leaderboard\")"
        embed.set_footer(text=f"Richest users in {ctx.guild}", icon_url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=["freemoney"])
    @commands.cooldown(1, 60 * 60 * 4, commands.BucketType.user)
    async def daily(self, ctx):
        """Redeem your daily cash
        Gives you a random amount of money between 300 and 375 dollars
        into your wallet"""
        amount = 300 + randint(0, 75)
        await ctx.send(f"Redeemed your daily cheque for `${amount}` :thumbsup:")
        await self.db.add_user_money(ctx.author.id, amount)

    @commands.command()
    async def give(self, ctx, member:Member, amount: int):
        """I don't know why you would want to give away your hard earned money but sure"""
        if amount < 0:
            return await ctx.send("That's illegal!")
        if member == ctx.author:
            return await ctx.send("Giving yourself money? 🤔")
        
        await ctx.send(f"Congrats, you just wasted a hard earned `${amount}`")
        await self.db.add_user_money(ctx.author.id, -amount)
        await self.db.add_user_money(member.id, amount)

    @commands.command(enabled=False)
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def steal(self, ctx, victim: Member):
        """Attempts to steal from <victim>\n
        Both you and the user you are attemping to
        steal from must have at least $75 or this
        will fail

        There is a 35% chance that you will fail
        and, as compensation, give the user you
        attempted to steal from some money

        The only bot that you can steal from is this one.
        However, there is a 60% chance that you will fail,
        but also a 125% reward if you are successful"""
        # FIXME: Check this hasn't broken again
        you = await self.db.get_user_money(ctx.author.id, human_readable=False)
        vtm = await self.db.get_user_money(victim.id, human_readable=False)
        win = randint(0, 100) > 35
        amount = randint(MIN_STEAL_AMOUNT, MAX_STEAL_AMOUNT)

        if victim == ctx.author:
            return await ctx.send("Congratulations, you played yourself")
        if victim.bot and victim != ctx.guild.me:
            return await ctx.send(f"Uh oh, you can't steal from bots! \N{ROBOT FACE} ~~||except me||~~")
        if you < 75:
            return await ctx.send(f"You must have at least `$75` to steal from someone. You still need another `${75-you}` \N{SHRUG}")
        if vtm < 75 and victim != ctx.guild.me:
            return await ctx.send(f"Not worth it, **{victim}** only has `${vtm}`")
        if victim == ctx.guild.me:
            win = randint(0, 100) > 60


        if win:
            while amount > vtm:
                amount = randint(MIN_STEAL_AMOUNT, amount)

            await ctx.send(f"Wow congrats **{ctx.author}**! You managed to steal `${amount}` from **{victim}**")
            try: await victim.send(
                    f"Massive 🇫 {ctx.author.mention} just stole `${amount}` from you in `{ctx.guild}` \N{CONFUSED FACE}"
                )
            except: pass
        else:
            while amount > you:
                amount = randint(MIN_STEAL_AMOUNT, amount)

            msg=await ctx.send(f"Massive 🇫 for **{ctx.author}** who tried (and failed) steal from **{victim}** and had to pay them `${amount}`")
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
            await ctx.send(f"massive 🇫 It was `{esp}` and you picked `{call}` \N{MONEY BAG} Waste of a coin lmao")
            return await self.db.add_user_money(ctx.author.id, -1)
        await ctx.send(f"Congrats you have ESP. As a result, you were rewarded with `$1`")
        await self.db.add_user_money(ctx.author.id, 1)


    @commands.command(enabled=False)
    async def blackjack(self, ctx, amount:int):
        """Play blackjack with the bot
        TODO: update description
        https://github.com/gsamarakoon/Fun-projects-for-Python/blob/master/A%20game%20of%20BlackJack.ipynb
        """
        # TODO: I might just delete this lol
        amt = await self.db.get_user_money(ctx.author.id, human_readable=False)
        if amount > amt:
            return await ctx.send(f"You only have `${amt}` to bet..")
        
        embed = Embed(colour=Colour.blue(), title=f"{ctx.author}'s blackjack game")
        msg=await ctx.send(embed=embed)
        for reaction in "\U0001f1ed \U0001f1f8".split():
            await msg.add_reaction(reaction)
            # TODO: This is going to suck a lot lmao


class AdminCurrency(CustomCog):
    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db

    @commands.command()
    @commands.is_owner()
    async def givemoney(self, ctx, user: Optional[User] = None, amount=100):
        usr = user or ctx.author
        await self.db.add_user_money(usr.id, amount)
        await ctx.send(f":thumbsup: Gave `${amount}` to **{usr}**")


def setup(bot: commands.Bot):
    bot.add_cog(Currency(bot))
    bot.add_cog(AdminCurrency(bot), hide=True)
