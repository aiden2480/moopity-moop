import json_store_client as jsonstore
from asyncio import get_event_loop
from os import getenv

from discord import Message
from discord.ext import commands
jsonstore.DEFAULT_TIMEOUT_SECONDS = 15

class Database(object):
    LEADERBOARD_EMOJI_KEY = {1: "👑", 2: "🔱", 3: "🏆"}
    LEADERBOARD_DEFAULT_EMOJI = "🎗"
    LEADERBOARD_URL_KEY = {1:"98fe9cdec2bf8ded782a7bf1e302b664", 2:"7d7c9561cc5ab5259ff8023b8ef86c99", 3:"0a00e865c445d42dfb9f64bedfab8cf8"}
    LEADERBOARD_DEFAULT_URL = "d702f2335a85d421e708bc9466571fa8"

    def __init__(self, url: str = getenv("DATABASE_URL")):
        self.client = jsonstore.AsyncClient(url)
        self.guild_minecraft_roles = dict()
        self.guild_server_ips = dict()
        get_event_loop().run_until_complete(self.update_cache())

    # Upkeep stuff
    async def update_cache(self):
        """Updates the internal cache with the
        data that is stored in the remote host
        This should prevent API abuse and lag"""
        self.cache = await self.client.get("") or dict()
        self.guild_minecraft_roles = {
            g: self.cache["guilds"][g]["role"]
            for g in self.cache["guilds"]
            if self.cache["guilds"][g].get("role")
        } if self.cache.get("guilds") else dict()
        self.guild_server_ips = {
            g: self.cache["guilds"][g]["minecraft"]
            for g in self.cache["guilds"]
            if self.cache["guilds"][g].get("minecraft")
        } if self.cache.get("guilds") else dict()

    # Testing these two
    async def get(self, key: str, default=None):
        lol = [i for i in key.split("/") if i]
        d = self.cache.get(lol[0])
        use_default = default == None

        for sub in lol:
            if sub != lol[0]:
                if d:
                    d = d.get(sub)
        return (d or default) if use_default else d

    async def save(self, key: str, data=None):
        if bool(data):
            await self.client.save(key, data)
        else:
            await self.client.delete(key)
        await self.update_cache()

    async def double_thanos(self, data="none"):
        """Double Thanos snaps all the data in the database.\n
        Technically this would only remove three quarters of the
        data but shut up boomer what would you know\n
        
        :param:`data` must be either `all`, `guild`, or `user`, representing
        what data to delete, otherwise it'll delete none lmao"""
        if data == "all":
            await self.client.delete("")
        if data in ["guild", "guilds"]:
            await self.client.delete("guilds")
        if data in ["user", "users"]:
            await self.client.delete("users")
        await self.update_cache()

    async def delete_guild(self, guildid: int):
        await self.client.delete(f"guilds/{guildid}")
        await self.update_cache()

    async def delete_user(self, userid: int):
        await self.client.delete(f"users/{userid}")
        await self.update_cache()

    # Blacklisting
    async def blacklist_guild(self, guildid: int, reason=""):
        r = reason or "No reason provided"
        await self.client.save(f"blacklist/guilds/{guildid}", r)
        await self.update_cache()

    async def unblacklist_guild(self, guildid: int):
        await self.client.delete(f"blacklist/guilds/{guildid}")
        await self.update_cache()

    async def is_guild_blacklisted(self, guildid: int):
        blist = self.cache.get("blacklist")
        if blist:
            guilds = blist.get("guilds")
            if guilds:
                if str(guildid) in guilds.keys():
                    return True
        return False

    # Guild prefixes
    async def set_guild_prefix(self, guildid: int, prefix: str):
        if bool(prefix):
            await self.client.save(f"guilds/{guildid}/prefix", prefix)
        else:
            await self.client.delete(f"guilds/{guildid}/prefix")
        await self.update_cache()

    async def get_guild_prefix(self, guildid: int):
        guilds = self.cache.get("guilds")
        if guilds:
            guild = guilds.get(str(guildid))
            if guild:
                return guild.get("prefix", None)
        return None
        # return await self.client.get(f"guilds/{guildid}/prefix")

    # Guild server IPs
    async def set_minecraft_server(self, guildid: int, serverip: str):
        if bool(serverip):
            await self.client.save(f"guilds/{guildid}/minecraft", serverip)
        else:
            await self.client.delete(f"guilds/{guildid}/minecraft")
        await self.update_cache()

    async def get_minecraft_server(self, guildid: int):
        guilds = self.cache.get("guilds")
        if guilds:
            guild = guilds.get(str(guildid))
            if guild:
                return guild.get("minecraft", None)
        return None
        # return await self.client.get(f"guilds/{guildid}/minecraft")

    # Guild minecraft role
    async def set_minecraft_role(self, guildid: int, roleid: int):
        if bool(roleid):
            await self.client.save(f"guilds/{guildid}/role", str(roleid))
        else:
            await self.client.delete(f"guilds/{guildid}/role")
        await self.update_cache()

    async def get_minecraft_role(self, guildid: int):
        guilds = self.cache.get("guilds")
        if guilds:
            guild = guilds.get(str(guildid))
            if guild:
                return int(guild.get("role", 0))
        return 0

    # Currency
    async def set_user_money(self, userid: int, amount: int):
        if bool(amount):
            await self.client.save(f"users/{userid}/money", amount)
        else:
            await self.client.delete(f"users/{userid}/money")
        await self.update_cache()

    async def get_user_money(self, userid: int, *, human_readable=True):
        """`human_readable` specefies if the bot should add in commas every
        three characters, which creates an `str` object instead of an `int`"""
        usrs = self.cache.get("users")
        d = 0
        if usrs:
            usr = usrs.get(str(userid))
            if usr:
                d = usr.get("money", 0)
        return f"{d:,}" if human_readable else d

    async def add_user_money(self, userid: int, amount: int):
        usermoney = await self.get_user_money(userid, human_readable=False)
        await self.set_user_money(userid, usermoney + amount)
        await self.update_cache()

    async def get_leaderboard(self, guild=None, maxusers=10):
        """
            Gets the users from the database with the most amount of money
            Guild param must be a Discord Guild object, if specified.
            If :param:guild is specified, only users from that guild will be returned.
            If :param:maxusers is specified, the return value will be a max of that
        """
        users = [int(u) for u in self.cache.get("users") if u]
        unsorted = {u:await self.get(f"users/{u}/money", 0) for u in users}
        filteredmax = sorted(unsorted, key=lambda i:-unsorted[i])
        
        # Check if we need to filter max users
        if maxusers: filteredmax = sorted(unsorted, key=lambda i:-unsorted[i])[:maxusers]
        srted = {u:unsorted[u] for u in filteredmax}
        
        # Returns all users on leaderboard
        if not guild: return srted

        # Only show users from that guild
        users_in_guild = [mbr.id for mbr in guild.members if not mbr.bot]
        return {id_:money for id_,money in srted.items() if id_ in users_in_guild}


async def get_prefix(bot: commands.Bot, msg: Message):
    """Get the prefix from the bot database"""
    prefixes = [bot.default_prefix]

    if msg.guild:
        if bot.is_ready():
            prfx = await bot.db.get_guild_prefix(msg.guild.id)
            prefixes = [prfx] if prfx != None else prefixes
    else:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)
