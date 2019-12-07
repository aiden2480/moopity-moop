# Importing
from datetime import datetime as dt
from datetime import timedelta as td
from random import choice
from time import time
from traceback import format_exception
from urllib.parse import urlencode
from warnings import filterwarnings

from aiohttp import web, __version__ as aio_version
from aiohttp_jinja2 import get_env as jinja_env
from aiohttp_jinja2 import setup as jinja_setup
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from discord import Activity, AsyncWebhookAdapter, Colour, Embed, Forbidden
from discord import Game, HTTPException, Message, Status, Webhook, __version__ as dpy_version
from discord.ext import commands
from humanize import naturaltime
from jinja2 import FileSystemLoader
from json_store_client import EmptyResponseWarning
from logging import getLogger

from cogs.assets.custom import CustomBot
from cogs.assets.database import get_prefix as prefix
from website.frontend import middlewares, routes as frontend_routes, web_get_cmd_data
from website.api import routes as backend_routes

# Create bot
bot = CustomBot(
    command_prefix=prefix,
    description="A small bot with commands to utilise your Minecraft/Discord experience",
    owner_id=272967064531238912,
    status=Status.idle,
    activity=Activity(type=2, name="Windows XP startup sounds"),
    case_insensitive=True,
)

# Create website
site = web.Application()
site["bot"] = bot
site["db"] = bot.db
site.logger = bot._weblogger
rand=lambda:choice("abcdefghijklmnopqrstuvwxyz")
jinja_setup(site, loader=FileSystemLoader("./website/templates"))
session_setup(site, EncryptedCookieStorage(
    bot.env.get("WEBSITE_COOKIE_TOKEN", rand()*32).encode(),
    cookie_name="MOOPITYMOOP",
    max_age=3600*24*31, # One year
))
for mw in middlewares:
    site.middlewares.append(mw)
getLogger("aiohttp_session").setLevel(40)

# Bot Events
@bot.event
async def on_ready():
    """Async setup function for the bot"""
    if hasattr(bot, "ready_time"):
        return
    bot.ready_time = dt.utcnow()
    bot.logger.info("Bot ready - {0.name!r} ({0.id})".format(bot.user))

    # Update env on site
    env = jinja_env(site)
    env.globals.update(aidzman=bot.get_user(bot.owner_id))

    # Update oauth stuff for the website
    site.oauth_data = {
        "client_id": bot.user.id,
        "client_secret": bot.env["BOT_CLIENT_SECRET"],
        "redirect_uri": bot.oauth_callback,
    }
    site.oauth_url = "https://discordapp.com/api/oauth2/authorize?" + urlencode({
        "client_id": bot.user.id,
        "redirect_uri": bot.oauth_callback,
        "response_type": "code",
        "scope": "identify guilds",
    })

    # Announce our presence to the whole wide world
    webhook = Webhook.from_url(bot.env["COMMANDS_WEBHOOK_URL"], adapter=AsyncWebhookAdapter(bot.session))
    e = Embed(
        colour=0x00B7D9, timestamp=dt.utcnow(),
        description=f"Time taken to load: `{bot.get_uptime()}`",
    )

    e.set_footer(text=bot.user)
    e.set_author(name="Bot restarted", icon_url="https://bit.ly/2Sd33Wx")
    await webhook.send(embed=e, username=bot.user.name, avatar_url=bot.user.avatar_url)


@bot.event
async def on_connect():
    await bot.db.update_cache()
    bot.database_ready = True

    bot.logger.info(f"Bot reconnected at {dt.now():%H:%M:%S}")
    bot.logger.info("Database ready")

    await bot.change_presence(
        status=Status.online,
        afk=False,
        activity=Game(name=choice((
            "Minecraft",
            f"{bot.default_prefix}help for commands!",
            f"created by {bot.owner}",
            f"{len(bot.users)} users accross {len(bot.guilds)} servers",
    ))))


@bot.event
async def on_disconnect():
    bot.logger.info(f"Bot disconnected at {dt.now():%H:%M:%S}")


