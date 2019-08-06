from flask import Flask, render_template, redirect, request, jsonify
from multiprocessing import Process
from random import randint
from time import time

from cogs.assets import database

# Setup flask
app = Flask("Moopity Moop",
    template_folder= "website/templates",
    static_folder= "website/static")
app.secret_key = b"this is big good secret key ;)"

# Main Routes
@app.route("/")
def index():
    start = time()
    with database.Database() as db:
        servers = db("SELECT * FROM MinecraftServers").fetchall()
        prefixes = db("SELECT * FROM GuildPrefixes").fetchall()
        return render_template("index.jinja",
            res= (servers, prefixes),
            time= time,
            start= start
        )

@app.route("/info")
def info():
    return render_template("info.jinja")

@app.route("/stats")
def stats():
    return render_template("stats.jinja")

@app.route("/cmds")
def cmds():
    return render_template("cmds.jinja")

@app.route("/links")
def links():
    return render_template("links.jinja")

# Star routes
@app.route("/invite")
def inviteindex():
    """Handles all the bot invite routes"""
    p = request.values.get("p")

    if p == "default":
        return redirect("default")
    elif p == "select":
        return redirect("select")
    elif p == "none":
        return redirect("none")
    else: # Invalid or not provided
        return render_template("invite.jinja")


# Other routes
#@app.route("/guildsettings/<guildid>")
def settings(guildid=None):
    return str(guildid)
    g = request.values.get("g", None)
    
    if g is None:
        return "you didn't provide 'g'!"
    else:
        return str(g)

@app.route("/pingo")
def ping():
    """This is the route that is pinged by https://uptimerobot.com,
    I created it to distinguish between normal traffic and pinging traffic"""
    return jsonify(message= "Yayeet the bot is online! (Or at least the website is)")

@app.errorhandler(404)
def thispageexistnt(e):
    return render_template("_base.jinja"), 404

# Create some global variables
app.jinja_env.globals["randint"] = randint
app.jinja_env.globals["db"] = database.Database

# Code to run the webserver
def k():
    app.run(host= "0.0.0.0", port= 0000)
def start_server(*args, **kwargs) -> "Start the server":
    """Start the website script for the bot"""
    
    app._thread = Process(
        name= "website",
        target= k
    ).start()
def terminate_server(*args, **kwargs) -> "Shutdown the server":
    """Terminate the thread that is running
    the server and, in turn, close the webserver"""
    
    app._thread.terminate()
    app._thread.join()

app.start = start_server
app.terminate = terminate_server
