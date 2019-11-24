# Importing
from datetime import datetime as dt
from datetime import timedelta as td
from random import choice, randint
from time import time
from traceback import format_exception
from urllib.parse import urlencode
from warnings import filterwarnings

from aiohttp import web
from aiohttp_jinja2 import get_env as jinja_env
from aiohttp_jinja2 import setup as jinja_setup
from aiohttp_session import setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from discord import Activity, AsyncWebhookAdapter, Colour, Embed
from discord import Game, HTTPException, Message, Status, Webhook
from discord.ext import commands
from humanize import naturaltime
from jinja2 import FileSystemLoader
from json_store_client import EmptyResponseWarning
from logging import getLogger

from cogs.assets.custombot import CustomBot
from cogs.assets.database import get_prefix as prefix
from cogs.assets.website import OAUTH_SCOPE, middlewares
from cogs.assets.website import routes as web_routes
from cogs.assets.website import web_get_cmd_data

# Create bot
bot = CustomBot(
    command_prefix=prefix,
    description="A small bot with commands to utilise your Minecraft/Discord experience",
    owner_id=272_967_064_531_238_912,
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
    await bot.db.update_cache()

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
        "scope": OAUTH_SCOPE,
    })

    # Announce our presence to the whole wide world
    webhook = Webhook.from_url(bot.env["COMMANDS_WEBHOOK_URL"], adapter=AsyncWebhookAdapter(bot.session))
    e = Embed(
        colour=0x00B7D9,
        timestamp=dt.utcnow(),
        description=f"Time taken to load: `{bot.get_uptime()}`",
    )

    e.set_footer(text=bot.user)
    e.set_author(name="Bot restarted", icon_url="https://bit.ly/2Sd33Wx")

    await webhook.send(embed=e, username=bot.user.name, avatar_url=bot.user.avatar_url)


@bot.event
async def on_connect():
    bot.logger.debug(f"Bot reconnected at {dt.now():%H:%M:%S}")
    await bot.change_presence(
        status=Status.online,
        afk=False,
        activity=Game(name=choice((
            f"{bot.default_prefix}help for commands!",
            f"created by {await bot.fetch_user(bot.owner_id)}",
            "Minecraft",
    ))))


@bot.event
async def on_disconnect():
    bot.logger.debug(f"Bot disconnected at {dt.now():%H:%M:%S}")
    await bot.change_presence(
        status=Status.idle, afk=True,
        activity=Game(name="disconnected.. Massive F 😟")
    )


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
        if m.content.strip() == ctx.guild.me.mention:
            # TODO: Fix this up (also in the general cog)
            await ctx.trigger_typing()
            prfx = await bot.db.get_guild_prefix(m.guild.id) or bot.default_prefix
            await ctx.send(
                f"Hello **{ctx.author}** \N{WAVING HAND SIGN} "
                f"My prefix in this server is `{prfx}`"
            )


