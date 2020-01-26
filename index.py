import markdown
from flask import Flask, redirect, render_template

from sleeper import getTeams

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


@app.route('/chat')
def chat():
    return redirect("https://meet.google.com/igd-oqkc-thg", code=301)
