from typing import Set

from discord import Guild
from discord.ext import commands, tasks
from cogs.assets.custom import CustomCog

# The number of seconds to wait
# if the last ping was successful
ONLINE = 60 * 10
# The number of seconds to wait
# if the last ping was unsuccessful
OFFLINE = 60 * 25


class Checker(object):
    # TODO: Add a `self.history` thingo for advanced ping detection
    # TODO: This breaks itself when unloading the cog
    """The object that controls all of the handling for the
    pinging of each individual server (multiple instances)"""

    def __init__(self, bot: commands.Bot, guildid: int, serverip: str):
        self.bot = bot
        self.ip = serverip
        self.guildid = guildid
        self.history: List[bool] = list()

        self.guild: Guild
        self.result: str
        self.online = False
        # ^^ Checks if online has changed since last iteration
        self.sess = bot.session
        self.tsk.start()

    # Main function
    @tasks.loop(seconds=ONLINE)
    async def tsk(self):
        """Pings the server and updates the info"""
        print(f"checking {self.guild.id} {self.ip!r}")

        # Fetch the stats
        async with self.sess.get(f"https://api.minetools.eu/ping/{self.ip}") as resp:
            data = await resp.json()
            data.pop("favicon")

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
    @tsk.before_loop
    async def before_task(self):
        """Make sure the cache is ready"""
        await self.bot.wait_until_ready()
        self.guild = self.bot.get_guild(self.guildid)

    @tsk.after_loop
    async def after_task(self):
        """Update the wait time, if needed"""
        if not self.online_changed:
            return
        if self.online:
            self.tsk.change_interval(seconds=ONLINE)
        else:
            self.tsk.change_interval(seconds=OFFLINE)


class ServerStatus(CustomCog):
    # TODO: What happens when someone changes the IP while the bot is still pinging hmm?
    # TODO rewrite this lulul
    """The cog that handles all the server pinging"""

    def __init__(self, bot: commands.Bot):
        super().__init__(self)
        self.bot = bot
        self.db = bot.db
        self.tasks: Set[Checker] = set()
    
    @commands.Cog.listener()
    async def on_ready(self):
        while not self.db.ready:
            pass
        if self.tasks != set():
            return # Tasks already loaded
        
        self.logger.debug(f"{self.__class__.__name__!r} cog ready, loading checkers")
        for guildid, serverip in self.db.guild_server_ips.items():
            self.create_task(int(guildid), serverip)
        self.logger.debug("Finished loading checkers")

    def cog_unload(self):
        """Finish & close all pingers"""
        [task.tsk.stop() for task in self.tasks]
        self.logger.debug(f"Closed {len(self.tasks)} tasks while unloading cog {self.__class__.__name__!r}")

    def create_task(self, guildid: int, serverip: str):
        """Creates a task"""
        tsk = Checker(self.bot, guildid, serverip)
        self.tasks.add(tsk)
        return tsk
    
    def stop_task(self, guildid: int):
        """Stop a particular task that a guild is running"""
        task = [t for t in self.tasks if t.guildid == guildid]
        task = task[0] if task else None
        if not task:
            print(f"No task found by Guild ID {guildid!r}")
        print(f"Closing task {task}")
        task.tsk.stop()
    
    def reload_task(self, guildid: int):
        """Reload a task, updating the data to ping"""
        # TODO: Make this lol
        ip = self.db.guild_server_ips.get(str(guildid))
        self.stop_task(guildid)
        self.create_task(guildid, ip)


def setup(bot: commands.Bot):
    bot.add_cog(ServerStatus(bot))
