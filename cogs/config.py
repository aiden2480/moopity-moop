from discord import Embed, Colour
from discord.ext.commands import Cog, Bot, BucketType
from discord.ext.commands import (
    command, cooldown, guild_only,
    bot_has_permissions, group, has_permissions
)

class Config(Cog):
    """The custom settings for your server"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.cog_emoji = "⚙"
        self.database = bot.database

    @guild_only()
    @cooldown(2, 4, BucketType.guild)
    @bot_has_permissions(read_message_history= True)
    @group(aliases= ["serverconfig", "serverconf"])
    async def config(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.trigger_typing()
            emojis = self.bot.emoji
            e = self.bot.EmptyEmbed(title= f"Server Config settings {emojis.rainbowsheep}", description= "Only users with `Manage Server` permissions can change these settings", set_footer= False, set_timestamp= False)
            e.set_footer(text= f"Server settings for {ctx.guild}", icon_url= self.bot.user.avatar_url)

            with self.database() as db:
                minecraftServer = db.get_guild_minecraft_server(ctx.guild.id).fetchone()
                guildPrefix = db(f"SELECT * FROM GuildPrefixes WHERE guildID={ctx.guild.id}").fetchone()

                if minecraftServer:
                    minecraftServer = "`"+ minecraftServer[1] +"`"
                if guildPrefix:
                    guildPrefix = "`"+ guildPrefix[1] +"`"
                else:
                    guildPrefix = "Default (`m!` or `M!`)"
            e.add_field(name= f"Bot Prefix {emojis.craftingtable}", value= guildPrefix)
            e.add_field(name= f"Minecraft Server {emojis.goldenapple}", value= minecraftServer)
            
            await ctx.send(embed= e)

    @config.command(aliases= ["mcserver", "mcserverip"])
    @has_permissions(manage_guild= True)
    async def server(self, ctx, ip= None):
        """Sets the minecraft server IP for this guild\n
        You must have `Manage Guild` premissions to use this command."""
        if ip == None:
            with self.database() as db:
                db.set_guild_minecraft_server(ctx.guild.id, None)
            return await ctx.send(embed= self.bot.EmptyEmbed(description= "Success! Server IP has been cleared!"))
        
        ip= ip.replace(" ", "") # Remove spaces from ip
        if len(ip) > 30:
            return await ctx.send(embed= self.bot.EmptyEmbed(description= "IP must be a maximum of `30` characters"))
        
        with self.database() as db:
            db.set_guild_minecraft_server(ctx.guild.id, ip)
        await ctx.send(embed= Embed(description= f"Success! Server IP is now `{ip}` :thumbsup:", colour= Colour.blue()))

    @command(name= "prefix", aliases= ["serverprefix", "botprefix"], enabled= False)
    @has_permissions(manage_guild= True)
    async def _prefix(self, ctx, prefix= None):
        """Set the prefix for this guild. Must be a maximum of 5 characters\n
        If prefix param is not supplied, the prefix is returned to default.\n
        You must have `Manage Guild` permissions to use this command.
        """
        if prefix == None:
            with self.database() as db:
                db(f"DELETE FROM GuildPrefixes WHERE guildID={ctx.guild.id}")
            return await ctx.send(embed= self.bot.EmptyEmbed(description= "Prefix has been returned to default of `m!`"))
        if len(prefix) > 5:
            return await ctx.send(embed= self.bot.EmptyEmbed(description= "Prefix must be a maximum of `5` characters"))
        
        with self.database() as db:
            db.set_prefix(ctx.guild.id, prefix)
        await ctx.send(embed= Embed(description= f"Success! Prefix is now `{prefix}` :thumbsup:", colour= Colour.blue()))


def setup(bot: Bot):
    bot.add_cog(Config(bot))
