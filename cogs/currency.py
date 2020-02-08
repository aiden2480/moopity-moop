from asyncio import TimeoutError as AsyncTimeoutError
from datetime import datetime as dt, timedelta as td
from random import choice, randint
from typing import Optional

from discord import Colour, Embed, Member, User
from discord.ext import commands
from cogs.assets.custom import CustomCog, cooldown

WORK_PHRASES = [
    "It works, why?",
    "It doesn't work, why?",
    "HTML is a real programming language",
    "Python is the best programming language",
    "I can't believe it worked first time!",
    "It's not a bug it's a feature",
]
WEIRD_IOS = {"’": "'", "‘": "'", "“": '"', "”": '"'}

class Currency(CustomCog):
    """What's better than a currency system where all you can do is
    steal ingots from other people?"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db
        self.work_streak = dict() # {id: [hours_worked]}
        self.bank_cooldown = dict() # {id: last_accessed}

    @commands.command(aliases=["bal"])
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
            embed.description += f"Use `{ctx.clean_prefix}daily` to get started"
        
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
    @cooldown(1, 60*60*24, commands.BucketType.user)
    async def daily(self, ctx):
        """Redeem your daily ingots
        Gives you a random amount of money between 300 and 375 ingots"""
        amount = randint(300, 375)
        await ctx.send(f"Redeemed your daily cheque for **{amount} {self.bot.ingot}** 👍")
        await self.db.add_user_money(ctx.author.id, amount)

    @commands.command(aliases=["pay"])
    async def give(self, ctx, member:Member, amount: int):
        """I don't know why you would want to give away your hard earned ingots but sure"""
        author = await self.db.get_user_money(ctx.author.id, human_readable=False)
        amount = min([amount, author])
        
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
    @cooldown(1, 480, 1, 390, commands.BucketType.member)
    async def steal(self, ctx, victim: Member):
        """Attempts to steal from an unsuspecting victim\n
        You must have at least 150 ingots to try and steal,
        and your victim must have at least 100.

        There is a 40% chance that you will fail
        and, as compensation, give the user you
        attempted to steal from some ingots instead
        """
        # TODO: Fiddle with the win/lose ratio
        you = await self.db.get_user_money(ctx.author.id, human_readable=False)
        vtm = await self.db.get_user_money(victim.id, human_readable=False)
        won = randint(0, 100) > 40

        # Checks
        if victim == ctx.author:
            return await ctx.send("Congratulations, you played yourself")
        if victim.bot:
            return await ctx.send(f"Uh oh, you can't steal from bots! 🤖")
        if you < 150:
            return await ctx.send(f"You must have at least **150 {self.bot.ingot}** to steal from someone. You still need another **{150-you} {self.bot.ingot}** 🤷")
        if vtm < 100:
            return await ctx.send(f"Not worth it, **{victim}** only has **{vtm} {self.bot.ingot}**")

        if won:
            amount = randint(round(vtm/8), round(vtm/3))
            await ctx.send(f"Wow congrats **{ctx.author}**! You managed to steal **{amount} {self.bot.ingot}** from **{victim}**")
            
            try: await victim.send(f"Massive 🇫 **{ctx.author}** just stole **{amount} {self.bot.ingot}** from you in `{ctx.guild}` 😕")
            except: pass

            await self.db.add_user_money(ctx.author.id, amount)
            await self.db.add_user_money(victim.id, -amount)
            return

        amount = randint(round(you/8), round(you/3))
        msg = await ctx.send(f"Massive 🇫 for **{ctx.author}** who tried (and failed) steal from **{victim}** and had to pay them **{amount} {self.bot.ingot}**")
        await ctx.react(msg, "🇫")

        await self.db.add_user_money(ctx.author.id, -amount)
        await self.db.add_user_money(victim.id, amount)

    @commands.command()
    @cooldown(8, 90, 20, 90)
    async def flip(self, ctx, headsortails: str = ""):
        """Flip a coin, who knows, you might get some ingots"""
        call = headsortails.lower()
        esp = "heads" if randint(0, 1) else "tails"

        if call not in ["heads", "tails"]:
            return await ctx.send("You need to call either `heads` or `tails`. It's that obvious")
        if call != esp:
            await ctx.send(f"massive 🇫 It was `{esp}` and you picked `{call}` {self.bot.ingot} Waste of an ingot lmao")
            return await self.db.add_user_money(ctx.author.id, -1)
        await ctx.send(f"Congrats you have ESP. As a result, you were rewarded with **1 {self.bot.ingot}**")
        await self.db.add_user_money(ctx.author.id, 1)

    @commands.command(enabled=False)
    async def gamble(self, ctx, amount: int, roll: int=None):
        """Gamble some ingots, you might get some good stuff
        
        If you try and gamble a lot of your total ingots,
        your chance of winning will go down slightly each percent
        (To save my currency system from itself lol)
        """
        # TODO: This works, but still looks really gross
        ingots = await self.db.get_user_money(ctx.author.id, human_readable=False)
        perc = round(100*float(amount)/float(ingots)) # The percentage of the total ingots that were betted
        if amount > ingots:
            return await ctx.send("I'm pretty sure you can't gamble money that you don't have...")

        winpercent = 55
        eightypercent = randint(70, 90) # Give a bit of a range
        if perc > eightypercent: # They're trying to bet too much and must be
            await ctx.send("You're trying to bet more than 80% of your money!")
            for _ in range(perc-eightypercent, 100):
                winpercent -= 1

        rand = randint(1, 100) if not roll else roll
        won = rand in range(1, winpercent-1)
        extra = randint(5, 25)

        winemoji = "🎉" if rand > 10 else "🤑"
        loseemoji = "😕" if rand > 10 else "🌪️"
        emoji = winemoji if won else loseemoji

        if won:
            msg = f"🎉 You won `{amount}` {self.bot.ingot} Congratulations!"
            
            if rand < 10:
                amount += extra
                msg = f"🤑 **BONUS**: You found `{extra}` ingots from under the gambling machine. You won a total of `{amount}` ingots!"
        else:
            msg = f"😕 You lost `{amount}` {self.bot.ingot} Better luck next time"

            if rand < 10:
                amount += extra
                msg = f"🌪️ You gambled away **{amount}** ingots without any luck and to top it off, you were mugged outside the shop. You lost a further {extra}. rip"
        
        lol = await ctx.send(f"🎲 **{ctx.author.display_name}**, you gambled `{amount}` {self.bot.ingot} and rolled a `{rand}` which means you **{'win' if won else 'lost'}**!\n{msg}")
        await ctx.react(lol, emoji)

        await ctx.send(f"Ok ima give you `{amount if won else -amount}` now")
        # await self.db.add_user_money(amount if won else -amount)

    @commands.command()
    @cooldown(1, 60*60, 1, 60*50, commands.BucketType.user)
    async def work(self, ctx):
        if ctx.author.id not in self.work_streak.keys(): # User has no streak recorded
            self.work_streak[ctx.author.id] = []
        else: # Check if the streak has been broken and delete it
            streak = self.work_streak[ctx.author.id]
            now = dt.now()
            if not (now-td(hours=24) <= streak[-1] <= now):
                # Longer than twenty four hours since last work
                self.work_streak[ctx.author.id] = []
        
        phrase = choice(WORK_PHRASES)
        prompt = await ctx.send("Type the following in chat:\n`{}`".format("\u200b".join(phrase)))

        try:
            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

            msg = await self.bot.wait_for("message", check=check, timeout=45.0)
        except AsyncTimeoutError:
            await prompt.edit(content="Timed out \N{CONFUSED FACE}")
            return self.work_streak.pop(ctx.author.id)

        content = msg.content
        for ios, normal in WEIRD_IOS.items():
            content = msg.content.replace(ios, normal)

        if content.replace("\u200b", "") == phrase and "\u200b" in content:
            await ctx.send("No cheating You lose!")
            return self.work_streak.pop(ctx.author.id)
        if content.lower() != phrase.lower():
            await ctx.send(f"Wrong! 😕\n```diff\n+ {phrase}\n- {content}```")
            return self.work_streak.pop(ctx.author.id)

        self.work_streak[ctx.author.id].append(dt.now())
        moolah = 90+10*len(self.work_streak[ctx.author.id])
        embed = Embed(colour=Colour.blue())
        embed.description = """
            Correct well done! {}
            You earned `{}` ingots from a `{}` day streak
        """.format(
            self.bot.ingot, moolah,
            len(self.work_streak[ctx.author.id])
        )        
        await ctx.send(embed=embed)
        await self.db.add_user_money(ctx.author.id, moolah)

    @commands.group(aliases=["vault"])
    async def bank(self, ctx):
        """Keep ingots safe from thievery in your bank.
        
        The maximum amount of ingots your bank can hold
        is fluid - always half of your wallet at the time
        of deposit. Your if your wallet balance drops below
        this limit while your ingots are in the bank, they are
        still safe, however you can't add more until your
        wallet balance tops up again.

        If you are in the support server you can hold more in
        your bank account: an extra 5%.
        
        Unlike your wallet, you can't get the balance of another
        users bank, unless they show it to you"""
        if ctx.invoked_subcommand is not None:
            return

        embed = Embed(colour=Colour.blue())
        bank = await self.db.get_bank_money(ctx.author.id, human_readable=False)
        wallet = await self.db.get_user_money(ctx.author.id, human_readable=False)
        premium = self.bot.is_user_premium(ctx.author.id)

        embed.description = f"Balance: **{bank}/{round(wallet/2)} {self.bot.ingot}**"
        if bank > round(wallet/2):
            embed.set_footer(text="Bank full! No more ingots can be deposited")
        embed.set_author(name=f"{ctx.author}'s bank account", icon_url="https://cdn.discordapp.com/emojis/652064889602441216.png")
        await ctx.send(embed=embed)
    
    @bank.command(aliases=["dep"])
    async def deposit(self, ctx, amount: int):
        """Deposit ingots into your bank"""
        bal = await self.db.get_user_money(ctx.author.id, human_readable=False)
        bank = await self.db.get_bank_money(ctx.author.id, human_readable=False)
        premium = self.bot.is_user_premium(ctx.author.id)
        capacity = 55 if premium else 50
        amount = int(min([amount, (capacity*bal)/100]))

        if bank > (capacity*bal)/100:
            return await ctx.send("Your bank is full!")
        
        await ctx.send(f"Done! Your wallet balance is now `{bal-amount}` ingots and your bank holds `{bank+amount}`")
        await self.db.add_bank_money(ctx.author.id, amount)
        await self.db.add_user_money(ctx.author.id, -amount)

    @bank.command(aliases=["with"])
    async def withdraw(self, ctx, amount: int):
        """Withdraw ingots from your bank"""
        bank = await self.db.get_bank_money(ctx.author.id, human_readable=False)
        amount = min([amount, bank])

        await ctx.send(f"Withdrew `{amount}` ingots 👍")
        await self.db.add_user_money(ctx.author.id, amount)
        await self.db.add_bank_money(ctx.author.id, -amount)


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
