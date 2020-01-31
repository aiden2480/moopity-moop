from datetime import datetime as dt
from datetime import timedelta as td
from logging import FileHandler, Formatter, StreamHandler, getLogger
from os import environ, path
from re import compile
from subprocess import check_output, CalledProcessError
from typing import List, Optional

from aiohttp import ClientSession
from discord import Message, Permissions, User, utils
from discord.ext import commands
from cogs.assets import database

try: from dotenv import load_dotenv
except ImportError: pass
else: load_dotenv(path.join(path.dirname(path.dirname(path.dirname(__file__))), ".env"))
mention_regex = compile(r"<@\!?([0-9]{1,19})>")


class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

DEFAULT_BUCKET = commands.BucketType.member

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
        self.default_prefix = "m!" if not self.development else "." # Yayeet
        self.delete_data_on_remove = True if self.env.get("DELETE_DATA_ON_REMOVE", "False").upper() == "TRUE" else False
        self.website_url = "https://www.moopitymoop.tk" if not self.development else "http://localhost:8080"
        self.oauth_callback = f"{self.website_url}/login"
        
        try: self.VERSION = check_output("git describe --tags --always", shell=True).decode().strip()
        except CalledProcessError: self.VERSION = "Latest"

        # Set up logging
        self.logger = getLogger("bot")
        self.cmdlogger = getLogger("bot.command")
        self.guildlogger = getLogger("bot.guild")
        self._weblogger = getLogger("web")

        location = "./moopitymoop.log" if self.development else "../moopitymoop.log"
        datefmt = "%H:%M:%S" if self.development else "%d/%m/%Y %H:%M:%S"
        fmode = "w" if self.development else "a"
        formatter = Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt=datefmt)
        stream = StreamHandler()
        fileh = FileHandler(location, fmode, "utf-8")
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
        self.logger.debug("Creating bot object")

        # A big 'ol list of emojis
        self.emoji = AttrDict({
            # Non-animated
            "pig": "<:pig:589642416299180043>",
            "minecraft": "<:minecraft:582072230574293013>",
            "goldenapple": "<:goldenapple:582083249153638400>",
            "craftingtable": "<:craftingtable:582083249631920128>",
            "goldingot": "<:goldingot:652065037933871132>",
            "ironingot": "<:ironingot:652064889602441216>",

            # Animated
            "rainbowsheep": "<a:rainbowsheep:582083253544943635>",
            "spinningminecraft": "<a:spinningminecraft:652245643812667433>",
        })
        self.ingot = self.emoji.ironingot # Shortcut

    # Redefined class methods
    def run(self, *args, **kwargs) -> None:
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
    
    def add_cog(self, cog, *, hide=False) -> None:
        """If param `hide` is `True`, the load
        time of the cog will be set to a time far
        beyond that of the others, putting it at the back"""
        try: super().add_cog(cog)
        except: return

        d = dt.utcnow() if not hide else dt.utcnow()+td(weeks=4)
        cog.__cog_settings__["loadtime"] = d
    
    async def get_context(self, message: Message, *, cls=None):
        return await super().get_context(message, cls=cls or CustomContext)

    # Other functions
    @property
    def cog_load_order(self) -> List[commands.Cog]:
        return sorted(self.cogs.values(), key=lambda c:c.__cog_settings__["loadtime"])
    
    @property
    def days_old(self) -> int:
        return (dt.utcnow()-self.user.created_at).days
    
    @property
    def created_at(self) -> dt:
        if self.user is None:
            return dt.utcnow()
        return self.user.created_at
    
    @property
    def owner(self) -> User:
        return self.get_user(self.owner_id)
    
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
        return uptime[0] if len(uptime) == 1 else ", ".join(uptime[:-1]) + " and " + uptime[-1]

    @property
    def uptime(self) -> str:
        """Find the uptime of the bot (fmt: relative `d`/`h`/`m`/`s`)"""
        return self.time_between(self.startup_time, dt.utcnow())

    def invite_url(self, p: int=335932480, guildid: int=None) -> str:
        """Generate an invite URL for the bot
        using the permsisions provided"""
        url = utils.oauth_url(
            self.user.id, permissions=Permissions(p),
            redirect_uri=self.guild_invite_url,
        )
        return f"{url}&guild_id={guildid}" if guildid else url


# I'll also make a custom Cog class, for logging pruposes
class CustomCog(commands.Cog):
    def __init__(self, cog: commands.Cog):
        """Creates an instance of a regular cog, with a few extra things I might want"""
        cog.logger = getLogger(f"bot.cogs.{cog.qualified_name.lower()}")

