from sqlite3 import connect

from discord import Message
from discord.ext.commands import Bot, when_mentioned_or

# Main database class
class Database(object):
    """Database interaction for the bot"""

    # Inbuilt methods
    def __init__(self, databaseLocation= "cogs/assets/database.db"):
        self.databaseLocation = databaseLocation
    
    def __enter__(self):
        self.conn = connect(self.databaseLocation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        del self

    def __call__(self, query, **context):
        c = self.conn.cursor()
        try:
            result = c.execute(query.format(**context))
            self.conn.commit()
        except Exception as e:
            result = e
        return result
    
    # Custom methods
    def set_prefix(self, guildID: int, prefix: str):
        p= self(f"SELECT * FROM GuildPrefixes WHERE guildID={guildID}").fetchone()
        if p: # Prefix has already been set and must be UPDATEd
            return self(f"UPDATE GuildPrefixes SET prefix='{prefix}' WHERE guildID={guildID}")
        else: # Can just INSERT the new prefix
            return self(f"INSERT INTO GuildPrefixes VALUES ({guildID}, '{prefix}')")

    def get_guild_minecraft_server(self, guildID: int):
        return self(f"SELECT * FROM MinecraftServers WHERE guildID={guildID}")
    
    def set_guild_minecraft_server(self, guildID: int, serverIP: str or None):
        if serverIP is None:
            return self(f"DELETE FROM MinecraftServers WHERE guildID={guildID}")
        p= self(f"SELECT * FROM MinecraftServers WHERE guildID={guildID}").fetchone()
        if p: # Server has already been set and must be UPDATEd
            return self(f"UPDATE MinecraftServers SET serverIP='{serverIP}' WHERE guildID={guildID}")
        else: # Can just INSERT the new server
            return self(f"INSERT INTO MinecraftServers VALUES ({guildID}, '{serverIP}')")

# Custom prefix for the bot
def get_prefix(bot: Bot, msg: Message):
    """Get the prefix for the bot using
    the database-stored prefix if avaliable"""
    prefixes= ["m!", "M!"] # Default prefix
    if bot.user.id == 598659752775385111:
        # Beta bot
        prefixes= ["-"]
        # Beta bot doesn't have any database functionality

    if msg.guild:
        with Database() as db:
            result = db(f"SELECT * FROM GuildPrefixes WHERE guildID={msg.guild.id}").fetchone()
            if result:
                prefixes = [result[1]]
    else:
        prefixes.append("")
    return when_mentioned_or(*prefixes)(bot, msg)

if __name__ == "__main__":
    with Database("database.db") as db:
        db("INSERT INTO GuildPrefixes VALUES (553071847483375626, 'baka')")
