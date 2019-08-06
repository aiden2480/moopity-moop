"""Ok, well I guess I'm just a tram"""
from asyncio import sleep
from json import loads
from logging import getLogger, FileHandler, Formatter, DEBUG
from traceback import format_exception

# Functions
def setup_custom_logger(loggerName, filename, level= DEBUG, lineformat= "%(asctime)s: %(levelname)s:\t%(name)s:\t%(message)s"):
    """Returns a logger based on input name"""
    logger = getLogger(loggerName)
    logger.setLevel(level)
    handler = FileHandler(filename= f"cogs/assets/logs/{filename}", encoding= "utf-8", mode= "w")
    handler.setFormatter(Formatter(lineformat))
    logger.addHandler(handler)
    return logger

async def check_server_status(bot):
    """Check MY minecraft server status, I get special privileges ok?"""
    
    await bot.wait_until_ready()
    me = bot.get_guild(553071847483375626).me
    url = "https://api.minetools.eu/ping/moopitymoop.aternos.me"
    lastCheckStatus = None
    logger = setup_custom_logger("serverstatus", "server.log", lineformat= "%(asctime)s: %(message)s")

    while True:
        resp = await bot.sess.get(url)
        data = loads(await resp.read())
        
        try:
            if "this server is offline" in data.get("description").lower():
                result = "OFFLINE"
                lastCheckStatus = False
            else:
                ping = round(data['latency'], 1)
                online = data['players']['online']
                maxp = data['players']['max']
                result = f"{online}/{maxp} players - {ping}ms ping"
                lastCheckStatus = True
        except:
            result = "OFFLINE"
            lastCheckStatus = False
        
        # Small function to increase the ping check time if the server is offline
        if bool(lastCheckStatus) == True: waitTime = 90
        else: waitTime = 300

        print(f"Server status: {result} - Wait time: {waitTime}")
 
        if lastCheckStatus:
            logger.info(f"true:\t{waitTime} - {result}")
        else:
            logger.info(f"false:\t{waitTime}")

        await me.edit(nick= result)
        await sleep(waitTime)