# How about custom ctx, while we're at it
class CustomContext(commands.Context):
    async def react(self, msg: Optional[Message], *reactions):
        """Add reactions to a message, absently. i.e. we don't really care if it fails.
        If `msg` is supplied, reactions will be added to ctx.message
        Retuns if the reaction add was successful or not"""
        reactions = list(reactions)
        if not isinstance(msg, Message):
            reactions.insert(0, msg)
            msg = self.message
        
        for emoji in reactions:
            try: await msg.add_reaction(emoji)
            except: return False
        return True
    
    @property
    def clean_prefix(self):
        m = mention_regex.match(self.prefix)
        if m:
            user = self.bot.get_user(int(m.group(1)))
            if user:
                return f"@{user.name} "
        return self.prefix
    
    @property
    def perms(self):
        """Returns the permissions of the context"""
        if self.guild is not None:
            return self.channel.permissions_for(self.guild.me)
        return self.channel.permissions_for(self.bot.user)

# A custom cooldown so I can give different users different cooldowns :)
class CustomCooldown:
    def __init__(self, rate, per, prem_rate, prem_per, bucket, **premium):
        self.premium = premium
        self.default_mapping = commands.CooldownMapping.from_cooldown(rate, per, bucket)
        self.premium_mapping = commands.CooldownMapping.from_cooldown(prem_rate, prem_per, bucket)

    def __call__(self, ctx: commands.Context):
        mapping = self.premium_mapping if self.is_premium(ctx) else self.default_mapping
        bucket = mapping.get_bucket(ctx.message)

        retry_after = bucket.update_rate_limit()
        if retry_after:
            error = commands.CommandOnCooldown(bucket, retry_after)
            error.premium = mapping is self.premium_mapping
            error.premium_mapping = self.premium_mapping
            raise error
        return True

    def is_premium(self, ctx: commands.Context):
        userid = ctx.author.id
        
        if self.premium["owner"]:
            if userid == ctx.bot.owner_id:
                return True
        
        if self.premium["admin"]:
            if ctx.author.permissions_in(ctx.channel).administrator:
                return True
        
        if self.premium["guild"]:
            if userid in [m.id for m in ctx.bot.get_guild(496081601755611137).members]:
                return True
        
        return False

def cooldown(*args, **kwargs):
    """
    Implements a custom cooldown which means I can apply different cooldowns for different users

    **ARGS**
    The args are the arguments required to set the ratelimits

    - If two arguments are supplied, they must be `rate` and `per`, meaning no seperate cooldown for premium and the default BucketType
    - If three arguments are supplied, they must be `rate`, `per`, and a `bucket`. No seperate cooldown for premium
    - If four arguments are supplied, they must be `rate`, `per`, `premium_rate` and `premium_per`. This allows for a custom cooldown to be set for premium users
    - If five arguments are supplied, they must be `rate`, `per`, `premium_rate`, `premium_per` and `bucket`. Allowing both a different ratelimit for premium and also a different bucket to be set
    
    **KWARGS**
    The keyword arguments are the settings for what does and doesn't count as premium for this command
    Below listed are the different options and their default settings

    - `guild=True` If being in the support guild should make a user "premium"
    - `admin=False` If the user should use premium cooldown if they have `administrator` perms
    - `owner=True` If the bot owner should be exempt from cooldowns 

    > More copy pasta from Danny's repo. This overwrites the default decorator in order to implement custom cooldown.
    https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/core.py#L1740
    """
    assert len(args) >= 2 and len(args) <= 5, f"Invalid amount of args provided ({len(args)})"
    premium = dict()
    premium["guild"] = kwargs.pop("guild", True)
    premium["admin"] = kwargs.pop("admin", False)
    premium["owner"] = kwargs.pop("owner", True)

    if kwargs:
        raise TypeError(f"Invalid premium argument {list(kwargs.keys())[0]!r}")

    if len(args) == 5: # Decorator supplied rate, per, prate, pper and bucket
        rate, per, prate, pper, bucket = args
    if len(args) == 4:
        rate, per, prate, pper = args
        bucket = DEFAULT_BUCKET
    elif len(args) == 3: # Decorator supplied rate, per and bucket
        rate, per, bucket = args
        prate, pper = rate, per
    elif len(args) == 2: # Decorator supplied rate and per
        rate, per = args
        prate, pper = rate, per
        bucket = DEFAULT_BUCKET
    
    cool = CustomCooldown(rate, per, prate, pper, bucket, **premium)
    return commands.check(cool)

# Converters
class MinecraftUser(commands.Converter):
    """Ensures the argument passed is a valid Minecraft user,
    ie the name is not over the character limit, etc"""
    async def convert(self, ctx: CustomContext, argument: str) -> str:
        base = f"Username `{argument!r}` is not a valid Mineraft username\n"
        
        if len(argument) > 16:
            raise commands.BadArgument(f"{base}Usernames are a max of 16 characters")
        
        return argument

class MinecraftServer(commands.Converter):
    """Ensures the argument passed is a valid Minecraft server,
    ie the ip is not over the character limit, etc"""
    async def convert(self, ctx: CustomContext, argument: str) -> str:
        if not all((
            len(argument) > 16, # TODO what the actual len lol?
            # TODO: spaces, characters, etc
        )):
            raise commands.BadArgument(f"IP {argument!r} is not a valid Mineraft IP")
        return argument
    