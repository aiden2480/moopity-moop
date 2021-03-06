from datetime import datetime as dt, timedelta as td
from time import perf_counter

from discord import Colour, Embed
from discord import __version__ as dpy_version
from discord.ext import commands
from humanize import naturaltime
from cogs.assets.paginator import HelpPaginator
from cogs.assets.custom import CustomCog, cooldown


class General(CustomCog):
    """General commands for the bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sess = bot.session
        self._original_help_command = bot.help_command
        bot.remove_command("help")

    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    @commands.command(name= "help")
    @cooldown(1, 3, 3, 3)
    @commands.bot_has_permissions(embed_links=True, read_message_history=True, add_reactions=True)
    async def _help(self, ctx, *, command: str = None):
        """Stop it, get some help"""
        if command is None:
            p = await HelpPaginator.from_bot(ctx)
            return await p.paginate()

        entity = self.bot.get_cog(command) or self.bot.get_command(command)
        if entity is None:
            clean = command.replace("@", "@\u200b")
            p = await HelpPaginator.from_bot(ctx)
            return await p.paginate(msg=f"Command or category `{clean}` not found")
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
            description=f":ping_pong: Pong! `{self.bot.latency*1000:.2f}ms` :ping_pong:",
        ))

    @commands.command(aliases=["about", "botinfo", "stats"])
    @commands.bot_has_permissions(embed_links=True)
    @cooldown(3, 8, 3, 3, commands.BucketType.user)
    async def info(self, ctx):
        """Info and stats about the bot"""
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), description=self.bot.description)
        global_commands = []

        for cog in [c[1] for c in self.bot.cogs.items()]:
            for cmd in cog.get_commands():
                if all((cmd.enabled, not cmd.hidden, not any(["is_owner" in str(i) for i in cmd.checks]))):
                    global_commands.append(cmd)

        async with self.sess.get("https://api.github.com/repos/aiden2480/moopity-moop/commits") as resp:
            lastcommits = (await resp.json())[:3]

        g = self.bot.get_guild(496081601755611137)
        c = g.get_channel(554544702624366603)
        history = await c.history(limit=20).flatten()
        msg = sorted(history, key=lambda m: m.content.startswith("🚀"), reverse=True)[0]
        infoo = f"{msg.content[3:].strip()}\n" if msg.content.startswith("🚀") else ""

        for commit in lastcommits:
            msg = commit["commit"]["message"].split("\n")[0]
            d = commit["commit"]["committer"]["date"]
            date = naturaltime(dt.strptime(d, "%Y-%m-%dT%H:%M:%SZ")+td(hours=11))
            i = f"[`{commit['sha'][:7]}`]({commit['html_url']}) {msg} ({date})"
            infoo += f"\n{i}"

        fields = {
            "Developer 💻": f"{self.bot.owner}\n{self.bot.owner.id}",
            "Version 🛠": f"Bot version `{self.bot.version}`\nDiscord.py `v{dpy_version}`",
            "Commands 🍰": len(global_commands),
            "Guild count 🛡": len(self.bot.guilds),
            "User count 👥": len(self.bot.users),
            "Ping 🏓": f"{round(self.bot.latency * 1000, 2)}ms",
        }

        e.add_field(name="Last updates 📰", value=infoo, inline=False)
        for field in fields:
            e.add_field(name=field, value=fields[field])
        e.add_field(name="Uptime 🤖", value=self.bot.uptime, inline=False)
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
        """)
        e.add_field(
            name="Other links 👥",
            value=f"""
            [Discord invite]({self.bot.guild_invite_url})
            [Bot website]({self.bot.website_url})
        """)
        e.set_author(name=f"Invite links for {self.bot.user}", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)
    
    @commands.command()
    async def vote(self, ctx):
        """Shows bot list voting pages for the bot"""
        embed = Embed(colour=Colour.blue(), description="", timestamp=ctx.message.created_at)
        embed.set_author(name=f"{self.bot.user}'s voting links", icon_url=self.bot.user.avatar_url)
        embed.set_footer(text=f"Each vote will gain you 40 ingots ({ctx.clean_prefix}bal)")
        
        embed.description += "<:logo:459634405183586304> [Divine Discord Bots](https://divinediscordbots.com/bot/567246604411863041/vote)"
        await ctx.send(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Shows how long the bot has been online"""
        await ctx.send(embed=Embed(
            colour=Colour.blue(),
            description=f"I have been online for `{self.bot.uptime}` 🤖",
        ))


def setup(bot: commands.Bot):
    bot.add_cog(General(bot))
