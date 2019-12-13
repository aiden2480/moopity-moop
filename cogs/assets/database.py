from asyncio import get_event_loop
from os import getenv

from aiohttp import ClientSession
from discord import Message
from discord.ext import commands
from json import dumps


class Database(object):
    """
        Represents a database connection

        This stores the data in a read-only cache property (`cache`).
        Internal methods can also be used as shortcuts for updating data quickly
    """
    TIMEOUT = 5
    
    LEADERBOARD_EMOJI_KEY = {1: "👑", 2: "🔱", 3: "🏆"}
    LEADERBOARD_URL_KEY = {1:"98fe9cdec2bf8ded782a7bf1e302b664", 2:"7d7c9561cc5ab5259ff8023b8ef86c99", 3:"0a00e865c445d42dfb9f64bedfab8cf8"}
    
    LEADERBOARD_DEFAULT_EMOJI = "🎗"
    LEADERBOARD_DEFAULT_URL = "d702f2335a85d421e708bc9466571fa8"

    # Setup functions
    def __init__(self, url:str=getenv("DATABASE_URL"), *, timeout:int=TIMEOUT, sess:ClientSession=None):
        self.__url = url
        self.TIMEOUT = timeout

        self._cache = dict()
        self.guild_server_ips = dict()
        self.guild_minecraft_roles = dict()
        
        self.sess = sess if isinstance(sess, ClientSession) else get_event_loop().run_until_complete(self.__create_session())
    
    async def __create_session(self) -> ClientSession:
        return ClientSession(headers={
            "Accept": "application/json",
            "Content-type": "application/json",
        })
    
    # Properties
    @property
    def ready(self) -> bool:
        """Indicates if the internal cache is ready"""
        return self._cache is not dict()
    
    @property
    def cache(self) -> dict:
        return self._cache

    # Get/set functions
    async def update_cache(self) -> "cache":
        """
            Updates the internal cache with the data that is stored in the remote host.
            This should prevent API abuse and lag by requesting data all the time.
        """
        self._cache = await self.get("") or dict()
        self.guild_minecraft_roles = {
            g: self._cache["guilds"][g]["role"]
            for g in self._cache["guilds"]
            if self._cache["guilds"][g].get("role")
        } if self._cache.get("guilds") else dict()
        self.guild_server_ips = {
            g: self._cache["guilds"][g]["minecraft"]
            for g in self._cache["guilds"]
            if self._cache["guilds"][g].get("minecraft")
        } if self._cache.get("guilds") else dict()
        return self._cache

    async def get(self, key: str, default=None, *, data=None):
        """
            Get a value from the database cache, using a key in the format `one/two`, etc.
            If a `default` is supplied, that will be returned if a value could not be resolved.
            Do not supply the `data` paramater, this is used by the internal operations.
        """
        data = data or self._cache
        args = key.split("/")

        if args and data:
            element = args[0]
            if element:
                value = data.get(element)
                return value if len(args) == 1 else await self.get("/".join(args[1:]), default, data=value)
            else: return default # Invalid key, return default
        else: # No key/data supplied, get all
            async with self.sess.get(self.__url) as resp:
                return (await resp.json())["result"]

    async def save(self, key: str, data: any):
        url = f"{self.__url}/{key}"
        if bool(data):
            async with self.sess.post(url, json=data, timeout=self.TIMEOUT) as resp:
                resp.raise_for_status()
            return await self.update_cache()
        await self.delete(key)
    
    async def delete(self, key: str):
        url = f"{self.__url}/{key}"
        async with self.sess.delete(url, timeout=self.TIMEOUT) as resp:
            resp.raise_for_status()
        await self.update_cache()

    # Thanos snap data
    async def double_thanos(self, data="none"):
        """
            Double Thanos snaps all the data in the database.
        
            `data` must be either `all`, `guild`, or `user`,
            representing what data to delete, otherwise it'll delete none lmao
        """
        if data == "all":
            await self.delete("")
        if data in ["guild", "guilds"]:
            await self.delete("guilds")
        if data in ["user", "users"]:
            await self.delete("users")
        await self.update_cache()

    async def delete_guild(self, guildid: int):
        await self.delete(f"guilds/{guildid}")

    async def delete_user(self, userid: int):
        await self.delete(f"users/{userid}")

    # Blacklisting
    async def blacklist_guild(self, guildid: int, reason="No reason provided"):
        return await self.save(f"blacklist/guilds/{guildid}", reason)

    async def unblacklist_guild(self, guildid: int):
        return await self.delete(f"blacklist/guilds/{guildid}")

    async def is_guild_blacklisted(self, guildid: int):
        return bool(await self.get(f"blacklist/guilds/{guildid}"))

    # Guild prefixes
    async def set_guild_prefix(self, guildid: int, prefix: str):
        return await self.save(f"guilds/{guildid}/prefix", prefix)

    async def get_guild_prefix(self, guildid: int):
        return await self.get(f"guilds/{guildid}/prefix", None)

    # Guild server IPs
    async def set_minecraft_server(self, guildid: int, serverip: str):
        return await self.save(f"guilds/{guildid}/minecraft", serverip)

    async def get_minecraft_server(self, guildid: int):
        return await self.get(f"guilds/{guildid}/minecraft")

    # Guild minecraft role
    async def set_minecraft_role(self, guildid: int, roleid: int):
        return await self.save(f"guilds/{guildid}/role", str(roleid))

    async def get_minecraft_role(self, guildid: int):
        return await self.get(f"guilds/{guildid}/role")

    # Currency
    async def set_user_money(self, userid: int, amount: int):
        amount = amount if amount >= 0 else 0
        return await self.save(f"users/{userid}/money")

    async def get_user_money(self, userid: int, *, human_readable=True):
        """`human_readable` specefies if the bot should add in commas every
        three characters, which creates an `str` object instead of an `int`"""
        d = await self.get(f"users/{userid}/money")
        return f"{d:,}" if human_readable else d

    async def add_user_money(self, userid: int, amount: int):
        usermoney = await self.get_user_money(userid, human_readable=False)
        return await self.set_user_money(userid, usermoney + amount)

    async def get_leaderboard(self, guild=None, maxusers=10):
        """
            Gets the users from the database with the most amount of money
            Guild param must be a Discord Guild object, if specified.
            If :param:guild is specified, only users from that guild will be returned.
            If :param:maxusers is specified, the return value will be a max of that
        """
        users = [int(u) for u in self._cache.get("users") if u]
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
    else: prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)
