from logging import getLogger

from aiohttp import ClientSession, web
from aiohttp_jinja2 import template, render_template, get_env as jinja_env
from aiohttp_session import get_session, new_session

# Create objects
OAUTH_SCOPE = "identify guilds"
routes = web.RouteTableDef()
logger = getLogger("web")

# Ensure logged in
def login_required(fn):
    async def wrapped(request: web.Request, *args, **kwargs):
        if "user_id" not in await get_session(request):
            return web.HTTPFound(request.app.oauth_url)
        return await fn(request, *args, **kwargs)
    return wrapped


# Navbar main routes
@routes.get("/")
@template("index.jinja")
async def index(request: web.Request):
    return dict()


@routes.get("/about")
@template("about.jinja")
async def about(request: web.Request):
    return dict()


@routes.get("/cmds")
@template("cmds.jinja")
async def cmds(request: web.Request):
    numcmds = sum([len(cmds) for cog, cmds in request.app.cmddata.items()])
    numcogs = len(request.app.cmddata.keys())
    return dict(data=request.app.cmddata, numcmds=numcmds, numcogs=numcogs)


# Navbar star routes
@routes.get("/invite")
async def invite(request: web.Request):
    """Handles all the bot invite routes"""
    p = request.query.get("p")

    if p == "select":
        url = request.app["bot"].invite_url(-1)
    elif p == "none":
        url = request.app["bot"].invite_url(0)
    else:
        url = request.app["bot"].invite_url()
    return web.HTTPFound(url)


@routes.get("/login")
async def login(request: web.Request):
    """The pretty hecking complicated route to log in with
    Discord. This will also fetch user data and guild data
    so the user can get their stats & edit guild settings"""
    # Get the code
    code = request.query.get("code")
    if not code:
        return web.HTTPFound(request.app.oauth_url)

    # Generate the post data
    data = {"grant_type": "authorization_code", "code": code, "scope": OAUTH_SCOPE}
    data.update(request.app.oauth_data)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # Make the request
    async with ClientSession(loop=request.loop) as session:
        # Get auth
        token_url = "https://discordapp.com/api/v6/oauth2/token"
        async with session.post(token_url, data=data, headers=headers) as r:
            token = await r.json()
            if r.status == 400:
                return web.HTTPFound("/")
            if token["scope"] != OAUTH_SCOPE:
                return web.Response(text="Missing required scopes. Please re-authenticate")
            headers["Authorization"] = f"{token['token_type']} {token['access_token']}"

        # Get user
        user_url = "https://discordapp.com/api/v6/users/@me"
        async with session.get(user_url, headers=headers) as r:
            user_info = await r.json()

        # Get guilds
        guilds_url = f"https://discordapp.com/api/v6/users/@me/guilds"
        async with session.get(guilds_url, headers=headers) as r:
            guild_info = await r.json()

    # Wipe the old session
    sess = await new_session(request)
    username = f"{user_info['username']}#{user_info['discriminator']}"
    request.app.logger.debug(f"New connection: {username!r} ({user_info['id']})")

    # Delete unneeded user info + save
    [user_info.pop(i) for i in "flags locale mfa_enabled".split()]
    user_info["id"] = int(user_info["id"])
    user_info["avatar"] = get_avatar(user_info)
    sess["user_id"] = user_info["id"]
    sess["user_info"] = user_info

    # Delete unneeded guild info + save
    for guild in guild_info:
        guild["admin"] = guild.pop("owner") or guild["permissions"] & 40 > 0
        guild.pop("permissions")
        guild.pop("features")
    sess["guild_info"] = [g for g in guild_info if g.pop("admin")]

    # Redirect to home
    return web.HTTPFound("/")


@routes.get("/logout")
async def logout(request: web.Request):
    """Unlike the login route, this is pretty simple"""
    sess = await get_session(request)
    sess.invalidate()
    return web.HTTPFound("/")


# Other routes
@routes.get("/leaderboard")
@template("leaderboard.jinja")
async def leaderboard(request: web.Request):
    q = request.query.get("guild", "")
    id_ = int(q) if q.isdigit() else ""
    guild = request.app["bot"].get_guild(id_)
    initlbdata = await request.app["db"].get_leaderboard(guild, 100)
    lbdata = {user:f"{amount:,}" for user,amount in initlbdata.items()}
    return dict(guild=guild, data=lbdata)


@routes.get("/guildpicker")
@template("guildpicker.jinja")
@login_required
async def picker(request: web.Request):
    sess = await get_session(request)
    guilds = sess.get("guild_info", list())
    guildids = [str(g.id) for g in request.app["bot"].guilds]
    return dict(guilds=guilds, guildids=guildids)


@routes.get("/user/{userid}")
async def userroute(request: web.Request):
    # TODO: Should I make or delete this?
    return web.Response(text="hi")


@routes.get("/guildsettings")
async def guildsettings_redirect(request: web.Request):
    return web.HTTPFound("/guildpicker")

