import ast
from asyncio import TimeoutError as AsyncioTimeoutError
from datetime import datetime as dt
from inspect import getsource
from time import time

import discord
from discord.ext import commands

"""
Don't star import from modules `commands` and `discord`
because they are directly referenced
"""
class Developer(commands.Cog):
    """Developer commands to manage the bot"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases= ["rld"])
    @commands.is_owner()
    async def reload(self, ctx, *cogs):
        """Reload cogs on the bot\n
        If param `cogs` is empty, all cogs will be reloaded 👍"""
        await ctx.trigger_typing()
        e = discord.Embed(colour= discord.Colour.blue(), timestamp= dt.utcnow())
        e.set_footer(text= "Cogs in bold have already been reloaded", icon_url= self.bot.user.avatar_url)

        if cogs != tuple():
            # Cleanup
            cogs = tuple([f"cogs.{cog}" for cog in cogs])
        else:
            # Reload whole bot
            cogs = tuple(self.bot.extensions)
        
        e = discord.Embed(colour= discord.Colour.blue(), description= "Reloading cogs `"+"`, `".join(cogs)+"`")
        msg, start_time = await ctx.send(embed= e), time()
        scogs, fcogs = [], [] # list and list of tuple (cog, error)
        for cog in cogs:
            try:
                self.bot.reload_extension(cog)
            except Exception as err:
                fcogs.append((cog, err))
            else:
                scogs.append(cog)
        
        if scogs:
            e.add_field(name= "Successful cogs ✅", value= "`"+ "`, `".join(scogs) +"`")
        if fcogs:
            e.add_field(name= "Failed cogs ❌", value= "\n".join([f"`{i[0]}` **-** {str(i[1])}" for i in fcogs]), inline= False)
        
        e.set_author(name= "Cog reload complete", icon_url= self.bot.user.avatar_url)
        e.description= f"Finished reloading `{len(cogs)}` cogs in `{round((time()-start_time)*1000)}`ms ⚙"
        await msg.edit(embed= e)

    @commands.command()
    @commands.is_owner()
    async def source(self, ctx, command):
        """Get the source of any command"""
        cmd = self.bot.get_command(command)
        if cmd is None: return await ctx.send(embed= discord.Embed(
            color= discord.Colour.blue(), description= "Could not find that command ❎"))
        await ctx.send(f"**Here ya go**```py\n{getsource(cmd.callback)}```")

    @commands.command(hidden= True)
    async def logs(self, ctx):
        """Check the bot logs\n
        Congrats on finding this command lol now what are you going to do about it"""
        e = discord.Embed(title= "Bot logs", description= "React with a number to see the relative logs\n:one: - Discord logs\n:two: - Moopity Moop logs\n:three: - Website logs", colour= discord.Colour.blue())
        e.set_footer(text= self.bot.user, icon_url= self.bot.user.avatar_url)
        msg = await ctx.send(embed= e)
        check = lambda reaction, user: user == ctx.author and reaction.emoji in ["1⃣", "2⃣", "3⃣"]
        for emoji in ["1⃣", "2⃣", "3⃣"]:
            await msg.add_reaction(emoji)
        
        def file_lines(fileLocation):
            with open(f"cogs/assets/logs/{fileLocation}", encoding= "utf-8") as fp:
                return len(fp.readlines())

        try:
            reaction, user = await self.bot.wait_for("reaction_add", check= check, timeout= 30.0)
        except AsyncioTimeoutError: # Unsuccessful
            e.description = "Timed out. ⏱"
            await msg.edit(embed= e)
        else: # Successful
            e.title = ""
            await ctx.trigger_typing()

            if str(reaction) == "1⃣":
                e.description = f"Showing logs for `Discord` ({file_lines('discord.log')} lines)"
                await ctx.send(file= discord.File(fp= "cogs/assets/logs/discord.log"))
                await msg.edit(embed= e)
            if str(reaction) == "2⃣":
                e.description = f"Showing logs for `Moopity Moop` ({file_lines('moopitymoop.log')} lines)"
                await ctx.send(file= discord.File(fp= "cogs/assets/logs/moopitymoop.log"))
                await msg.edit(embed= e)
            if str(reaction) == "3⃣":
                e.description = f"Showing logs for `Website` ({file_lines('website.log')} lines)"
                await ctx.send(file= discord.File(fp= "cogs/assets/logs/website.log"))
                await msg.edit(embed= e)

    @commands.command(name= "eval")
    @commands.is_owner()
    async def eval_cmd(self, ctx, *, cmd):
        """Evaluates input.\n
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invokation context
        - `__import__`: the builtin `__import__` function
        """
        # Helper function
        def insert_returns(body):
            # insert return stmt if the last expression is a expression statement
            if isinstance(body[-1], ast.Expr):
                body[-1] = ast.Return(body[-1].value)
                ast.fix_missing_locations(body[-1])

            # for if statements, we insert returns into the body and the orelse
            if isinstance(body[-1], ast.If):
                insert_returns(body[-1].body)
                insert_returns(body[-1].orelse)

            # for with blocks, again we insert returns into the body
            if isinstance(body[-1], ast.With):
                insert_returns(body[-1].body)

        # Exec setup
        fn_name = "_eval_expr"
        cmd = cmd.strip("` ")
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"
        parsed = ast.parse(body)
        body = parsed.body[0].body
        insert_returns(body)

        # Environment variables
        env = {
            'ctx': ctx,
            'bot': ctx.bot,
            'discord': discord,
            'database': self.bot.database,
            'commands': commands,
            '__import__': __import__}
        exec(compile(parsed, filename= "<ast>", mode= "exec"), env)

        result = (await eval(f"{fn_name}()", env))
        await ctx.send(result)

    @commands.command()
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shutdown the bot, bye! 👋"""
        await ctx.send("Bye! 👋")
        await self.bot.logout()
        raise KeyboardInterrupt(f"Shutdown command run by {ctx.author}")
    
    @commands.is_owner()
    @commands.command(hidden= True)
    async def evalu(self, ctx, user: discord.Member, *, command: str):
        """Evaluate commands as another user
        (testing owner-only commands and the like)"""
        ctx.message.author = user
        ctx.message.content = f"{ctx.prefix}{command}"
        await self.bot.process_commands(ctx.message)


def setup(bot: commands.Bot):
    bot.add_cog(Developer(bot))