from aiohttp import ClientSession
from datetime import datetime as dt
from json import loads, JSONDecodeError
from re import sub
from time import time

from discord import Embed, Colour
from discord.ext.commands import Cog, BucketType
from discord.ext.commands import command, cooldown
from cogs.assets.custombot import CustomBot

class Minecraft(Cog):
    """Commands for Minecraft"""
    def __init__(self, bot: CustomBot):
        self.bot = bot
    
    @command(aliases= ["lookup", "server"])
    @cooldown(2, 12, BucketType.user)
    async def mcserver(self, ctx, server):
        """Find a server to get its status and other information\n
        Other information includes:
         - Latency
         - Server software
         - Player count
         - Players online (if possible)
        """
        start = time()
        await ctx.trigger_typing()
        e = Embed(title= server, colour= Colour.blue())
        msg = await ctx.send(embed= Embed(title= "Ping in progress..", description= "This could take a few seconds", colour= Colour.blue()))

        async with ClientSession(loop= self.bot.loop) as http:
            async with http.get(f"https://api.minetools.eu/ping/{server}") as resp:
                try:
                    response = loads(await resp.read())
                    error = response.get("error")
                except JSONDecodeError:
                    error = "[ERROR] Invalid IP"
                
        if error:
            e.colour, e.title, e.description= Colour.red(), "Error pinging server", error
        else:
            e.set_thumbnail(url= f"https://api.minetools.eu/favicon/{server}")
            fields = {
                "Ping :ping_pong:": str(round(response["latency"], 2))+"ms",
                "Version :desktop:": response["version"]["name"],
                "Player count :busts_in_silhouette:": str(response["players"]["online"]) +"/"+ str(response["players"]["max"])}
            if response["players"]["sample"]: # For big servers a sample range is not provided
                fields["Players :video_game:"] = "`"+ "`, `".join([p["name"] for p in response["players"]["sample"]]) +"`"
            
            for field in fields:
                e.add_field(name= field, value= fields[field])
            e.description, e.timestamp= sub("§[a-zA-z0-9]", "", response["description"]), dt.utcnow()
            e.set_footer(text= f"Server pinged in {round((time()- start)*1000)}ms", icon_url= self.bot.user.avatar_url)
        await msg.edit(embed= e)

    @command(aliases= ["user"])
    @cooldown(2, 12, BucketType.user)
    async def mcuser(self, ctx, name_or_UUID):
        """Find a minecraft user by username or UUID"""
        start = time()
        await ctx.trigger_typing()
        emojis = self.bot.emoji
        e = Embed(colour= Colour.blue())
        msg = await ctx.send(embed= Embed(title= "Ping in progress..", description= "This could take a few seconds", colour= Colour.blue()))

        async with ClientSession(loop= self.bot.loop) as http:
            try:
                async with http.get(f"https://api.mojang.com/users/profiles/minecraft/{name_or_UUID}") as resp:
                    userinfo = loads(await resp.read())
                async with http.get(f"https://api.mojang.com/user/profiles/{userinfo['id']}/names") as resp:
                    usernamehistory = loads(await resp.read())
            except JSONDecodeError:
                return await msg.edit(embed= Embed(colour= Colour.red(), description= f"Could not find user by `UUID` or `nick` as **`{name_or_UUID}`**"))
        
        e.add_field(name= f"Name {emojis.minecraft}", value= userinfo["name"])
        e.add_field(name= f"UUID {emojis.goldenapple}", value= userinfo["id"])
        e.add_field(name= f"Username History ({len(usernamehistory)}) {emojis.pig}", value= ", ".join(f"`{u['name']}`" for u in usernamehistory))
        e.add_field(name= f"Textures {emojis.craftingtable}", value= f"[Open skin](https://minotar.net/skin/{name_or_UUID})")

        e.set_thumbnail(url= f"https://minotar.net/body/{name_or_UUID}")
        e.set_author(name= f"{userinfo['name']}'s Minecraft profile", icon_url= f"https://minotar.net/avatar/{name_or_UUID}")
        e.set_footer(text= f"Information gathered in {round((time()- start)*1000)}ms", icon_url= self.bot.user.avatar_url)
        e.timestamp = dt.utcnow()
        await msg.edit(embed= e)

    @command(aliases= ["hyuser"])
    @cooldown(2, 12, BucketType.user)
    async def hypixel(self, ctx, user):
        """Find the Hypixel stats of a user\n
        You can find:
         - Login Dates
         - Player achievements
         - Stats for the various gamemodes
         - Rank and money
        """
        start = time()
        await ctx.trigger_typing()
        key = self.bot.env("HYPIXEL_KEY")
        e = Embed(colour= Colour.blue(), timestamp= dt.utcnow())#, description= "Click on a reaction below to find more detailed stats  (🛏 `Bedwars`, ⚔ `Buildbattle`)")
        msg = await ctx.send(embed= Embed(title= "Gathering stats", description= "This could take a few seconds", colour= Colour.blue()))

        async with ClientSession(loop= self.bot.loop) as http:
            print(f"https://api.hypixel.net/player?name={user}&key={key}")
            async with http.get(f"https://api.hypixel.net/player?name={user}&key={key}") as resp:
                query = loads(await resp.read())

        if query["success"] != True or query["player"] == None:
            e.set_footer(text= self.bot.user, icon_url= self.bot.user.avatar_url)
            e.colour, e.description = Colour.red(), "Player stats could not be retrieved 🤷"
            return await msg.edit(embed= e)

        stats = query["player"]
        last_session = self.bot.time_between(dt.fromtimestamp(int(stats.get("lastLogin", "Never"))/1000), dt.fromtimestamp(stats["lastLogout"]/1000))
        achv = {
            "general": [a for a in stats["achievementsOneTime"] if a.startswith("general")],
            "bedwars": [a for a in stats["achievementsOneTime"] if a.startswith("bedwars")],
            "buildbattle": [a for a in stats["achievementsOneTime"] if a.startswith("buildbattle")],
            "skywars": [a for a in stats["achievementsOneTime"] if a.startswith("skywars")],
        }

        e.add_field(name= f"Achievements ({len(stats['achievementsOneTime'])}) 🛡", value= f"""
            General: `{len(achv["general"])}`
            Bedwars: `{len(achv["bedwars"])}`
            Buildbattle: `{len(achv["buildbattle"])}`
            Skywars: `{len(achv["skywars"])}`
        """)
        e.add_field(name= "Login Details 📅", value= f"""
            First login: `{time.ctime(stats["firstLogin"]/1000)}`
            Last login: `{time.ctime(stats["lastLogin"]/1000)}`
            Last session: `{last_session}`
        """)
        e.add_field(name= "Economy 🌟", value= f"""
            Experience: `{stats["networkExp"]}`
        """)

        e.set_footer(text= f"Information gathered in {round((time()- start)*1000)}ms", icon_url= self.bot.user.avatar_url)
        e.set_author(name= f"Hypixel stats for {stats['playername']}", icon_url= "https://api.minetools.eu/favicon/mc.hypixel.net")
        await msg.edit(embed= e)

    @command(aliases= ["thehive"])
    @cooldown(2, 12, BucketType.user)
    async def hive(self, ctx, user= None):
        """Fetch stats about the hypixel server or a hypixel user\n
        If param `user` is specified, user stats will be retrieved, if not,
        stats about the hypixel server will be retrieved"""
        
        # Setup
        start = time()
        await ctx.trigger_typing()
        e = Embed(colour= Colour.blue(), timestamp= dt.utcnow())
        msg = await ctx.send(embed= Embed(title= "Gathering stats", description= "This could take a few seconds", colour= Colour.blue()))

        # Server stats
        if user is None:
            async with ClientSession(loop= self.bot.loop) as http:
                async with http.get("http://api.hivemc.com/v1/server/playercount") as resp:
                    playercount = loads(await resp.read())["count"]
                async with http.get("http://api.hivemc.com/v1/server/uniquecount") as resp:
                    uplayercount = loads(await resp.read())["count"]
            
            e.title = "The Hive stats 🐝"
            e.description = f"**Current player count**: `{playercount}`\n**Unique player count**: `{uplayercount}`"
            e.set_thumbnail(url= "https://api.minetools.eu/favicon/play.hivemc.com")
            e.set_footer(text= f"Information gathered in {round((time()- start)*1000)}ms", icon_url= self.bot.user.avatar_url)
            return await msg.edit(embed= e)

        # Player stats
        async with ClientSession(loop= self.bot.loop) as http:
            async with http.get(f"http://api.hivemc.com/v1/player/{user}") as resp:
                if resp.status == 404:
                    e.set_footer(text= self.bot.user, icon_url= self.bot.user.avatar_url)
                    e.colour, e.description = Colour.red(), "Player stats could not be retrieved 🤷"
                    return await msg.edit(embed= e)
                # Else
                query = loads(await resp.read())

        if query["rankName"] == "Regular Hive Member":
            query["rankName"] = "Regular"
        if query["achievements"] is None:
            query["achievements"] = []
        
        e.description = f"{query['status']['description']} **{query['status']['game']}**"
        e.add_field(name= "Stats 🏆", value= f"""
            Rank: `{query["rankName"]}`
            Tokens: `{query["tokens"]}`💰
            Crates: `{query["crates"]}`📦
            Medals: `{query["medals"]}`🥇
            Achievements: `{len(query["achievements"])}`
        """)
        e.add_field(name= "Login Details 📅", value= f"""
            First login: `{time.ctime(query["firstLogin"])}`
            Last login: `{time.ctime(query["lastLogin"])}`
        """)
        e.set_author(name= f"The Hive stats for {query['username']}", icon_url= "https://api.minetools.eu/favicon/play.hivemc.com")
        e.set_footer(text= f"Information gathered in {round((time()- start)*1000)}ms", icon_url= self.bot.user.avatar_url)
        await msg.edit(embed= e)


def setup(bot):
    bot.add_cog(Minecraft(bot))
