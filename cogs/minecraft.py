from datetime import datetime as dt
from re import sub
from time import ctime, time

from discord import Colour, Embed
from discord.ext import commands
from humanize import naturaltime
from cogs.assets.custom import CustomCog, MinecraftUser


class Minecraft(CustomCog):
    """Commands for Minecraft"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.sess = bot.session

    @commands.command(aliases=["lookup", "pingserver"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def server(self, ctx, server:str):
        """Find a server to get its status and other information\n
        Other information includes:
         - Latency
         - Server software
         - Player count
         - Players online (if possible)
        """
        await ctx.trigger_typing()
        e = Embed(title=server, colour=Colour.blue(), timestamp=ctx.message.created_at)

        async with self.sess.get(f"https://api.minetools.eu/ping/{server}") as resp:
            try:
                response = await resp.json()
                error = response.get("error")
                players = response["players"]
            except Exception:
                error = "[ERROR] Invalid IP"

        if error:
            e.colour = Colour.red()
            e.title = "Error pinging server"
            e.description = error
            return await ctx.send(embed=e)

        fields = {
            "Ping :ping_pong:": str(round(response["latency"], 2)) + "ms",
            "Version :desktop:": response["version"]["name"],
            "Player count :busts_in_silhouette:": f"{players['online']}/{players['max']}"
        }
        if players["sample"]:
            fields["Players :video_game:"] = f"`{'`, `'.join([p['name'] for p in players['sample']])}`"

        for field in fields:
            e.add_field(name=field, value=fields[field])
        e.description = sub("§[a-zA-z0-9]", "", response["description"])
        e.set_footer(text=f"Server pinged in {round((time()-ctx.message.created_at.timestamp())*1000)}ms", icon_url=self.bot.user.avatar_url)
        e.set_thumbnail(url=f"https://api.minetools.eu/favicon/{server}")
        await ctx.send(embed=e)

    @commands.command(aliases=["user", "profile"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def mcuser(self, ctx, name_or_UUID):
        """Find a minecraft user by username or UUID"""
        start = time()
        await ctx.trigger_typing()
        emojis = self.bot.emoji
        e = Embed(colour=Colour.blue())

        async with self.sess.get(f"https://api.mojang.com/users/profiles/minecraft/{name_or_UUID}") as resp:
            if resp.status != 200:
                e.colour = Colour.red()
                e.description=f"Could not find user by `UUID` or `nick` as **`{name_or_UUID}`**"
                return await ctx.send(embed=e)
            userinfo = await resp.json()
        async with self.sess.get(f"https://api.mojang.com/user/profiles/{userinfo['id']}/names") as resp:
            usernamehistory = await resp.json()

        e.add_field(name=f"Name {emojis.minecraft}", value=userinfo["name"])
        e.add_field(name=f"UUID {emojis.goldenapple}", value=userinfo["id"])
        e.add_field(
            name=f"Username History ({len(usernamehistory)}) {emojis.pig}",
            value=", ".join(f"`{u['name']}`" for u in usernamehistory),
            inline=False
        )
        e.add_field(
            name=f"Textures {emojis.craftingtable}",
            value=f"[Open skin](https://minotar.net/skin/{name_or_UUID})",
        )

        e.set_thumbnail(url=f"https://minotar.net/body/{name_or_UUID}")
        e.set_author(
            name=f"{userinfo['name']}'s Minecraft profile",
            icon_url=f"https://minotar.net/avatar/{name_or_UUID}",
        )
        e.set_footer(
            text=f"Information gathered in {round((time()- start)*1000)}ms",
            icon_url=self.bot.user.avatar_url,
        )
        e.timestamp = dt.utcnow()
        await ctx.send(embed=e)

    @commands.command(name="status", aliases=["mcserverstatus"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def status_command(self, ctx):
        """Finds the status of the minecraft servers"""
        start = time()
        await ctx.trigger_typing()
        async with self.sess.get("https://status.mojang.com/check") as resp:
            sts = {list(chk.keys())[0]:list(chk.values())[0] for chk in await resp.json()}

        e = Embed(
            description="",
            colour=Colour.blue(),
            title=f"{self.bot.emoji.minecraft} Minecraft server status",
        )
        
        for server, status in sts.items():
            e.description += f"{dict(green='✅', yellow='⚠', red='⛔')[status]} **{server}**\n"
        e.set_footer(text=f"Stats retrieved in {round((time()-start)*1000)}ms")
        await ctx.send(embed=e)

    @commands.command(aliases=["hyuser", "hypixeluser"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def hypixel(self, ctx, user):
        """Find the Hypixel stats of a user\n
        You can find:
         - Login Dates
         - Player achievements
         - Stats for the various gamemodes
         - Rank and money
        """
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())

        async with self.sess.get(
            f"https://api.hypixel.net/player?name={user}&key={self.bot.env['HYPIXEL_KEY']}"
        ) as resp:
            start = time()
            query = await resp.json()

        if query["success"] != True or query["player"] == None:
            e.colour = Colour.red()
            e.description = "Player stats could not be retrieved 🤷"
            e.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)
            return await ctx.send(embed=e)

        if not query["player"].get("lastLogin"):
            e.colour =  Colour.orange()
            e.description = f"User `{user}` has never logged into `mc.hypixel.net` 🤷"
            return await ctx.send(embed=e)

        stats = query["player"]
        last_session = self.bot.time_between(
            dt.fromtimestamp(stats.get("lastLogin", 0) / 1000),
            dt.fromtimestamp(stats.get("lastLogout", 0) / 1000),
        )
        achv = {
            "general": [
                a for a in stats["achievementsOneTime"] if a.startswith("general")
            ],
            "bedwars": [
                a for a in stats["achievementsOneTime"] if a.startswith("bedwars")
            ],
            "buildbattle": [
                a for a in stats["achievementsOneTime"] if a.startswith("buildbattle")
            ],
            "skywars": [
                a for a in stats["achievementsOneTime"] if a.startswith("skywars")
            ],
        }

        e.add_field(
            name=f"Achievements ({len(stats['achievementsOneTime'])}) 🛡",
            value=f"""
            General: `{len(achv["general"])}`
            Bedwars: `{len(achv["bedwars"])}`
            Buildbattle: `{len(achv["buildbattle"])}`
            Skywars: `{len(achv["skywars"])}`
        """,
        )
        e.add_field(
            name="Login Details 📅",
            value=f"""
            First login: `{ctime(stats["firstLogin"]/1000)}`
            Last login: `{ctime(stats["lastLogin"]/1000)}`
            Last session: `{last_session}`
        """,
        )
        e.add_field(
            name="Economy 🌟",
            value=f"""
            Experience: `{stats["networkExp"]}`
        """,
        )

        e.set_footer(
            text=f"Information gathered in {round((time()- start)*1000)}ms",
            icon_url=self.bot.user.avatar_url,
        )
        e.set_author(
            name=f"Hypixel stats for {stats['playername']}",
            icon_url="https://api.minetools.eu/favicon/mc.hypixel.net",
        )
        await ctx.send(embed=e)

    @commands.command(aliases=["thehive", "hiveuser"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def hive(self, ctx, user):
        """Fetch stats about a Hive user"""
        start = time()
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())

        async with self.sess.get(f"http://api.hivemc.com/v1/player/{user}") as resp:
            if resp.status == 404:
                e.colour = Colour.red()
                e.description = "Player stats could not be retrieved 🤷"
                e.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)
                return await ctx.send(embed=e)
            query = await resp.json()

        if query["rankName"] == "Regular Hive Member":
            query["rankName"] = "Regular"
        if query["achievements"] is None:
            query["achievements"] = []

        e.description=f"{query['status']['description']} **{query['status']['game']}**"
        e.add_field(
            name="Stats 🏆",
            value=f"""
            Rank: `{query["rankName"]}`
            Tokens: `{query["tokens"]}`💰
            Crates: `{query["crates"]}`📦
            Medals: `{query["medals"]}`🥇
            Achievements: `{len(query["achievements"])}`
        """,
        )

        e.add_field(name="Login Details 📅", value=f"""
            First login: `{ctime(query["firstLogin"])}`
            (`{naturaltime(dt.fromtimestamp(query["firstLogin"]))}`)
            Last login: `{ctime(query["lastLogin"])}`
            (`{naturaltime(dt.fromtimestamp(query["lastLogin"]))}`)
        """)
        e.set_author(
            name=f"The Hive stats for {query['username']}",
            icon_url="https://api.minetools.eu/favicon/play.hivemc.com",
        )
        e.set_footer(
            text=f"Information gathered in {round((time()- start)*1000)}ms",
            icon_url=self.bot.user.avatar_url,
        )
        await ctx.send(embed=e)

    @commands.command(aliases=["thehivestats"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def hivestats(self, ctx):
        """Fetch stats about the hive server"""
        start = time()
        await ctx.trigger_typing()
        e = Embed(title="The Hive stats 🐝", colour=Colour.blue(), timestamp=dt.utcnow())

        async with self.sess.get("http://api.hivemc.com/v1/server/playercount") as resp:
            playercount = (await resp.json())["count"]
        async with self.sess.get("http://api.hivemc.com/v1/server/uniquecount") as resp:
            uplayercount = (await resp.json())["count"]

        e.description = f"**Current player count**: `{int(playercount):,}`\n**Unique player count**: `{int(uplayercount):,}`"
        e.set_thumbnail(url="https://api.minetools.eu/favicon/play.hivemc.com")
        e.set_footer(text=f"Information gathered in {round((time()- start)*1000)}ms", icon_url=self.bot.user.avatar_url)
        return await ctx.send(embed=e)

    @commands.cooldown(8, 45, commands.BucketType.user)
    @commands.command(aliases=["usernamecheck"])
    async def namecheck(self, ctx, name: MinecraftUser):
        """Check if a Minecraft username is taken, or if you can claim it"""
        if len(name) > 16:
            return await ctx.send("A Minecraft username is a max of 16 characters...")
        
        await ctx.trigger_typing()
        embed = Embed(colour=Colour.blue())
        embed.set_author(name=f"Username checker")
        async with self.sess.get(f"https://api.mojang.com/users/profiles/minecraft/{name}") as resp:
            if resp.status not in [200, 204]:
                embed.description = f"An error occoured while processing the request.\nI got an unexpected status `{resp.status}` 😕"
            elif resp.status == 204:
                embed.description = f"The username `{name}` is free!\n[Click here](https://account.mojang.com/me) to claim the account! {self.bot.emoji.minecraft}"
                embed.set_thumbnail(url="https://minotar.net/body/MHF_Steve")
            elif resp.status == 200:
                udata = await resp.json()
                embed.description = f"The username `{udata['name']}` is taken! 😕"
                embed.add_field(name=f"{udata['name']}'s UUID", value=udata["id"])
                embed.set_thumbnail(url=f"https://minotar.net/body/{name}")
                embed.set_author(name=embed.author.name, icon_url=f"https://minotar.net/avatar/{name}")
        await ctx.send(embed=embed)
    
    @commands.command()
    async def sales(self, ctx):
        """Shows the sales statistics for Minecraft"""
        await ctx.trigger_typing()
        embed = Embed(colour=Colour.blue(), title=f"{self.bot.emoji.minecraft} Minecraft Sale Statistics")
        payload = {"metricKeys": ["item_sold_minecraft", "prepaid_card_redeemed_minecraft", "item_sold_cobalt", "item_sold_scrolls"]}
        async with self.sess.post("https://api.mojang.com/orders/statistics", json=payload) as resp:
            data = await resp.json()

        embed.add_field(name="Total sales", value=f"{data['total']:,}")
        embed.add_field(name="Last 24 hours", value=f"{data['last24h']:,}")
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Minecraft(bot))
