# TODO: Still need to re-format this file
from datetime import datetime as dt
from re import sub
from time import ctime, time

from discord import Colour, Embed
from discord.ext import commands
from humanize import naturaltime
from cogs.assets.custom import CustomCog

MINECRAFT_STATUS_EMOJI = dict(
    green="\N{WHITE HEAVY CHECK MARK}",
    yellow="\N{WARNING SIGN}",
    red="\N{NO ENTRY}",
)

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
        start = time()
        await ctx.trigger_typing()
        e = Embed(title=server, colour=Colour.blue())
        msg = await ctx.send(embed=Embed(
            title="Ping in progress..",
            description="This could take a few seconds",
            colour=Colour.blue(),
        ))

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
            return await msg.edit(embed=e)

        fields = {
            "Ping :ping_pong:": str(round(response["latency"], 2)) + "ms",
            "Version :desktop:": response["version"]["name"],
            "Player count :busts_in_silhouette:": f"{players['online']}/{players['max']}"
        }
        if players["sample"]:
            fields["Players :video_game:"] = f"`{'`, `'.join([p['name'] for p in players['sample']])}`"

        for field in fields:
            e.add_field(name=field, value=fields[field])
        e.timestamp = dt.utcnow()
        e.description = sub("§[a-zA-z0-9]", "", response["description"])
        e.set_footer(text=f"Server pinged in {round((time()- start)*1000)}ms", icon_url=self.bot.user.avatar_url)
        e.set_thumbnail(url=f"https://api.minetools.eu/favicon/{server}")
        await msg.edit(embed=e)

    @commands.command(aliases=["user"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def mcuser(self, ctx, name_or_UUID):
        """Find a minecraft user by username or UUID"""
        start = time()
        await ctx.trigger_typing()
        emojis = self.bot.emoji
        e = Embed(colour=Colour.blue())
        msg = await ctx.send(embed=Embed(
            title="Ping in progress..",
            description="This could take a few seconds",
            colour=Colour.blue(),
        ))

        try:
            async with self.sess.get(f"https://api.mojang.com/users/profiles/minecraft/{name_or_UUID}") as resp:
                userinfo = await resp.json()
            async with self.sess.get(f"https://api.mojang.com/user/profiles/{userinfo['id']}/names") as resp:
                usernamehistory = await resp.json()
        except Exception:
            return await msg.edit(embed=Embed(
                colour=Colour.red(),
                description=f"Could not find user by `UUID` or `nick` as **`{name_or_UUID}`**",
            ))

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
        await msg.edit(embed=e)

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
            e.description += f"{MINECRAFT_STATUS_EMOJI[status]} **{server}**\n"
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
        # TODO: Fix this one up
        start = time()
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())
        msg = await ctx.send(embed=Embed(
            title="Gathering stats",
            description="This could take a few seconds",
            colour=Colour.blue(),
        ))

        async with self.sess.get(
            f"https://api.hypixel.net/player?name={user}&key={self.bot.env['HYPIXEL_KEY']}"
        ) as resp:
            query = await resp.json()

        if query["success"] != True or query["player"] == None:
            e.colour = Colour.red()
            e.description = "Player stats could not be retrieved \N{SHRUG}"
            e.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)
            return await msg.edit(embed=e)

        if not query["player"].get("lastLogin"):
            e.colour =  Colour.orange()
            e.description = f"User `{user}` has never logged into `mc.hypixel.net` \N{SHRUG}"
            return await msg.edit(embed=e)

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
        await msg.edit(embed=e)

    @commands.command(aliases=["thehive", "hiveuser"])
    @commands.cooldown(2, 12, commands.BucketType.user)
    async def hive(self, ctx, user):
        """Fetch stats about a Hive user"""
        start = time()
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())
        msg = await ctx.send(embed=Embed(
            title="Gathering stats",
            description="This could take a few seconds",
            colour=Colour.blue()
        ))

        async with self.sess.get(f"http://api.hivemc.com/v1/player/{user}") as resp:
            if resp.status == 404:
                e.colour = Colour.red()
                e.description = "Player stats could not be retrieved \N{SHRUG}"
                e.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)
                return await msg.edit(embed=e)
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

        e.add_field(
            name="Login Details 📅",
            value=f"""
            First login: `{ctime(query["firstLogin"])}`
            (`{naturaltime(dt.fromtimestamp(query["firstLogin"]))}`)
            Last login: `{ctime(query["lastLogin"])}`
            (`{naturaltime(dt.fromtimestamp(query["lastLogin"]))}`)
        """,
        )
        e.set_author(
            name=f"The Hive stats for {query['username']}",
            icon_url="https://api.minetools.eu/favicon/play.hivemc.com",
        )
        e.set_footer(
            text=f"Information gathered in {round((time()- start)*1000)}ms",
            icon_url=self.bot.user.avatar_url,
        )
        await msg.edit(embed=e)

    @commands.command(aliases=["thehivestats"])
    @commands.cooldown(2, 5, commands.BucketType.user)
    async def hivestats(self, ctx):
        """Fetch stats about the hive server"""
        start = time()
        await ctx.trigger_typing()
        e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())
        msg = await ctx.send(embed=Embed(
            title="Gathering stats",
            description="This could take a few seconds",
            colour=Colour.blue(),
        ))

        async with self.sess.get("http://api.hivemc.com/v1/server/playercount") as resp:
            playercount = (await resp.json())["count"]
        async with self.sess.get("http://api.hivemc.com/v1/server/uniquecount") as resp:
            uplayercount = (await resp.json())["count"]

        e.title = "The Hive stats \N{HONEYBEE}"
        e.description = f"**Current player count**: `{playercount}`\n**Unique player count**: `{uplayercount}`"
        e.set_thumbnail(url="https://api.minetools.eu/favicon/play.hivemc.com")
        e.set_footer(text=f"Information gathered in {round((time()- start)*1000)}ms", icon_url=self.bot.user.avatar_url)
        return await msg.edit(embed=e)


def setup(bot: commands.Bot):
    bot.add_cog(Minecraft(bot))
