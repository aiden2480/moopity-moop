from aiohttp.web import RouteTableDef, Request, json_response
from discord import Embed, Colour

routes = RouteTableDef()

# API routes
@routes.get("/api/shieldsio")
async def shieldsio(request: Request):
    """Returns the guildcount in https://shields.io format"""
    count=len(request.app["bot"].guilds)
    return json_response(dict(
        color="#3498DB",
        label="server count",
        message=f"{count} unique",
        schemaVersion=1,
    ))

@routes.get("/api/guildcount")
async def guildcount(request: Request):
    return json_response(dict(
        count=len(request.app["bot"].guilds)
    ))


# Bot list webhooks
@routes.post("/webhook/divinediscordbotscom")
async def divinediscordbotscom(request: Request):
    if request.headers["Authorization"] != request.app["bot"].env["DIVINE_DISCORD_BOTS_COM"]:
        return json_response(dict(message="Invalid authentication token", status=403)) 
    
    db = request.app["db"]
    bot = request.app["bot"]
    data = await request.json()
    user = await bot.fetch_user(int(data["user"]["id"]))
    await db.add_user_money(user.id, 40)
    bal = await db.get_user_money(user.id)

    embed = Embed(
        colour=Colour.blue(), title=f"{bot.emoji.spinningminecraft} Thanks for upvoting!",
        description=f"Have a free **25 {bot.ingot}** and **3 {bot.emoji.goldingot}**\nYour balance is now **{bal} {bot.ingot}**"
    )
    embed.set_footer(text=bot.user, icon_url=bot.user.avatar_url)
    
    try: await user.send(embed=embed)
    except: pass
    return json_response(dict(message="Upvote recieved"))
