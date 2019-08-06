from akinator import CantGoBackAnyFurther
from akinator.async_aki import Akinator
from datetime import datetime as dt

from discord import Embed, Colour
from discord.ext.commands import Cog, BucketType, CommandOnCooldown, CommandInvokeError
from discord.ext.commands import command, guild_only, group, cooldown
from cogs.assets.custombot import CustomBot

class Fun(Cog):
    """Fun commands such as games and special features
    Some have absolutely nothing to do with Minecraft! yay!"""
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.busdriverthanks = 0

    @group(name= "akinator", aliases= ["aki"])
    #@cooldown(2, 60, BucketType.user)
    async def akinator_cmd(self, ctx):
        """A classic game of Akinator!"""
        if ctx.invoked_subcommand:
            return
        await ctx.send(f"Use `{ctx.prefix}{ctx.command} help` for help about the akinator commands or `{ctx.prefix}{ctx.command} start` to start a new game")

    @akinator_cmd.command()
    async def help(self, ctx):
        "Pls send help! I have no" \
        "idea how this game works!"
        e = Embed(
            colour= Colour.blue(),
            timestamp= dt.utcnow(),
            title= "Akinator help command",
            description= f"Use the command `{ctx.prefix}akinator` to start a new game of Akinator")
        
        e.add_field(name= "What is Akinator?", value= "Akinator is an online character guessing game where I try to guess what character you are thinking of and ask a series of questions to help me!")
        e.add_field(name= "Progress bar", value= "The progress bar at the top of the interactive game represents how close I think I am to guessing your character")
        e.add_field(name= "Reactions", value= "The 5 different reactions represent the different options:\n>>> **👍 Yes 👎 No 🤷 I don't know**\n>>>** 🔼 Probably 🔽 Probably not**")
        
        e.set_thumbnail(url= "https://bit.ly/30aHPen")
        e.set_footer(text= "Akinator help command", icon_url= self.bot.user.avatar_url)
        await ctx.send(embed= e)

    @akinator_cmd.command(name= "start", aliases= ["new"])
    async def akinator_main_cmd(self, ctx):
        if ctx.guild is not None:
            perms = ctx.channel.permissions_for(ctx.guild.me)
        else:
            perms = ctx.channel.permissions_for(ctx.bot.user)

        e = Embed(
            timestamp= dt.utcnow(),
            colour= Colour.blue(),
            description= "Setting up your Akinator game!\n\n" \
                "Please give me a moment while I get things ready for you.\nThis could take a few seconds.. ⌛")
        e.set_author(name= f"Akinator with {ctx.author}", icon_url= "https://bit.ly/30aHPen")
        msg= await ctx.send(embed= e)

        aki = Akinator()
        q = await aki.start_game()
        for emoji in "👍👎🤷🔼🔽":
            await msg.add_reaction(emoji)

        async def uinput(*args):
            """Short for user input, get's a user's message from discord"""
            
            def check(reaction, user):
                return all((
                    user == ctx.author, reaction.message.channel == ctx.channel,
                    str(reaction.emoji in "👍👎🤷🔼🔽")#, reaction.message.id == ctx.message.id
                ))

            progression = (int(round(aki.progression)/2), int(round(85-aki.progression)/2))
            e.title= "**"+ ":"*progression[0] + "**" + ":"*progression[1] if aki.progression != 0 else ":"*43
            e.description = str(args[0])
            await msg.edit(embed= e)

            reaction, user = await ctx.bot.wait_for("reaction_add", check= check)#, timeout= 1)
            if perms.manage_messages:
                await reaction.remove(user)
            return {"👍": "0", "👎": "1", "🤷": "2", "🔼": "3", "🔽": "4"}[str(reaction.emoji)]

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
        e.set_image(url= aki.picture)
        await msg.edit(embed= e)

    #@akinator_main_cmd.error
    async def akinator_error_handler(self, ctx, error):
        print(error)

        ctx.error_handled= True
        return
        print(str(error))
        print("TimeoutError" in str(error))
        if isinstance(error, (CommandInvokeError)):
            await ctx.send("An error occoured while running this command")
        else:
            return
        ctx.error_handled= True


    @group(aliases= ["mcrole", "role"])
    @guild_only()
    async def autorole(self, ctx):
        """Automatically add a role to any user that stats playing `Minecraft`\n
        You could make the role a different colour, hoisted, mentionable, etc
        to determine who in your server is playing `Minecraft`.\n
        **Please note**: This command requires that the bots *top* role must
        be above the designated `Minecraft` role"""
        if ctx.invoked_subcommand:
            return
        e = Embed(
            colour= Colour.blue(),
            timestamp= dt.utcnow(),
            description= self.autorole.__doc__,
        )
        
        e.set_author(name= f"{self.bot.user.name} AutoRole command", icon_url= self.bot.user.avatar_url)
        e.add_field(name= "Set `Minecraft` role", value= f"Requires `Manage Server` permissions\n```{ctx.prefix}{ctx.command} set <role>```")
        e.add_field(name= "Query `Minecraft` role", value= f"Returns the pre-set `Minecraft` role\n```{ctx.prefix}{ctx.command} query```")
            
        await ctx.send(embed= e)


    @command()
    @cooldown(3, 60, BucketType.user)
    async def thank(self, ctx):
        """Thank the bus driver"""
        self.busdriverthanks += 1
        
        s = ""
        if self.busdriverthanks != 1:
            s = "s"
        
        await ctx.send(f"The bus driver has been thanked {self.busdriverthanks} time{s}! 🚐")
    
    @thank.error
    async def thank_error_handler(self, ctx, error):
        if isinstance(error, CommandOnCooldown):
            ctx.error_handled = True
            await ctx.send(f"You can't thank the bus driver yet!\nYou need to wait another `{round(error.retry_after)}` seconds! 🚍")


def setup(bot: CustomBot):
    bot.add_cog(Fun(bot))
