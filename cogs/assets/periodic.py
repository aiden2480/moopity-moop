from asyncio import get_event_loop
from datetime import datetime as dt
from datetime import timedelta as td
from typing import List

from aiohttp import ClientSession
from discord import Guild
from discord.ext import commands, tasks

# The number of seconds to wait
# if the last ping was successful
ONLINE = 60 * 10
# The number of seconds to wait
# if the last ping was unsuccessful
OFFLINE = 60 * 25


class Checker(object):
    # TODO: Add a `self.history` thingo for advanced ping detection
    # TODO: This fucks itself up when unloading the cog
    """The object that controls all of the handling for the
    pinging of each individual server (multiple instances)"""

    def __init__(self, bot: commands.Bot, sess: ClientSession, guildid: int, serverip: str):
        print(f"checker init {guildid} {serverip!r}")
        self.bot = bot
        self.ip = serverip
        self.guildid = guildid
        self.history: List[bool] = list()

        self.guild: Guild
        self.result: str
        self.online = False
        # ^^ Checks if online has changed since last iteration
        self.sess = sess
        self._task.start()

    # Main function
    @tasks.loop(seconds=ONLINE)
    async def _task(self):
        """Pings the server and updates the info"""
        print(f"checking {self.guild.id} {self.ip!r}")

        # Fetch the stats
        async with self.sess.get(f"https://api.minetools.eu/ping/{self.ip}") as resp:
            data = await resp.json()
            data["favicon"] = f"https://api.minetools.eu/favicon/{self.ip}"

        # Sort the data
        ping = 5 * round(data["latency"] / 5)
        players = data["players"]["online"]
        maxplayers = data["players"]["max"]
        online = f"{players}/{maxplayers} plyrs - {ping}ms ping"
        result = online if ping > 5 else "OFFLINE"
        online = result != "OFFLINE"

        # Update class variables
        self.result = result
        self.online_changed = self.online != online
        self.online = online
        await self.guild.me.edit(nick=result)

    # Extra functions
    @_task.before_loop
    async def before_task(self):
        """Make sure the cache is ready"""
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.guildid)

    @_task.after_loop
    async def after_task(self):
        """Update the wait time, if needed"""
        if not self.online_changed:
            return
        if self.online:
            self._task.change_interval(seconds=ONLINE)
        else:
            self._task.change_interval(seconds=OFFLINE)


class ServerStatus(commands.Cog):
    # TODO: What happens when someone changes the IP while the bot is still pinging hmm?
    """The cog that handles all the server pinging"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        self.sess = bot.session
        self.tasks: List[Checker] = list()

    @commands.Cog.listener(name="on_ready")
    async def load_ips(self):
        end = dt.utcnow() + td(seconds=40)
        while self.db.guild_server_ips == dict():
            if dt.utcnow() > end:
                return  # No data was loaded after 40 seconds
        for guild in self.db.guild_server_ips.items():
            self.create_task(int(guild[0]), guild[1])

    def cog_unload(self):
        """Finish & close all pingers"""
        self.bot.logger.debug(f"Closed {len(self.tasks)} tasks")
        return [task._task.stop() for task in self.tasks]

    def create_task(self, guildid: int, serverip: str):
        """Creates a task"""
        tsk = Checker(self.bot, self.sess, guildid, serverip)
        self.tasks.append(tsk)


class DiscordBotListPosters(commands.Cog):
    """The cog that facilitates the posting of server
    counts and member counts to the various bot lists
    that I hope Moopity Moop will soon be a part of!"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot):
    # FIXME: Fix periodic cog
    # TODO: Create cog for pinging bot lists
    # bot.add_cog(ServerStatus(bot))
    # bot.add_cog(DiscordBotListPosters(bot))
    pass
