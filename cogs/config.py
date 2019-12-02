from typing import Union

from discord import Colour, Embed, Role
from discord.ext import commands
from cogs.assets.custom import CustomCog


class Config(CustomCog):
    """The custom settings for your server"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db

    @commands.command(name="config", aliases=["serverconfig", "serverconf"])
    @commands.cooldown(3, 5, commands.BucketType.user)
    @commands.guild_only()
    async def config_command(self, ctx):
        # TODO: You only need admin permissions to change the prefix lmao not view it
        """Get the config data for this server"""
        emojis = self.bot.emoji
        e = Embed(title=f"Server config settings for **{ctx.guild}** ⚙", colour=Colour.blue(), description="")

        prfx = await self.db.get_guild_prefix(ctx.guild.id)
        server = await self.db.get_minecraft_server(ctx.guild.id)
        roleid = await self.db.get_minecraft_role(ctx.guild.id)
        role = ctx.guild.get_role(roleid)

        p = ctx.clean_prefix
        e.description += f"`{p}prefix <prefix>` to change the bot prefix\n"
        e.description += f"`{p}role <role>` to set the role given to a user playing `Minecraft`\n"
        e.description += f"`{p}setserver <ip>` to set the IP for this server\n"
        e.description += f"\nTip: you can also change these settings on the [bot website]({self.bot.website_url}/guildsettings/{ctx.guild.id})\n"
        
        e.add_field(name=f"Bot Prefix {emojis.craftingtable}", value=f"`{prfx}`" if prfx else None)
        e.add_field(name=f"Minecraft Role 🔶", value=role.mention if role else None)
        e.add_field(name=f"Minecraft Server {emojis.goldenapple}", value=f"`{server}`" if server else server)
        e.set_footer(text="Only users with 'Manage Server' permissions can change these settings", icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=e)

    @commands.command(name="prefix", aliases=["serverprefix", "botprefix"])
    @commands.cooldown(3, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix_command(self, ctx, prefix=None):
        """Set the prefix for this guild. Must be a maximum of 15 characters\n
        If prefix option is set to `""`, the prefix is returned to default.
        You must have `Manage Guild` permissions to use this command.
        """
        embed = Embed(colour=Colour.blue(), timestamp=ctx.message.created_at, description="")
        embed.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)

        if prefix == None:
            prfx = await self.db.get_guild_prefix(ctx.guild.id) or self.bot.default_prefix

            embed.description = f'Hello **{ctx.author}** 👋 My prefix here is **`{prfx}`**\n\nUse `{ctx.clean_prefix}{ctx.command.name} <prefix>` to set the prefix or `{ctx.clean_prefix}{ctx.command.name} ""` to reset it the the default'
            return await ctx.send(embed=embed)

        if prefix in ["", self.bot.default_prefix]:
            embed.description = f"Prefix returned to the default (`{self.bot.default_prefix}`)"
            await ctx.send(embed=embed)
            return await self.db.set_guild_prefix(ctx.guild.id, None)

        if len(prefix) > 15:
            embed.description = "Prefix must be a maximum of `15` characters"
            return await ctx.send(embed=embed)

        embed.description = f"Success! Prefix is now `{prefix}` :thumbsup:"
        await ctx.send(embed=embed)
        await self.db.set_guild_prefix(ctx.guild.id, prefix)

    @commands.command(name="setserver", aliases=["mcserver", "mcserverip"])
    @commands.cooldown(3, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def mcserver_command(self, ctx, ip=None):
        """Set the server IP for this guild. Must be a maximum of 35 characters\n
        If ip option is set to `""`, the prefix is returned to default.
        You must have `Manage Guild` permissions to use this command.
        """
        embed = Embed(colour=Colour.blue(), timestamp=ctx.message.created_at)
        embed.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)

        if ip == None:
            i = await self.db.get_minecraft_server(ctx.guild.id) or None

            embed.description = f"The current server IP for **{ctx.guild}** is `{i}`"
            return await ctx.send(embed=embed)

        if ip in ["", "reset"]:
            embed.description = "Server IP has been cleared"
            await ctx.send(embed=embed)
            return await self.db.set_minecraft_server(ctx.guild.id, None)

        if len(ip) > 35:
            embed.description = "Server IP must be a maximum of `35` characters"
            return await ctx.send(embed=embed)

        embed.description = f"Success! Server IP is now `{ip}` :thumbsup:"
        await ctx.send(embed=embed)
        await self.db.set_minecraft_server(ctx.guild.id, ip)

    @commands.command(name="autorole", aliases=["minecraftrole", "mcrole", "role"])
    @commands.cooldown(3, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def autorole_command(self, ctx, role: Union[Role, str] = None):
        """Automatically add a role to any user that stats playing `Minecraft`\n
        To clear the preset role, use the paramater `""` or `reset`
        You could make the role a different colour, hoisted, mentionable, etc
        to determine who in your server is playing `Minecraft`.\n
        **Please note**: This command requires that the bots *top* role must
        be above the designated `Minecraft` role"""
        embed = Embed(colour=Colour.blue(), timestamp=ctx.message.created_at)
        embed.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)

        if role in ["", "reset"]:
            embed.description = "Minecraft role has been cleared"
            await ctx.send(embed=embed)
            return await self.db.set_minecraft_role(ctx.guild.id, None)

        if role == None:
            roleid = await self.db.get_minecraft_role(ctx.guild.id)
            role = ctx.guild.get_role(roleid)

            embed.description = f"The current Minecraft role for **{ctx.guild}** is "
            embed.description += role.mention if role else "`None`"
            return await ctx.send(embed=embed)

        if not isinstance(role, Role):
            # Needs to be `Role` object from now on
            embed.description = f"Role {role!r} not found 😕"
            return await ctx.send(embed=embed)

        if role > ctx.guild.me.top_role:
            embed.description = f"The role {role.mention} is higher than my top role. Please lower the role in the server settings hierarchy or raise mine 😎"
            return await ctx.send(embed=embed)

        if role.managed:
            embed.description = f"The role {role.mention} is a managed role, it's either a Twitch role or a bot's role. Please pick a different role"
            return await ctx.send(embed=embed)

        embed.description = f"Success! Minecraft role is now {role.mention} :thumbsup:"
        await ctx.send(embed=embed)
        await self.db.set_minecraft_role(ctx.guild.id, role.id)


def setup(bot: commands.Bot):
    bot.add_cog(Config(bot))
