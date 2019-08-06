from discord import Game, Embed, Colour
from discord.ext.commands import Bot, Cog, BucketType, CommandOnCooldown
from discord.ext.commands import command, cooldown

class Hidden(Cog, command_attrs= dict(hidden= True)):
    """Congrats you have found the hidden commands for the bot *shudders*"""
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(aliases= ["🍰"])
    async def cake(self, ctx):
        """Lets sit down and have some cake"""
        try:
            await ctx.message.add_reaction("🍰")
            #await ctx.send("🍰")
        except:
            pass # Don't really care if missing permissions

    @cooldown(1, 45, BucketType.user)
    @command()
    async def status(self, ctx, *, status):
        """Change my status, oh boy!"""
        await self.bot.change_presence(activity= Game(name= status))
        await ctx.send(f"Done! My status is now `Playing `**`{status}`**")
    
    @status.error
    async def status_error_handler(self, ctx, error):
        if isinstance(error, CommandOnCooldown):
            await ctx.send(embed= Embed(
                colour= Colour.blue(),
                title= "This command is on cooldown!",
                description= f"Please try again in {round(error.retry_after)} seconds\n\n||Did you really think I'd let you go crazy with **this** command???||"
            ))
            ctx.error_handled = True


def setup(bot: Bot):
    bot.add_cog(Hidden(bot))
