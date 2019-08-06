# Importing
from argparse import ArgumentParser
from aiohttp import ClientSession
from datetime import datetime as dt
from dotenv import load_dotenv
from logging import (
    FileHandler, Formatter,
    DEBUG, getLogger
)
from os import path
from random import choice
from time import time
from traceback import format_exception

from cogs.assets import keepalive, database, custombot
from discord import (
    Embed, Status, Activity, Game, Message,
    Webhook, AsyncWebhookAdapter, Colour)
from discord.ext.commands import (
    Context, NotOwner, CommandNotFound,
    MissingRequiredArgument, BadArgument,
    TooManyArguments, UserInputError,
    DisabledCommand, NoPrivateMessage,
    CommandOnCooldown, MissingPermissions,
    BotMissingPermissions,
)

# Setup argument parsing
parser = ArgumentParser(description= "Options for starting up Moopity Moop")
parser.add_argument("--nobot", action= "store_true", default= False, help= "Start the website but not the bot")
parser.add_argument("--noweb", action= "store_true", default= False, help= "Start the bot with no additional web server")
parser.add_argument("--prefix", default= None, help= "Override the bot prefix temporarily with a new one")
args = parser.parse_args()

# Setup bot
bot = custombot.CustomBot(
    command_prefix= args.prefix or database.get_prefix,
    description= "A small bot with commands to utilise your Minecraft/Discord experience" or "A discord bot featuring commands for popular minecraft servers & more!",
    owner_id= 272967064531238912,
    status= Status.idle,
    activity= Activity(type= 2, name= "Windows XP startup sounds"),
    case_insensitive= True,
)

# Set up logging
handler = lambda filename: FileHandler(filename= f"cogs/assets/logs/{filename}.log", encoding= "utf-8", mode= "w")

logger = getLogger("moopitymoop")
logger.setLevel(DEBUG)
h = handler("moopitymoop")
h.setFormatter(Formatter("%(asctime)s: %(levelname)s:\t%(name)s:\t%(message)s"))
logger.addHandler(h)

w = getLogger("werkzeug")
w.setLevel(DEBUG)
h = handler("website")
h.setFormatter(Formatter("%(asctime)s: %(levelname)s:\t%(name)s:\t%(message)s"))
w.addHandler(h)

d = getLogger("discord")
d.setLevel(DEBUG)
h = handler("discord")
h.setFormatter(Formatter("%(asctime)s: %(levelname)s:\t%(name)s:\t%(message)s"))
d.addHandler(h)

# Setup environment variables
load_dotenv(path.join(path.dirname(__file__), ".env"))

# Bot Events
@bot.event
async def on_ready():
    """Async setup function for the bot"""
    if hasattr(bot, "ready_time"):
        return
    bot.ready_time = dt.utcnow()
    
    print("Discord ready: {0.name} ({0.id})".format(bot.user))
    await bot.change_presence(activity= Game(name= choice((
        "Ethan has mega gay",
        f"{bot.default_prefix}help for commands!",
        "moopitymoop.aternos.me",
        f"{bot.default_prefix}info for info!",
        f"created by {bot.get_user(bot.owner_id)}",
    ))))

    # Create our tasks
    #bot.loop.create_task(util.check_server_status(bot))

    # Announce our presence to the whole wide world
    async with ClientSession(loop= bot.loop) as http:
        webhook = Webhook.from_url(bot.env("COMMANDS_WEBHOOK_URL"), adapter= AsyncWebhookAdapter(http))
        e = Embed(colour= 0x00b7d9, timestamp= dt.utcnow(), description= f"Time taken to load: `{bot.get_uptime()}`")

        e.set_footer(text= bot.user)
        e.set_author(name= "Bot restarted", icon_url= "https://bit.ly/2Sd33Wx")

        await webhook.send(embed= e, username= bot.user.name, avatar_url= bot.user.avatar_url)

@bot.event
async def on_connect():
    t = dt.now()
    print(f"Bot reconnected at {t.hour}:{t.minute}:{t.second}.")
    await bot.change_presence(status= Status.online, afk= False)

@bot.event
async def on_disconnect():
    t = dt.now()
    print(f"Bot disconnected at {t.hour}:{t.minute}:{t.second}.")
    await bot.change_presence(status= Status.idle, afk= True, activity= Game(name= "disconnected.. Massive F 😟"))

@bot.event
async def on_message(m: Message):
    if m.author.bot:
        return

    await bot.wait_until_ready()
    await bot.process_commands(m)

