from asyncio import sleep
from discord.ext.commands import Cog, Bot
from json import loads

# Create the tasks dictionary
TASKS = dict()
# Fmt: {fcn: time} ie {check_server_status: 300}
TASK_ASSETS = dict(server= dict(time= None))
# Another dictionary to hold task assets

async def check_server_status(bot: Bot):
    """Check MY minecraft server status, I get special privileges ok?\n
    Wait time: 
    """
    
    global TASK_ASSETS
    await bot.wait_until_ready()
    me = bot.get_guild(553071847483375626).me
    url = "https://api.minetools.eu/ping/moopitymoop.aternos.me"
    TASK_ASSETS["server"]["time"] = None

    while True:
        resp = await bot.sess.get(url)
        data = loads(await resp.read())
        
        try:
            if "this server is offline" in data.get("description").lower():
                result = "OFFLINE"
                TASK_ASSETS["server"]["time"] = False
            else:
                ping = round(data['latency'], 1)
                online = data['players']['online']
                maxp = data['players']['max']
                result = f"{online}/{maxp} players - {ping}ms ping"
                TASK_ASSETS["server"]["time"] = True
        except:
            result = "OFFLINE"
            TASK_ASSETS["server"]["time"] = False
        
        # Small function to increase the ping check time if the server is offline
        if bool(TASK_ASSETS["server"]["time"]) == True: waitTime = 90
        else: waitTime = 300

        print(f"Server status: {result} - Wait time: {waitTime}")
 
        await me.edit(nick= result)
        await sleep(waitTime)

def setup(bot: Bot):
    global TASKS
    

    for task in TASKS:
        bot.loop.create_task()

def teardown(bot):
    print("periodic cog removed")