@bot.event
async def on_message(m: Message):
    if m.author.bot:
        return

    # Process commands
    await bot.wait_until_ready()
    await bot.process_commands(m)

    # Just in case some idiot managed to lose the prefix
    ctx = await bot.get_context(m)
    if ctx.invoked_subcommand is None and ctx.guild:
        if m.content.strip() == ctx.me.mention:
            try:
                await ctx.trigger_typing()
                prfx = await bot.db.get_guild_prefix(m.guild.id) or bot.default_prefix
                await ctx.send(f"Hello **{ctx.author}** 👋 My prefix in this server is `{prfx}`")
            except Forbidden: await ctx.react("‼") # Can't send messages


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Bot error handler"""

    if getattr(ctx, "error_handled", False):
        return # Check if error already handled

    # Find the actual error, if it is a `CommandInvokeError`
    error = getattr(error, "original", error)

    # Setup response embed
    e = Embed(colour=Colour.blue(), timestamp=dt.utcnow())
    e.set_footer(text=bot.user, icon_url=bot.user.avatar_url)

    # Error groups
    ignored_errors = (commands.NotOwner, commands.CommandNotFound)
    param_errors = (
        commands.MissingRequiredArgument,
        commands.BadArgument,
        commands.TooManyArguments,
        commands.UserInputError,
    )

    # Command errors
    if isinstance(error, ignored_errors):
        pass
    elif isinstance(error, param_errors):
        e.title = "Incorrect use of command"
        e.description = str(error)
        e.add_field(name="The correct usage is", value=f"```{ctx.clean_prefix}{ctx.command} {ctx.command.signature}```")
        await ctx.send(embed=e)
    elif isinstance(error, commands.DisabledCommand):
        e = Embed(colour=0xFB8F02)
        e.set_author(name="Disabled command", icon_url="https://bit.ly/2JHJ91I")
        if ctx.author.id == bot.owner_id:
            e.description = "Bypassing disable.."
            msg = await ctx.send(embed=e)

            ctx.command.enabled = True
            try: await ctx.reinvoke()
            except Exception as err:
                await ctx.send(f"```py\n{err.__class__.__name__}: {err}```")
                raise
            ctx.command.enabled = False

            e.description += " Done\nRe-disabling command"
            await msg.edit(embed=e, delete_after=5)
        else:
            e.timestamp = dt.utcnow()
            e.set_footer(text=f"Run by {ctx.author}", icon_url=ctx.author.avatar_url)
            e.description = "This command has been disabled. Please wait while it is being fixed 🛠"
            await ctx.send(embed=e)
    elif isinstance(error, commands.NoPrivateMessage):
        e.title = "Error while performing command"
        e.description = "This command cannot be used in a DM",
        await ctx.send(embed=e)
    elif isinstance(error, commands.CommandOnCooldown):
        e.title = "This command is on cooldown!"
        e.description = f"Please try again in {naturaltime(dt.now()+td(seconds=error.retry_after), future=True)}"
        await ctx.send(embed=e)
    elif isinstance(error, commands.MissingPermissions):
        perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
        e.title = "You're missing permissions!"
        e.description = f"You can't run this command :angry: Come back when you have the following permissions:\n{', '.join(perms)}"
        await ctx.send(embed=e)
    elif isinstance(error, commands.BotMissingPermissions):
        perms = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_perms]
        e.title = "I'm missing permissions!"
        e.description = f"I need the following permissions to execute this command:\n{', '.join(perms)}"
        
        try: await ctx.send(embed=e)
        except Forbidden: # Can't send embeds
            try: await ctx.send(e.description) # Can't send messages
            except: await ctx.react("‼")

    # Other errors
    elif isinstance(error, HTTPException):
        if error.status == 400 and "fewer in length" in error.text.lower():
            e.title = "Error executing command"
            e.description = "Too many characters to send reply 🤷"
            await ctx.send(embed=e)
    else:
        formatted = "\n".join(format_exception(type(error), error, error.__traceback__, 10))
        error_code = f"`{error.__class__.__name__}//{int(time())}`"
        bot.logger.error(formatted)

        e.color = 0xFB8F02
        e.description = f"```py\n{formatted}```"
        e.set_author(name="An error occoured", icon_url="https://bit.ly/2JHJ91I")
        e.add_field(name="User", value=f"{ctx.author}\n{ctx.author.id}")
        e.add_field(name="Error code", value=error_code)
        e.add_field(name="Guild", value=ctx.guild.name) if ctx.guild else None
        e.add_field(name="Channel", value=f"{'#' if ctx.guild else ''}{ctx.channel}")

        if ctx.author == bot.owner:
            return await ctx.send(embed=e)

        webhook = Webhook.from_url(bot.env["ERROR_WEBHOOK_URL"], adapter=AsyncWebhookAdapter(bot.session))
        await webhook.send(embed=e, username=bot.user.name, avatar_url=bot.user.avatar_url)

        em = Embed(
            color=0xFFA500, timestamp=dt.utcnow(), title="💣 Oof, an error occoured 💥",
            description=f"Please [join the support guild]({bot.guild_invite_url}) and tell **{bot.owner}** what happened to help fix this bug.\n\nError code: {error_code}",
        )

        em.set_footer(text=f"< Look for this guy!", icon_url=bot.owner.avatar_url)
        await ctx.send(embed=em)


# Finally start the app!
if __name__ == "__main__":
    loop = bot.loop
    bot.logger.debug("Loading cogs")
    for cog in [
        "general",
        "minecraft",
        "image",
        "currency",
        "config",
        "fun",
        "developer",
        "hidden",
        # Extra cogs
        "assets.events",
        "assets.periodic",
    ]: bot.load_extension(f"cogs.{cog}")
    bot.load_extension("jishaku")
    bot.logger.debug("Cogs loaded")

    # Warnings
    filterwarnings("ignore", category=EmptyResponseWarning)
    [bot.logger.warning(f"Disabled command `{cmd!s}` found in cog `{cmd.cog.qualified_name}`") for cmd in bot.walk_commands() if not cmd.enabled]
    [bot.logger.warning(f"Command `{cmd!s}` found in cog `{cmd.cog.qualified_name}` has no help text!") for cmd in bot.commands if cmd.help is None]

    # Setup the website
    site.add_routes(frontend_routes)
    site.add_routes(backend_routes)
    site.router.add_static("/static", "./website/static")
    site.on_startup.append(web_get_cmd_data)
    env = jinja_env(site)
    env.globals.update(bot=bot, db=bot.db, app=site, dpy_ver=dpy_version, aio_ver=aio_version)
    env.globals.update(**{i.__name__:i for i in [
        reversed, len, range, list, dict, str,
    ]})

    # Run the website
    webrunner = web.AppRunner(site)
    loop.run_until_complete(webrunner.setup())
    webserver = web.TCPSite(webrunner)
    loop.run_until_complete(webserver.start())
    site.logger.info(f"Starting website on {webserver.name}")
    bot.webrunner = webrunner

    # Run the bot
    try:
        bot.logger.info("Starting bot")
        bot.run()
    finally:
        bot.logger.info("Stopping script with exit code 0")

    # Close up from website
    site.logger.debug("Closing asyncio loop")
    loop.close()