@bot.event
async def on_command_error(ctx: Context, error):
    """Bot error handler"""
    
    if getattr(ctx, "error_handled", False):
        return  # Check if error already handled
    
    # Setup response embed
    aidzman = bot.get_user(bot.owner_id)
    e = Embed(colour= Colour.blue(), timestamp=dt.utcnow())
    e.set_footer(text=bot.user, icon_url=bot.user.avatar_url)
    
    # Error groups
    ignored_errors = (NotOwner, CommandNotFound)
    param_errors = (
        MissingRequiredArgument,
        BadArgument,
        TooManyArguments,
        UserInputError,
    )
    
    # Command errors
    if isinstance(error, ignored_errors):
        pass
    elif isinstance(error, param_errors):
        e.title, e.description = "Incorrect use of command", str(error)
        e.add_field(name="The correct usage is", value=f"```{ctx.prefix}{ctx.command} {ctx.command.signature}```")
        await ctx.send(embed= e)
    elif isinstance(error, DisabledCommand):
        if ctx.author.id == bot.owner_id:
            ctx.command.enabled = True
            try:
                await ctx.reinvoke()
            except Exception as e:
                await ctx.send(f"```py\n{e}```")
            ctx.command.enabled = False
        else:
            pass  # Don't do anything for a normal user
    elif isinstance(error, NoPrivateMessage):
        e.title, e.description = (
            "Error while performing command",
            "This command cannot be used in DM",
        )
        await ctx.send(embed=e)
    elif isinstance(error, CommandOnCooldown):
        e.title, e.description = (
            "This command is on cooldown!",
            f"Please try again in {round(error.retry_after)} seconds",
        )
        await ctx.send(embed=e)
    elif isinstance(error, MissingPermissions):
        perms = [
            "`" + p.replace("_", " ").capitalize() + "`" for p in error.missing_perms
        ]
        e.title, e.description = (
            "You're missing permissions!",
            "Don't you try to bullshit me :angry: Come back when you have the following permissions:\n{0}".format(
                ", ".join(perms)
            ),
        )
        await ctx.send(embed=e)
    elif isinstance(error, BotMissingPermissions):
        if "send_messages" in error.missing_perms:
            return  # Can't send a message saying the bot can't send messages ;(
        perms = [
            "`" + p.replace("_", " ").capitalize() + "`" for p in error.missing_perms
        ]
        e.title, e.description = (
            "I'm missing permissions!",
            "I need the following permissions to execute this command:\n{0}".format(
                ", ".join(perms)
            ),
        )
        await ctx.send(embed=e)
    # Not a command error
    elif "Must be 2000 or fewer in length" in str(error) or "Must be 2048 or fewer in length" in str(error):
        e.title, e.description = (
            "Error executing command",
            "Too many characters to send reply 🤷",
        )
        await ctx.send(embed=e)
    else:
        format_error = lambda error: "\n".join(format_exception(type(error), error, error.__traceback__, 10))
        error_code, hashtag= f"`{error.original.__class__.__name__}//{int(time())}`", ""
        # I know, it really is the best way to document errors ;)

        e.color, e.description = (
            0xfb8f02,
            f"```py\n{format_error(error)}```")
        e.set_author(name= "An error occoured", icon_url= "https://bit.ly/2JHJ91I")
        e.add_field(name= "User", value= f"{ctx.author}\n{ctx.author.id}")
        e.add_field(name= "Error code", value= error_code)
        
        if ctx.guild:
            hashtag= "#"
            e.add_field(name= "Guild", value= ctx.guild.name)
        e.add_field(name= "Channel", value= f"{hashtag}{ctx.channel}")

        if ctx.author == aidzman:
            return await ctx.send(embed= e)

        async with ClientSession(loop= bot.loop) as http:
            webhook = Webhook.from_url(bot.env("ERROR_WEBHOOK_URL"), adapter= AsyncWebhookAdapter(http))
            await webhook.send(embed= e, username= bot.user.name, avatar_url= bot.user.avatar_url)

        em = Embed(
            color= 0xFFA500,
            timestamp= dt.utcnow(),
            title= "💣 Oof, an error occoured 💥",
            description= f"Please [join the support guild]({bot.guild_invite_url}) and tell **{aidzman}** what happened to help fix this bug.\n\nError code: {error_code}")
        
        em.set_footer(text= f"< Look for this guy!", icon_url= aidzman.avatar_url)
        await ctx.send(embed= em)

        
# Finally start the app!
if __name__ == "__main__":
    for cog in [
        "general", "minecraft", "config",
        "developer", "hidden", "fun",
        "currency",

        # Extra cogs
        "assets.events",
        "assets.periodic",
    ]: bot.load_extension(f"cogs.{cog}")
    bot.load_extension("jishaku")

    loop = bot.loop
    web = keepalive.app
    web.bot = bot
    use_web, use_bot= not args.noweb, not args.nobot
    
    # Run the bot
    try:
        if use_web:
            logger.warning("Running the website")
            web.start()
        if use_bot:
            logger.warning("Running the bot")
            bot.run()
        pass
    except KeyboardInterrupt:
        # Save + Close
        print("Beginning termination process")
        web.terminate()
        loop.close()
        exit()
