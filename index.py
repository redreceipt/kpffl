import os

import markdown
from flask import Flask, redirect, render_template

from sleeper import getLeague, getStandings, getTeams

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/rules")
def rules():
    with open("docs/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        return render_template("rules.html", html=html)


@app.route("/teams")
def teams():
    return render_template("teams.html", teams=getTeams())


@app.route("/rankings")
def rankings():
    return render_template("rankings.html",
                           league=getLeague(),
                           rankings={"standings": getStandings()})


@app.route('/meet')
def meet():
    return redirect(os.getenv("GOOGLE_MEET_URI"), code=301)


@app.route('/chat')
def chat():
    return redirect(os.getenv("DISCORD_URI"), code=301)
