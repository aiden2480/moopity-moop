from datetime import datetime as dt
from inspect import getsourcefile, getsourcelines
from os.path import relpath
from time import time

from discord import Colour, Embed, User
from discord.ext import commands
from cogs.assets.custom import CustomCog


class Developer(CustomCog):
    """Developer commands to manage the bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def cog_before_invoke(self, ctx):
        """These are dev only commands"""
        if ctx.command.name == "source":
            return
        
        if ctx.author.id != ctx.bot.owner_id:
            raise commands.NotOwner()

    @commands.command(aliases=["rld"])
    async def reload(self, ctx, *cogs):
        """Reload cogs on the bot\n
        If param `cogs` is empty, all cogs will be reloaded 👍"""
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())
        e.set_footer(
            text="Cogs in bold have already been reloaded",
            icon_url=self.bot.user.avatar_url,
        )

        if cogs != tuple():
            # Cleanup
            cogs = tuple([f"cogs.{cog}" for cog in cogs])
        else:
            # Reload whole bot
            cogs = tuple(self.bot.extensions)

        e = Embed(
            colour=Colour.blue(),
            description="Reloading cogs `" + "`, `".join(cogs) + "`",
        )
        msg, start_time = await ctx.send(embed=e), time()
        scogs, fcogs = [], []  # list and list of tuple (cog, error)
        for cog in cogs:
            try:
                self.bot.reload_extension(cog)
            except Exception as err:
                fcogs.append((cog, err))
            else:
                scogs.append(cog)

        if scogs:
            e.add_field(name="Successful cogs ✅", value="`" + "`, `".join(scogs) + "`")
        if fcogs:
            e.add_field(
                name="Failed cogs ❌",
                value="\n".join([f"`{i[0]}` **-** {str(i[1])}" for i in fcogs]),
                inline=False,
            )

        e.set_author(name="Cog reload complete", icon_url=self.bot.user.avatar_url)
        e.description = f"Finished reloading `{len(cogs)}` cogs in `{round((time()-start_time)*1000)}`ms ⚙"
        await msg.edit(embed=e)

    @commands.command(aliases=["sauce"])
    async def source(self, ctx, *, command: str=None):
        """Displays my full source code or for a specific command."""
        source = "https://github.com/aiden2480/moopity-moop"

        if command in [None, "help"]:
            return await ctx.send(source)
        
        obj = self.bot.get_command(command)        
        if obj is None:
            return await ctx.send(f"Couldn't find that command 😕\n{source}")

        src = obj.callback.__code__
        module = obj.callback.__module__
        filename = src.co_filename

        if module.startswith("discord") or module.startswith("jishaku"):
            return await ctx.send(source)

        lines, firstlineno = getsourcelines(src)
        location = relpath(filename).replace("\\", "/")
        final_url = f"{source}/blob/master/{location}#L{firstlineno}-L{firstlineno+len(lines)-1}"
        await ctx.send(f"Command **{obj}** takes up `{len(lines)}` lines in file **{location}**\n{final_url}")
    
    @commands.command()
    async def reset(self, ctx, mbr: commands.Greedy[User]=None, *commands):
        """Reset cooldowns"""
        mbr = [ctx.author] or mbr
        con = ctx
        cmds = [self.bot.get_command(cmd) for cmd in commands if cmd] if commands else self.bot.commands
        for cmd in cmds:
            for m in mbr:
                con.author = m
                cmd.reset_cooldown(con)
        await ctx.send("Done")



def setup(bot: commands.Bot):
    bot.add_cog(Developer(bot))
