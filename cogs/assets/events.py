from datetime import datetime as dt

from discord import AsyncWebhookAdapter, Embed, Guild, Member, Role, Webhook
from discord.ext import commands
from cogs.assets.custom import CustomCog


class Events(CustomCog):
    """
    Handles all extra events for the bot that
    I don't want clogging up the main file. I've
    got a whole bunch of events, some called multiple times:
        - Webhook logging of commands, guild updates
        - Minecraft role checks
        - Checking for blacklisted guilds
        - Deleting old user's data
        - Posting data to Google Analytics
    
    The cheat sheet for Google Analytics is as follows:
        v: version            t: type (of hit)
        aip: anonymise IP     tid: tracking ID
        an: application name  dp: document path
        dh: document host     uid: user ID
        cid: client ID        cs: campaign source
        cm: campaign medium   cd: screen name
        dt: document title    cc: campaign content
    """

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db
        self.sess = bot.session
        self.guild_webhook_url = bot.env["GUILD_WEBHOOK_URL"]
        self.commands_webhook_url = bot.env["COMMANDS_WEBHOOK_URL"]
        self.gurl = "https://www.google-analytics.com/collect"
        self.gparams = dict(
            v="1", t="pageview", aip="1",
            tid=self.bot.env["GOOGLE_TRACKING_ID"],
            an=str(bot.user), dh=bot.website_url,
        )

    # Webhook events
    @commands.Cog.listener(name="on_guild_join")
    async def guild_join_webhook(self, guild: Guild):
        """Notify me when the bot joins a guild"""
        self.bot.guildlogger.info(f"Joined a guild: {guild.name}")
        webhook = Webhook.from_url(self.guild_webhook_url, adapter=AsyncWebhookAdapter(self.sess))
        e = Embed(
            colour=0x6CE479,
            timestamp=dt.utcnow(),
            description=f"Joined **{guild.name}**",
        )

        e.set_thumbnail(url=guild.icon_url)
        e.add_field(name="Member count", value=guild.member_count)
        e.add_field(name="New total guilds", value=len(self.bot.guilds))
        e.set_author(name="Guild Join", icon_url="https://bit.ly/32iG9BC")
        e.set_footer(text=f"Guild owner: {guild.owner}", icon_url=guild.owner.avatar_url)

        await webhook.send(
            embed=e,
            username=self.bot.user.name,
            avatar_url=self.bot.user.avatar_url,
        )

    @commands.Cog.listener(name="on_guild_remove")
    async def guild_leave_webhook(self, guild: Guild):
        """Notify me when the bot leaves a guild"""
        self.bot.guildlogger.info(f"Left a guild: {guild.name}")
        webhook = Webhook.from_url(self.guild_webhook_url, adapter=AsyncWebhookAdapter(self.sess))
        e = Embed(
            colour=0xE84C3D, timestamp=dt.utcnow(),
            description=f"Left **{guild.name}**"
        )

        e.set_thumbnail(url=guild.icon_url)
        e.add_field(name="Member count", value=guild.member_count)
        e.add_field(name="New total guilds", value=len(self.bot.guilds))
        e.set_author(name="Guild Leave", icon_url="https://bit.ly/2NQSABA")
        e.set_footer(text=f"Guild owner: {guild.owner}", icon_url=guild.owner.avatar_url)

        await webhook.send(
            embed=e, username=self.bot.user.name, avatar_url=self.bot.user.avatar_url
        )

    @commands.Cog.listener(name="on_command")
    async def command_run_webhook(self, ctx: commands.Context):
        # TODO: Needs to be reformatted?
        # TODO: This still fails in a try/except loop
        try: self.bot.cmdlogger.info(f"{ctx.author}: {ctx.message.content}")
        except: pass # Sometimes there's a whole lotta shit in the message that the bot can't decode

        webhook = Webhook.from_url(self.commands_webhook_url, adapter=AsyncWebhookAdapter(self.sess))
        e = Embed(
            colour=0xFFC000,
            timestamp=dt.utcnow(),
            description=f"```{ctx.message.clean_content}```",
        )

        if ctx.guild:
            e.set_thumbnail(url=ctx.guild.icon_url)
            e.add_field(name="Guild", value=ctx.guild.name)

        e.add_field(name="Channel", value=f"{'#' if ctx.guild else ''}{ctx.channel}")
        e.set_author(name="Command run", icon_url="https://bit.ly/2p75wYc")
        e.set_footer(text=f"{ctx.author} • {ctx.author.id}", icon_url=ctx.author.avatar_url)

        await webhook.send(
            embed=e, username=self.bot.user.name, avatar_url=self.bot.user.avatar_url
        )

    # Minecraft role events
    @commands.Cog.listener(name="on_member_update")
    async def minecraft_role(self, before: Member, after: Member):
        """Gives the `Minecraft` role to a user in my server if
        they start playing it\n
        Takes the role away if they stop playing it
        """
        guild = before.guild
        if not guild or before.bot:
            return
        if str(guild.id) not in self.db.guild_minecraft_roles.keys():
            return

        role = guild.get_role(int(self.db.guild_minecraft_roles[str(guild.id)]))
        b = [a.name for a in before.activities]
        a = [a.name for a in after.activities]

        if "Minecraft" in a and "Minecraft" not in b:
            try:
                await after.add_roles(role, reason="Started playing Minecraft")
                self.logger.debug(f"Adding minecraft role to {before} in {before.guild}")
            except: pass  # Missing permissions
        if "Minecraft" in b and "Minecraft" not in a:
            try:
                await after.remove_roles(role, reason="Stopped playing Minecraft")
                self.logger.debug(f"Removing minecraft role from {before} in {before.guild}")
            except: pass  # Missing permissions

    @commands.Cog.listener(name="on_guild_role_delete")
    async def check_minecraft_role_deleted(self, role: Role):
        # TODO: Maybe make a logger for `events`? (`guild` can fall under it)
        if str(role.id) in self.db.guild_minecraft_roles.values():
            await self.db.set_minecraft_role(role.guild.id, None)
            self.logger.debug(f"Deleted the minecraft role for {role.guild.id} ({role.id})")

    # Thanos snap excess data
    @commands.Cog.listener(name="on_guild_remove")
    async def thanos_snap_guild(self, guild: Guild):
        if not self.bot.delete_data_on_remove:
            return # I decided to keep the data
        self.logger.debug(f"Deleting guild data for {guild}")
        await self.db.delete_guild(guild.id)
    
    @commands.Cog.listener(name="on_member_remove")
    async def thanos_snap_user(self, member: Member):
        if not self.bot.delete_data_on_remove: return
        user = self.bot.get_user(member.id)
        if user or member.bot:
            return # Not removed from the bot's scope/no data to delete
        self.logger.debug(f"Deleting user data for {member}")
        await self.db.delete_user(member.id)


    # Blacklist event
    @commands.Cog.listener(name="on_guild_join")
    async def check_blacklist_guilds(self, guild: Guild):
        if not await self.db.is_guild_blacklisted(guild.id):
            return

        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.send_messages:
                chnl = channel
                break
        else: # No channels where bot can send messages
            return await guild.leave()

        aidzman = await self.bot.fetch_user(self.bot.owner_id)
        await chnl.send(
            f"Hello residents of **{guild.name}** \N{WAVING HAND SIGN} " \
            "It looks like you've been blacklisted from using this bot \N{CONFUSED FACE}\n" \
            "If you think this is a mistake, please contact `{aidzman}` to undo this ban\n" \
            "I'll just leave now \N{DOOR}"
        )
        await guild.leave()

    # Google Analytics
    @commands.Cog.listener(name="on_command")
    async def analytics_on_command(self, ctx):
        params = self.gparams.copy()
        params.update({
            "dp": f"/commands/{ctx.command.name}",
            "cid": f"{ctx.author.id}",
            "cs": f"{ctx.guild.id}" if ctx.guild else "PRIVATE_MESSAGE",
            "dt": ctx.command.name,
        })
        async with self.sess.get(self.gurl, params=params) as r:
            pass

    @commands.Cog.listener(name="on_guild_join")
    async def analytics_guild_join(self, guild: Guild):
        params = self.gparams.copy()
        params.update({
            "dp": "/events/GUILD_ADD",
            "cid": f"{guild.id}",
            "cs": f"{guild.id}",
            "dt": "GUILD_ADD",
        })
        async with self.sess.get(self.gurl, params=params) as r:
            pass

    @commands.Cog.listener(name="on_guild_remove")
    async def on_guild_remove(self, guild: Guild):
        params = self.gparams.copy()
        params.update({
            "dp": "/events/GUILD_REMOVE",
            "cid": f"{guild.id}",
            "cs": f"{guild.id}",
            "dt": "GUILD_REMOVE",
        })
        async with self.sess.get(self.gurl, params=params) as r:
            pass


class DiscordBotListPosters(CustomCog):
    """The cog that facilitates the posting of server
    counts and member counts to the various bot lists
    that I hope Moopity Moop will soon be a part of!"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.sess = bot.session
    
    async def update_stats(self):
        """Actually updates the stats on all the DBL websites"""
        self.logger.info("Updating bot stats on DBL websites..")

        # await self.discordBotWorldAPI()
        # await self.discordBotsGgAPI()
        # await self.botListSpaceAPI()

    # Add listeners
    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild):
        await self.on_guild_update()
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await self.on_guild_update()


def setup(bot: commands.Bot):
    bot.add_cog(Events(bot))
    #bot.add_cog(DiscordBotListPosters(bot))