@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Bot error handler"""

    if getattr(ctx, "error_handled", False):
        return  # Check if error already handled

    # Setup response embed
    aidzman = bot.get_user(bot.owner_id)
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
        e.title, e.description = "Incorrect use of command", str(error)
        e.add_field(
            name="The correct usage is",
            value=f"```{ctx.prefix}{ctx.command} {ctx.command.signature}```",
        )
        await ctx.send(embed=e)
    elif isinstance(error, commands.DisabledCommand):
        e = Embed(colour=0xFB8F02)
        e.set_author(name="Disabled command", icon_url="https://bit.ly/2JHJ91I")
        if ctx.author.id == bot.owner_id:
            e.description = "Bypassing disable.."
            msg = await ctx.send(embed=e)

            ctx.command.enabled = True
            await ctx.invoke(ctx.command)
            ctx.command.enabled = False

            e.description += " Done\nRe-disabling command"
            await msg.edit(embed=e, delete_after=5)
        else:
            e.timestamp = dt.utcnow()
            e.set_footer(text=f"Run by {ctx.author}", icon_url=ctx.author.avatar_url)
            e.description = "This command has been disabled. Please wait while it is being fixed \N{HAMMER AND WRENCH}"
            await ctx.send(embed=e)
    elif isinstance(error, commands.NoPrivateMessage):
        e.title, e.description = (
            "Error while performing command",
            "This command cannot be used in DM",
        )
        await ctx.send(embed=e)
    elif isinstance(error, commands.CommandOnCooldown):
        e.title = "This command is on cooldown!"
        e.description = "Please try again in "+naturaltime(dt.utcnow()+td(seconds=error.retry_after), future=True)
        await ctx.send(embed=e)
    elif isinstance(error, commands.MissingPermissions):
        perms = [f"`{p.replace('_', ' ').capitalize()}`" for p in error.missing_perms]
        e.title = "You're missing permissions!"
        e.description = f"You can't run this command :angry: Come back when you have the following permissions:\n{', '.join(perms)}"
        await ctx.send(embed=e)
    elif isinstance(error, commands.BotMissingPermissions):
        if "send_messages" in error.missing_perms:
            return  # Can't send a message saying the bot can't send messages ;(
        perms = [f"`{p.replace('_', ' ').capitalize()}`" for p in error.missing_perms]
        e.title = "I'm missing permissions!"
        e.description = f"I need the following permissions to execute this command:\n{', '.join(perms)}"
        await ctx.send(embed=e)

    # Other errors
    elif isinstance(error.original, HTTPException) and (
        "or fewer in length" in str(error.original)
    ):
        # TODO: This needs to be fixed
        e.title, e.description = (
            "Error executing command",
            "Too many characters to send reply \N{SHRUG}",
        )
        await ctx.send(embed=e)
    else:
        format_error = lambda error: "\n".join(
            format_exception(type(error), error, error.__traceback__, 10)
        )
        error_code = f"`{error.original.__class__.__name__}//{int(time())}`"
        hashtag = "#" if ctx.guild else ""
        bot.logger.error(format_error(error))
        # I know, it really is the best way to document errors ;)

        e.color, e.description = (0xFB8F02, f"```py\n{format_error(error.original)}```")
        e.set_author(name="An error occoured", icon_url="https://bit.ly/2JHJ91I")
        e.add_field(name="User", value=f"{ctx.author}\n{ctx.author.id}")
        e.add_field(name="Error code", value=error_code)

        if ctx.guild:
            e.add_field(name="Guild", value=ctx.guild.name)
        e.add_field(name="Channel", value=f"{hashtag}{ctx.channel}")

        if ctx.author == aidzman:
            return await ctx.send(embed=e)

        webhook = Webhook.from_url(
            bot.env["ERROR_WEBHOOK_URL"], adapter=AsyncWebhookAdapter(bot.session)
        )
        await webhook.send(
            embed=e, username=bot.user.name, avatar_url=bot.user.avatar_url
        )

        em = Embed(
            color=0xFFA500,
            timestamp=dt.utcnow(),
            title="💣 Oof, an error occoured 💥",
            description=f"Please [join the support guild]({bot.guild_invite_url}) and tell **{aidzman}** what happened to help fix this bug.\n\nError code: {error_code}",
        )

        em.set_footer(text=f"< Look for this guy!", icon_url=aidzman.avatar_url)
        await ctx.send(embed=em)


# Finally start the app!
if __name__ == "__main__":
    loop = bot.loop
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

    # Suppress those useless warnings
    filterwarnings("ignore", category=EmptyResponseWarning)

    # Setup the website
    site.add_routes(web_routes)
    site.router.add_static("/static", "./website/static")
    site.on_startup.append(web_get_cmd_data)
    env = jinja_env(site)
    env.globals.update(bot=bot, db=bot.db, app=site)
    env.globals.update(**{i.__name__:i for i in [
        randint, reversed, len, range, list, dict,
    ]})

    # Run the website
    site.logger.debug("Creating runner")
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
    site.logger.info("Closing asyncio loop")
    loop.close()
