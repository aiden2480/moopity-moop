from datetime import datetime as dt

from discord import Colour, Embed
from discord import __version__ as dpy_version
from discord.ext import commands
from humanize import naturaltime
from cogs.assets.paginator import HelpPaginator


class General(commands.Cog):
    """General commands for the bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sess = bot.session

    @commands.command(name= "help")
    @commands.cooldown(1, 3.0)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, read_message_history=True, add_reactions=True)
    async def _help(self, ctx, *, command: str = None):
        """Stop it, get some help"""
        if command is None:
            p = await HelpPaginator.from_bot(ctx)
        else:
            entity = self.bot.get_cog(command) or self.bot.get_command(command)

            if entity is None:
                clean = command.replace("@", '@\u200b')
                return await ctx.send(f'Command or category "{clean}" not found.')
            elif isinstance(entity, commands.Command):
                p = await HelpPaginator.from_command(ctx, entity)
            else:
                p = await HelpPaginator.from_cog(ctx, entity)
        await p.paginate()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def ping(self, ctx):
        """Pong!"""
        await ctx.send(embed=Embed(
            colour=Colour.blue(),
            description=f":ping_pong: Pong! `{round(self.bot.latency*1000, 2)}ms` :ping_pong:",
        ))

    @commands.command(aliases=["about", "botinfo", "stats"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(3, 8, commands.BucketType.user)
    async def info(self, ctx):
        """Info and stats about the bot"""
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), description=self.bot.description)
        aidzman = self.bot.get_user(self.bot.owner_id)
        global_commands = []
        infoo = ""

        for cog in [c[1] for c in self.bot.cogs.items()]:
            for cmd in cog.get_commands():
                if all((cmd.enabled, not cmd.hidden, not any(["is_owner" in str(i) for i in cmd.checks]))):
                    global_commands.append(cmd)

        async with self.sess.get("https://api.github.com/repos/aiden2480/moopity-moop/commits") as resp:
            lastcommits = (await resp.json())[:3]

        for commit in lastcommits:
            msg = commit["commit"]["message"].split("\n")[0]
            d = commit["commit"]["committer"]["date"]
            date = naturaltime(dt.strptime(d, "%Y-%m-%dT%H:%M:%SZ"))
            i = f"[`{commit['sha'][:7]}`]({commit['html_url']}) {msg} ({date})"
            infoo += f"\n{i}"

        fields = {
            "Developer \N{PERSONAL COMPUTER}": f"{aidzman}\n{aidzman.id}",
            "Commands \N{SHORTCAKE}": len(global_commands),
            "Ping \N{TABLE TENNIS PADDLE AND BALL}": f"{round(self.bot.latency * 1000, 2)}ms",
            "Guild count \N{SHIELD}": len(self.bot.guilds),
            "User count \N{BUSTS IN SILHOUETTE}": len(self.bot.users),
            "Library \N{BOOKS}": f"Discord.py {dpy_version}",
        }

        e.add_field(name="Last updates", value=infoo, inline=False)
        for field in fields:
            e.add_field(name=field, value=fields[field])
        e.add_field(name="Uptime \N{ROBOT FACE}", value=self.bot.get_uptime(), inline=False)
        e.set_author(name=self.bot.user, icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def invite(self, ctx):
        """Get the invite link for the bot"""
        e = Embed(colour=Colour.blue())

        e.add_field(
            name="Bot 🤖",
            value=f"""
            [**Regular invite**]({self.bot.invite_url()})
            [Select Permissions]({self.bot.invite_url(-1)})
            [No permissions]({self.bot.invite_url(0)})
        """,
        )
        e.add_field(
            name="Other links 👥",
            value=f"""
            [Discord invite]({self.bot.guild_invite_url})
            [Bot website]({self.bot.website_url})
        """,
        )
        e.set_author(
            name=f"Invite links for {self.bot.user}", icon_url=self.bot.user.avatar_url
        )

        await ctx.send(embed=e)

    @commands.command()
    async def uptime(self, ctx):
        """Shows how long the bot has been online"""
        await ctx.send(embed=Embed(
            colour=Colour.blue(),
            description=f"I have been online for `{self.bot.get_uptime()}` \N{ROBOT FACE}",
        ))

    @commands.command(name="hello", aliases=[""], enabled=False)
    async def _hello(self, ctx):
        # TODO: Make this invoke without a command
        print("prefix", ctx.prefix)
        print("mention", ctx.guild.me.mention)

        if not ctx.guild:
            return print("in dm!")
        if ctx.prefix.split() != ctx.guild.me.mention.split():
            return print("prefixes don't match")

        print("checks passed!")
        prfx = await self.bot.db.get_guild_prefix(ctx.guild.id) or self.bot.default_prefix
        await ctx.send(
            f"Hello **{ctx.author}** \N{WAVING HAND SIGN} "
            f"My prefix in this server is `{prfx}`"
        )

    @commands.command(enabled=False)
    async def h(self, ctx, name):
        cmd = self.bot.get_command(name)
        if not cmd:
            return await ctx.send("Not a command")
        ch = list()

        checks = set(cmd.checks)
        for chk in checks:
            name = str(chk).split(" ")[1].split(".")[0]
            ch.append(name.replace("_", " "))
        await ctx.send(", ".join(ch) or "No checks \N{SHRUG}")
    
    # TODO: fix leaderboard command, the bot shouldn't have money and the person isn't in the guild any more
    @commands.command(enabled=False)
    async def c(self, ctx, name):
        cmd = self.bot.get_command(name)
        if not cmd:
            return await ctx.send("Not a command")
        await ctx.send(cmd._buckets._cooldown or "No cooldown on that command")

def setup(bot: commands.Bot):
    bot.remove_command("help")
    bot.add_cog(General(bot))
