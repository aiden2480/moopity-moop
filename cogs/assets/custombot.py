from datetime import datetime as dt, timedelta as td
from logging import FileHandler, Formatter, StreamHandler, getLogger
from os import environ, path

from aiohttp import ClientSession
from discord import Colour, Embed, Permissions, utils
from discord.ext import commands

from cogs.assets import database

try: from dotenv import load_dotenv
except ImportError: pass
else: load_dotenv(path.join(path.dirname(path.dirname(path.dirname(__file__))), ".env"))


Default = "Any"

# Helper classes
class CustomEmbed(object):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def EmptyEmbed(self, set_footer=True, set_timestamp=True, **kwargs):
        """Generate an empty embed for the bot"""
        e = Embed()
        e.title = kwargs.get("title", "")
        e.description = kwargs.get("description", "")
        e.colour = kwargs.get("colour", Colour.blue())

        if set_timestamp:
            e.timestamp = kwargs.get("timestamp", dt.utcnow())
        if set_footer:
            e.set_footer(text=self.bot.user, icon_url=self.bot.user.avatar_url)
        return e


class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


# Main CustomBot class
class CustomBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        # Initialize essentials
        super().__init__(*args, **kwargs)

        # Add an instance of our database
        self.db = database.Database(environ.get("DATABASE_URL"))

        # A buncha variables I'll be using later on
        self.env = environ  # Enable env to be used bot-wide
        self.development = True if self.env.get("DEVELOPMENT", "False").upper() == "TRUE" else False
        self.guild_invite_url = "https://discord.gg/AJj45Sj"  # Support guild invite url
        self.session = ClientSession(loop=self.loop)  # HTTP request manager
        self.startup_time = dt.utcnow()  # Store bot startup time
        self.EmptyEmbed = CustomEmbed(self).EmptyEmbed  # Embed template (I'm cheating lol)
        self.default_prefix = "m!" if not self.development else "." # Yayeet
        self.delete_guild_data = False if self.development else True # Delete guild data when the bot leaves
        self.website_url = "https://moopity-moop.chocolatejade42.repl.co" if not self.development else "http://localhost:8080"
        self.oauth_callback = f"{self.website_url}/login"
        self.get_dt = lambda:dt.utcnow()

        # Set up logging
        self.logger = getLogger("bot")
        self.cmdlogger = getLogger("bot.command")
        self.guildlogger = getLogger("bot.guild")
        self._weblogger = getLogger("web")

        location = "./moopitymoop.log" if self.development else "../moopitymoop.log"
        datefmt = "%H:%M:%S" if self.development else "%d/%m/%Y %H:%M:%S"
        fmode = "w" if self.development else "a"
        formatter = Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s", datefmt=datefmt)
        stream = StreamHandler()
        fileh = FileHandler(location, mode=fmode)
        stream.setLevel(10)
        fileh.setLevel(10)
        stream.setFormatter(formatter)
        fileh.setFormatter(formatter)

        self.logger.addHandler(stream)
        self.logger.addHandler(fileh)
        self.logger.setLevel(self.env.get("LOG_LEVEL", 10))
        self._weblogger.addHandler(stream)
        self._weblogger.addHandler(fileh)
        self._weblogger.setLevel(self.env.get("LOG_LEVEL", 10))

        self.logger.debug("Created bot logger")
        self._weblogger.debug("Created web logger")

        # A big 'ol list of emojis
        self.emoji = AttrDict({
            # Non-animated
            "pig": "<:pig:589642416299180043>",
            "minecraft": "<:minecraft:582072230574293013>",
            "goldenapple": "<:goldenapple:582083249153638400>",
            "craftingtable": "<:craftingtable:582083249631920128>",
            # Animated
            "rainbowsheep": "<a:rainbowsheep:582083253544943635>",
            "minecraftSpin": "<a:minecraftSpin:582107014256263168>",
        })

    # Redefined class methods
    def run(self, *args, **kwargs):
        """Runs the bot, waow! (`Blocking`)"""
        kwargs["reconnect"] = True
        super().run(self.env["BOT_TOKEN"], *args, **kwargs)

    async def logout(self, *args, **kwargs):
        self.logger.debug("Closing custom aiohttp ClientSession")
        await self.session.close()
        if hasattr(self, "webrunner"):
            self.logger.debug("Closing website runner")
            await self.webrunner.cleanup()
        self.logger.debug("Running original discord.py logout")
        await super().logout(*args, **kwargs)
    
    def add_cog(self, cog, *, hide=False):
        """If param `hide` is `True`, the load
        time of the cog will be set to a time far
        beyond that of the others, putting it at the back"""
        try: super().add_cog(cog)
        except: return
        d = dt.utcnow() if not hide else dt.utcnow()+td(weeks=4)

        if hasattr(cog, "config"):
            try: cog.config["loadtime"]
            except KeyError: cog.config["loadtime"] = d
        else:
            cog.config = dict(loadtime=d)

    # Other functions
    def time_between(self, dateone: dt, datetwo: dt) -> str:
        """Find the time between `dateone` and `datetwo` and
        return it in a human readable format fit for discord!\n
        Param `dateone` must be an older date than `datetwo`"""
        ut = (datetwo - dateone).total_seconds()
        key = ["days", "hours", "minutes", "seconds"]
        ut = [
            int(ut // (60 * 60 * 24)),
            int((ut % (60 * 60 * 24)) // (60 * 60)),
            int(((ut % (60 * 60 * 24)) % (60 * 60)) // 60),
            int(((ut % (60 * 60 * 24)) % (60 * 60)) % 60),
        ]
        uptime = [f"{i} {key[u]}" for u, i in enumerate(ut) if i != 0]

        if len(uptime) == 1:
            uptime = uptime[0]
        else:
            uptime = ", ".join(uptime[:-1]) + " and " + uptime[-1]

        return uptime

    def get_uptime(self) -> str:
        """Find the uptime of the bot (fmt: relative `d`/`h`/`m`/`s`)"""
        return self.time_between(self.startup_time, dt.utcnow())

    def invite_url(self, p: int = 335932480, guildid: int=None) -> str:
        """Generate an invite URL for the bot
        using the permsisions provided"""
        url = utils.oauth_url(
            self.user.id, permissions=Permissions(p),
            redirect_uri=self.guild_invite_url,
        )
        return f"{url}&guild_id={guildid}" if guildid else url
