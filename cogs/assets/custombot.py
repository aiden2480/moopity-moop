from datetime import datetime as dt
from os import getenv
from aiohttp import ClientSession

from discord import Permissions, Embed, Colour, utils
from discord.ext.commands import Bot
from cogs.assets import database

Default = "Any"

# Helper classes
class CustomEmbed(object):
    def __init__(self, bot):
        self.bot = bot

    def EmptyEmbed(self, set_footer= True, set_timestamp= True, **kwargs):
        """Generate an empty embed for the bot"""
        e = Embed()
        e.title = kwargs.get("title", "")
        e.description = kwargs.get("description", "")
        e.colour = kwargs.get("colour", Colour.blue())

        if set_timestamp: e.timestamp = kwargs.get("timestamp", dt.utcnow())
        if set_footer: e.set_footer(text= self.bot.user, icon_url= self.bot.user.avatar_url)
        return e

class AttrDict(dict):
	def __getattr__(self, attr):
		return self[attr]

	def __setattr__(self, attr, value):
		self[attr] = value

# Main CustomBot class
class CustomBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # Initialize the bot instance

        # A buncha variables I'll be using later on
        self.database = database.Database # Database handler
        self.env = getenv # Enable env to be used bot-wide
        self.guild_invite_url = "https://discord.gg/AJj45Sj" # Support guild invite url
        self.sess = ClientSession(loop= self.loop) # HTTP request manager
        self.startup_time = dt.utcnow() # Store bot startup time
        self.EmptyEmbed = CustomEmbed(self).EmptyEmbed # Embed template (I'm cheating lol)
        self.website_url = "https://moopity-moop.chocolatejade42.repl.co"
        self.default_prefix = "m!"

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
        super().run(self.env("BOT_TOKEN"), *args, **kwargs)

    # Other functions
    def time_between(self, dateone: dt, datetwo: dt) -> str:
        """Find the time between `dateone` and `datetwo` and
        return it in a human readable format fit for discord!\n
        Param `dateone` must be an older date than `datetwo`"""
        ut = (datetwo- dateone).total_seconds()
        key = ["days", "hours", "minutes", "seconds"]
        ut = [
            int(ut // (60*60*24)), int((ut % (60*60*24)) // (60*60)),
            int(((ut % (60*60*24)) % (60*60)) // 60), int(((ut % (60*60*24)) % (60*60)) % 60)]
        uptime = [f"{i} {key[u]}" for u,i in enumerate(ut) if i != 0]
        
        if len(uptime) == 1:
            uptime = uptime[0]
        else:
            uptime = ", ".join(uptime[:-1]) +" and "+ uptime[-1]
        
        return uptime

    def get_uptime(self) -> str:
        """Find the uptime of the bot (fmt: relative `d`/`h`/`m`/`s`)"""
        return self.time_between(self.startup_time, dt.utcnow())

    def invite_url(self, p: int= 335932480) -> str:
        """Generate an invite URL for the bot
        using the permsisions provided"""
        return utils.oauth_url(
            self.user.id,
            permissions= Permissions(p),
            redirect_uri= self.guild_invite_url,
        )
