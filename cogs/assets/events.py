"""Handles all extra events for the bot that
I don't want clogging up the main file"""
from aiohttp import ClientSession
from datetime import datetime as dt

from discord import Webhook, AsyncWebhookAdapter, Guild, Member, Embed
from discord.ext.commands import Bot, Cog
from discord.ext.commands import command, is_owner


class Events(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.guild_webhook_url = bot.env("GUILD_WEBHOOK_URL")
        self.commands_webhook_url = bot.env("COMMANDS_WEBHOOK_URL")
    
    # Events
    @Cog.listener()
    async def on_guild_join(self, guild):
        """Notify me when the bot joins a guild"""
        print(f"Joined a new guild: {guild.name}")
        
        async with ClientSession(loop= self.bot.loop) as http:
            webhook = Webhook.from_url(self.guild_webhook_url, adapter= AsyncWebhookAdapter(http))
            e = Embed(colour= 0x6ce479, timestamp= dt.utcnow(), description= f"Joined **{guild.name}**")
            
            e.set_thumbnail(url= guild.icon_url)
            e.add_field(name= "Member count", value= guild.member_count)
            e.add_field(name= "New total guilds", value= len(self.bot.guilds))
            e.set_author(name= "Guild Join", icon_url= "https://bit.ly/32iG9BC")
            e.set_footer(text= f"Guild owner: {guild.owner}", icon_url= guild.owner.avatar_url)

            await webhook.send(embed= e, username= self.bot.user.name, avatar_url= self.bot.user.avatar_url)

    @Cog.listener()
    async def on_guild_remove(self, guild):
        """Notify me when the bot leaves a guild"""
        print(f"Left a guild: {guild.name}")
        
        async with ClientSession(loop= self.bot.loop) as http:
            webhook = Webhook.from_url(self.guild_webhook_url, adapter= AsyncWebhookAdapter(http))
            e = Embed(colour= 0xe84c3d, timestamp= dt.utcnow(), description= f"Left **{guild.name}**")
            
            e.set_thumbnail(url= guild.icon_url)
            e.add_field(name= "Member count", value= guild.member_count)
            e.add_field(name= "New total guilds", value= len(self.bot.guilds))
            e.set_author(name= "Guild Leave", icon_url= "https://bit.ly/2NQSABA")
            e.set_footer(text= f"Guild owner: {guild.owner}", icon_url= guild.owner.avatar_url)

            await webhook.send(embed= e, username= self.bot.user.name, avatar_url= self.bot.user.avatar_url)

    @Cog.listener()
    async def on_command(self, ctx):
        print(f"{ctx.author}: {ctx.message.content}")

        async with ClientSession(loop= self.bot.loop) as http:
            webhook = Webhook.from_url(self.commands_webhook_url, adapter= AsyncWebhookAdapter(http))
            e = Embed(colour= 0xffc000, timestamp= dt.utcnow(), description= f"```{ctx.message.clean_content}```")
            hashtag = ""
            
            if ctx.guild:
                hashtag = "#"
                e.set_thumbnail(url= ctx.guild.icon_url)
                e.add_field(name= "Guild", value= ctx.guild.name)
            
            e.add_field(name= "Channel", value= f"{hashtag}{ctx.channel}")
            e.set_author(name= "Command run", icon_url= "https://yokoent.com/images/exclamation-mark-png-9.png")
            e.set_footer(text= f"{ctx.author} • {ctx.author.id}", icon_url= ctx.author.avatar_url)

            await webhook.send(embed= e, username= self.bot.user.name, avatar_url= self.bot.user.avatar_url)

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        """Gives the `Minecraft` role to a user in my server if
        they start playing it\n
        Takes the role away if they stop playing it
        """
        if before.guild.id == 553071847483375626:
            Aactivities = [a.name for a in after.activities]
            Bactivities = [a.name for a in before.activities]
            mcRole = after.guild.get_role(590_054_428_200_140_810)
            
            if "Minecraft" in Aactivities and "Minecraft" not in Bactivities:
                print(f"{after} just started playing minecraft")
                await after.add_roles(mcRole, reason= "Started playing Minecraft")
            if "Minecraft" in Bactivities and "Minecraft" not in Aactivities:
                print(f"{after} just stopped playing Minecraft")
                await after.remove_roles(mcRole, reason= "Stopped playing Minecraft")


def setup(bot: Bot):
    bot.add_cog(Events(bot))