@routes.get("/guildsettings/{guildid}")
@template("guildsettings.jinja")
@login_required
async def guildsettings_frontend(request: web.Request):
    sess = await get_session(request)
    guildid = request.match_info["guildid"]
    if not guildid.isdigit():
        return web.json_response(dict(message="Bad guild ID", status=400), status=400)
    
    bot = request.app["bot"]
    db = request.app["db"]
    guild = bot.get_guild(int(guildid))
    botguilds = [g.id for g in bot.guilds]
    guilds = [g["id"] for g in sess["guild_info"] if int(g["id"]) in botguilds]
    if guildid not in guilds:
        return web.HTTPFound("/guildpicker")
    
    get_role_colour = lambda role: "#%02x%02x%02x"%role.color.to_rgb() if role.colour.value else "#B9BBBE"
    guild = bot.get_guild(int(guildid))
    prefix = await db.get_guild_prefix(guild.id) or ""
    serverip = await db.get_minecraft_server(guild.id) or ""
    mcrole = guild.get_role(await db.get_minecraft_role(guild.id))
    return dict(
        guild=guild, prefix=prefix,
        serverip=serverip, mcrole=mcrole,
        get_role_colour=get_role_colour,
        saved="saved" in request.query
    )

@routes.post("/guildsettings/{guildid}")
@login_required
async def guildsettings_backend(request: web.Request):
    sess = await get_session(request)
    guildid = request.match_info["guildid"]
    if not guildid.isdigit():
        return web.json_response(dict(message="Bad guild ID", status=400), status=400)
    
    bot = request.app["bot"]
    db = request.app["db"]
    data = await request.post()
    guild = bot.get_guild(int(guildid))
    botguilds = [g.id for g in bot.guilds]
    guilds = [g["id"] for g in sess["guild_info"] if int(g["id"]) in botguilds]
    if guildid not in guilds:
        return web.HTTPFound("/guildpicker")
    
    oldprefix = await db.get_guild_prefix(guild.id) or ""
    oldserverip = await db.get_minecraft_server(guild.id) or ""
    oldminecraftrole = await db.get_minecraft_role(guild.id) or ""

    prefix = data.get("prefix")
    serverip = data.get("serverip")
    minecraftrole = data.get("minecraftrole")
    if prefix != oldprefix and prefix != None:
        await db.set_guild_prefix(guild.id, prefix)
    if serverip != oldserverip and serverip != None:
        await db.set_minecraft_server(guild.id, serverip)
    if minecraftrole != str(oldminecraftrole) and minecraftrole != None:
        await db.set_minecraft_role(guild.id, minecraftrole or None)
    return web.HTTPFound(f"/guildsettings/{guildid}?saved")

@routes.get("/support")
async def support(request: web.Request):
    return web.HTTPFound(request.app["bot"].guild_invite_url)


# Middlewares
@web.middleware
async def mw_not_found(request, handler):
    """A custom 404 status page"""
    try:
        response = await handler(request)
        if response.status != 404:
            return response
    except web.HTTPException as ex:
        if ex.status != 404:
            raise
    return render_template("_base.jinja", request, {})

@web.middleware
async def mw_update_globals(request, handler):
    """Each request, automatically update the jinja
    global variables `request` and `session`"""
    env = jinja_env(request.app)
    sess = await get_session(request)
    env.globals.update(request=request, session=sess)
    return await handler(request)

@web.middleware
async def mw_bot_ready(request, handler):
    """Wait until the bot is ready before dispatching
    the first request. Some of the website stuff
    depends on the bot's internal cache being ready"""
    if not request.app["bot"].is_ready():
        return web.HTTPClientError(text="Error 425 Website is still booting up\nPlease try again in about 30 seconds")
    return await handler(request)

# TODO: The 404 page no longer works scam
middlewares = [mw_bot_ready, mw_update_globals]

# Other functions
async def web_get_cmd_data(app: web.Application):
    """Gets the command data from the bot\n
    This should be added as an `on_startup` signal"""
    cmds = sorted(app["bot"].commands, key=lambda cmd: cmd.cog_name)
    cmds = sorted(cmds, key=lambda i:app["bot"].cog_load_order.index(i.cog))
    cmds = [cmd for cmd in cmds if cmd.enabled and not cmd.hidden and cmd.name != "jishaku"]
    cmds = [cmd for cmd in cmds if "is_owner" not in [chk.__qualname__.split(".")[0] for chk in cmd.checks]]

    data = {cog.qualified_name: list() for cog in app["bot"].cog_load_order}
    [data[cmd.cog.qualified_name].append(cmd) for cmd in cmds]
    for cog in data.copy():
        if data[cog] == list():
            del data[cog]
    app.cmddata = data


def get_avatar(user_info: dict = {}):
    """Returns the avatar URL of the user"""
    try: return f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}.png"
    except KeyError:
        try: return f"https://cdn.discordapp.com/embed/avatars/{int(user_info['discriminator'])%5}.png"
        except KeyError: pass
    return "https://cdn.discordapp.com/embed/avatars/0.png"
