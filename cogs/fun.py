from asyncio import TimeoutError as AsyncTimeoutError
from datetime import datetime as dt
from html import unescape
from io import BytesIO
from random import choice, randint, shuffle
from time import perf_counter

from akinator import CantGoBackAnyFurther
from akinator.async_aki import Akinator
from discord import Colour, Embed, File
from discord.ext import commands
from cogs.assets.custom import CustomCog

REDDIT_POST_LIMIT=75
GLITCH_ALL = "".join((chr(i) for i in range(0x300, 0x370))) + "".join((chr(i) for i in range(0x483, 0x48a)))


class Fun(CustomCog):
    """Fun commands such as games and special features
    Some have absolutely nothing to do with Minecraft! yay!"""
    # TODO: Make a cog listener that gives user money for using the commands

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db
        self.sess = bot.session
        self.busdriverthanks = 0

    @commands.group(name="akinator", aliases=["aki"])
    @commands.cooldown(2, 60, commands.BucketType.user)
    @commands.bot_has_permissions(add_reactions=True)
    async def akinator_cmd(self, ctx):
        """A classic game of Akinator!"""
        if ctx.invoked_subcommand:
            return
        await ctx.send(
            f"Use `{ctx.clean_prefix}{ctx.command} help` for help about the akinator " \
            f"commands or `{ctx.clean_prefix}{ctx.command} start` to start a new game"
        )

    @akinator_cmd.command()
    async def help(self, ctx):
        "Pls send help! I have no" "idea how this game works!"
        e = Embed(
            colour=Colour.blue(),
            timestamp=dt.utcnow(),
            title="Akinator help command",
            description=f"Use the command `{ctx.clean_prefix}akinator` to start a new game of Akinator",
        )

        e.add_field(
            name="What is Akinator?",
            value="Akinator is an online character guessing game where I try to guess what character you are thinking of and ask a series of questions to help me!",
        )
        e.add_field(
            name="Progress bar",
            value="The progress bar at the top of the interactive game represents how close I think I am to guessing your character",
        )
        e.add_field(
            name="Reactions",
            value="The 5 different reactions represent the different options:\n>>> **👍 Yes 👎 No 🤷 I don't know**\n>>>** 🔼 Probably 🔽 Probably not**",
        )

        e.set_thumbnail(url="https://bit.ly/30aHPen")
        e.set_footer(text="Akinator help command", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    @akinator_cmd.command(name="start", aliases=["new"])
    async def akinator_main_cmd(self, ctx):
        if ctx.guild is not None:
            perms = ctx.channel.permissions_for(ctx.guild.me)
        else:
            perms = ctx.channel.permissions_for(ctx.bot.user)

        e = Embed(
            timestamp=dt.utcnow(),
            colour=Colour.blue(),
            description="Setting up your Akinator game!\n\n"
            "Please give me a moment while I get things ready for you.\nThis could take a few seconds.. ⌛",
        )
        e.set_author(name=f"Akinator with {ctx.author}", icon_url="https://bit.ly/30aHPen")
        msg = await ctx.send(embed=e)

        aki = Akinator()
        q = await aki.start_game()
        for emoji in "👍👎🤷🔼🔽":
            await msg.add_reaction(emoji)

        async def uinput(*args):
            """Short for user input, get's a user's message from discord"""

            def check(reaction, user):
                return all((
                    user == ctx.author,
                    reaction.message.channel == ctx.channel,
                    str(reaction.emoji in "👍👎🤷🔼🔽"),
                ))

            progression = (
                int(round(aki.progression) / 2),
                int(round(85 - aki.progression) / 2),
            )
            e.title = (
                "**" + ":" * progression[0] + "**" + ":" * progression[1]
                if aki.progression != 0
                else ":" * 43
            )
            e.description = str(args[0])
            await msg.edit(embed=e)

            reaction, user = await ctx.bot.wait_for("reaction_add", check=check)
            if perms.manage_messages:
                await reaction.remove(user)
            return {"👍": "0", "👎": "1", "🤷": "2", "🔼": "3", "🔽": "4"}[
                str(reaction.emoji)
            ]

        while aki.progression <= 85:
            a = await uinput(q)
            if a == "b":
                try:
                    q = await aki.back()
                except CantGoBackAnyFurther:
                    pass
            else:
                q = await aki.answer(a)
        await aki.win()

        e.title = ""
        e.description = f"I guess {aki.name}, was I correct?"
        e.set_image(url=aki.picture)
        await msg.edit(embed=e)

    # @akinator_main_cmd.error
    async def akinator_error_handler(self, ctx, error):
        ctx.error_handled = True
        return

        if isinstance(error, commands.CommandInvokeError):
            await ctx.send("An error occoured while running this command")
        else:
            return
        ctx.error_handled = True

    @commands.command()
    @commands.cooldown(1, 6, commands.BucketType.user)
    @commands.bot_has_permissions(add_reactions=True)
    async def trivia(self, ctx: commands.Context, difficulty="random"):
        """Gives you some random trivia.\n
        Harder trivia is worth more coins and easier is worth less
        To specify a difficulty of the trivia you want, enter either
        `easy`, `medium`, or `hard` in to the command paramenters
        and you will recieve that level difficulty trivia.
        """
        await ctx.trigger_typing()
        params = dict(amount=1, type="multiple")
        if difficulty.lower() in ["easy", "medium", "hard"]:
            params["difficulty"] = difficulty.lower()
        async with self.sess.get("https://opentdb.com/api.php", params=params) as r:
            question = (await r.json())["results"][0]

        embed = Embed(
            colour=Colour.blue(),
            description=f"**{unescape(question['question'])}**\n*You have 15 seconds to answer*\n",
        )

        answers = question["incorrect_answers"] + [question["correct_answer"]]
        reactions = ["🇦", "🇧", "🇨", "🇩"]
        shuffle(answers)
        correct_answer_index = answers.index(question["correct_answer"])
        correct_emoji = reactions[correct_answer_index]
        worth = dict(easy=2, medium=5, hard=7)[question["difficulty"]] + randint(-3, 3)

        for emoji, ans in zip(reactions, answers):
            embed.description += f"\n{emoji} {unescape(ans)}"
        embed.add_field(name="Worth", value=f"`{worth} coins`")
        embed.add_field(name="Difficulty", value=f"`{question['difficulty']}`")
        embed.add_field(name="Category", value=f"`{question['category']}`")
        embed.set_author(name=f"{ctx.author}'s trivia question", icon_url=ctx.author.avatar_url)
        message = await ctx.send(embed=embed)
        for i in reactions:
            await message.add_reaction(i)

        try:
            chk = lambda reaction, user: user == ctx.author and str(reaction.emoji) in reactions
            reaction, user = await self.bot.wait_for("reaction_add", check=chk, timeout=15)
        except AsyncTimeoutError:
            await ctx.react(message, "⏱")
            return await ctx.send("⏱ wtf you didn't answer in time???")

        if str(reaction.emoji) == correct_emoji:
            await ctx.react(message, "🎉")
            await ctx.send(f"🎉 Correct, big brain! You earned yourself `{worth}` coins!")
            await self.db.add_user_money(ctx.author.id, worth)
        else:
            await ctx.react(message, "😕")
            await ctx.send(f"😕 Wow such small brain. The correct answer was {correct_emoji} `{unescape(question['correct_answer'])}`")

    @commands.command(aliases=["zalgo"])
    async def glitch(self, ctx, *, data: str):
        """Generate Zalgo text"""
        zalgo = "".join((c+"".join((choice(GLITCH_ALL) for i in range(20))) for c in data))
        txt = f"Generated `{len(zalgo)}` characters of zalgo\n\n{zalgo}"
        if len(txt) <= 2000:
            return await ctx.send(txt)
        file=File(BytesIO(zalgo.encode("utf-8")), filename="zalgo.txt")
        await ctx.send(f"I generated `{len(zalgo)}` characters of zalgo, here it is ⬇", file=file)
    
    @commands.command(name="10s")
    @commands.bot_has_permissions(add_reactions=True)
    @commands.cooldown(5, 60, commands.BucketType.user)
    async def ten_secs(self, ctx):
        """React to the message as close to 10 seconds as you can to win coins!"""
        emoji = str(choice(ctx.guild.emojis+(self.bot.emoji.minecraft,)))
        embed = Embed(description=f"React to this message with {emoji} after exactly 10 seconds", colour=Colour.blue())
        embed.set_author(icon_url=ctx.author.avatar_url, name=f"{ctx.author}'s 10s game")
        msg = await ctx.send(embed=embed)
        start = perf_counter()
        await msg.add_reaction(emoji)

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == str(emoji)
        
        try: reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=20)
        except AsyncTimeoutError:
            embed.description = "Timed out after 20 seconds 😕"
            return await msg.edit(embed=embed)
        
        end = perf_counter()-start
        diff = abs(10-end)
        coins = {0:4, 1:2, 2:1}.get(round(diff), 0)
        endstr = f"{end:.1f}" if len(str(round(end))) == 2 else f"{end:.2f}"
        embed.description = "\n".join(i.strip() for i in f"""```md
            \u200b      Results
            ====================
            < time   = "{endstr}s" >
            < off by = "{diff:.2f}s" >
            < coins  = "{coins} net" >
        ```""".splitlines())
        await msg.edit(embed=embed)
        await self.db.add_user_money(ctx.author.id, coins)
    
    @commands.command(enabled=False)
    async def reddit(self, ctx):
        """Get a random post off r/minecraft"""
        await ctx.trigger_typing()
        embed = Embed(colour=Colour.blue())
        async with self.sess.get(f"https://reddit.com/r/minecraft/top.json?limit={REDDIT_POST_LIMIT}") as resp:
            data = await resp.json()
            post = choice(data["data"]["children"])["data"]
        footer = f"👍 {post['ups']} | 💬 {post['num_comments']}"
        url = Embed.Empty
        file = None
        await ctx.send(f"https://reddit.com{post['permalink']}")

        if post["all_awardings"]:
            award = post["all_awardings"][-1:]
            footer = f"{award['name']} x{award['count']}" +f" | {footer}"
            url = award["icon_url"]

        # TODO: Implement if the video size is too big
        if post["post_hint"] == "video:hosted":
            url = post["media"]["reddit_video"]["fallback_url"]
            async with self.sess.get(url) as resp:
                file=File(BytesIO(await resp.read()), filename="video.mp4")

        #embed.set_image(url=post["url"])
        embed.set_footer(text=footer, icon_url=url)
        embed.description = f"{self.bot.emoji.minecraft} [`{post['author']}`](https://reddit.com/u/{post['author']}) - [{post['title']}](https://reddit.com{post['permalink']})"
        await ctx.send(embed=embed, file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Fun(bot))
