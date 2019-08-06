from aiohttp import ClientSession

from discord import Embed, Colour, __version__ as dpy_version
from discord.ext.commands import Cog, Bot, BucketType, Command
from discord.ext.commands import command, cooldown, bot_has_permissions, has_permissions
from cogs.assets.paginator import HelpPaginator, CannotPaginate

class General(Cog):
    """General commands about the bot"""
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @command(name= "help")
    @cooldown(1, 3)
    @bot_has_permissions(embed_links= True)
    async def _help(self, ctx, *, command: str = None):
        """Stop it, get some help 🤚"""

        try:
            if command is None:
                p = await HelpPaginator.from_bot(ctx)
            else:
                entity = self.bot.get_cog(command) or self.bot.get_command(command)

                if entity is None:
                    clean = command.replace('@', '@\u200b')
                    return await ctx.send(f'Command or category `{clean}` not found.')
                elif isinstance(entity, Command):
                    p = await HelpPaginator.from_command(ctx, entity)
                else:
                    p = await HelpPaginator.from_cog(ctx, entity)
        except Exception as e:
            if isinstance(e, CannotPaginate):
                await ctx.send(e)
            else:
                raise e
        else:
            await p.paginate()

    @command()
    @bot_has_permissions(embed_links= True)
    async def ping(self, ctx):
        """Pong!"""
        await ctx.send(embed= Embed(
            colour= Colour.blue(),
            description= f":ping_pong: Pong! `{round(self.bot.latency*1000, 2)}ms` :ping_pong:"
        ))

    @command(aliases= ["about", "botinfo", "stats"])
    @bot_has_permissions(embed_links= True)
    @cooldown(3, 8, BucketType.user)
    async def info(self, ctx):
        """Info and stats about the bot"""
        e = Embed(colour= Colour.blue(), description= self.bot.description)
        aidzman = self.bot.get_user(self.bot.owner_id)
        global_commands = []
        
        for cog in [c[1] for c in self.bot.cogs.items()]:
            for cmd in cog.get_commands():
                if all((cmd.enabled, not cmd.hidden, not any(["is_owner" in str(i) for i in cmd.checks]))):
                    global_commands.append(cmd)

        fields = {
            "Developer 💻": f"{aidzman}\n{aidzman.id}",
            "Commands 🍰": len(global_commands),
            "Ping 🏓": str(round(self.bot.latency*1000, 2)) +"ms",
            
            "Guild count 🛡": len(self.bot.guilds),
            "User count 👥": len(self.bot.users),
            "Library 📚": f"Discord.py {dpy_version}",
            
            #"Coroutines 📋": f"{len([t for t in Task.all_tasks() if not t.done()])} running, {len(Task.all_tasks())} total",
            "Uptime 🤖": self.bot.get_uptime(),
        }

        for field in fields:
            e.add_field(name= field, value= fields[field])
        e.set_author(name= self.bot.user, icon_url= self.bot.user.avatar_url)
        await ctx.send(embed= e)

    @command()
    @bot_has_permissions(embed_links= True)
    async def invite(self, ctx):
        """Get the invite link for the bot"""
        e = Embed(colour= Colour.blue())
        
        e.add_field(name= "Bot 🤖", value= f"""
            [**Regular invite**]({self.bot.invite_url()})
            [Select Permissions]({self.bot.invite_url(-1)})
            [No permissions]({self.bot.invite_url(0)})
        """)
        e.add_field(name= "Other links 👥", value= f"""
            [Discord invite]({self.bot.guild_invite_url})
            [Bot website]({self.bot.website_url})
        """)
        e.set_author(name= f"Invite links for {self.bot.user}", icon_url= self.bot.user.avatar_url)
        
        await ctx.send(embed= e)

    @command()
    async def uptime(self, ctx):
        await ctx.send(embed= Embed(
            colour= Colour.blue(),
            description= f"I have been online for `{self.bot.get_uptime()}` 🤖"
        ))


def setup(bot: Bot):
    bot.remove_command("help")
    bot.add_cog(General(bot))
