import os
from functools import wraps

import markdown
from flask import Flask, redirect, render_template, request, session, url_for

from kpffl import addCoachesPollVote, getCoachesPoll
from sleeper import getStandings, getTeams, verifyOwner

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY") or b"\xc2\xb2\xe1\x9d\xafM\xe4\xf7\rn\xfej\xb1\xc5'\xbf"

@app.route("/login", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        session["user_id"] = verifyOwner(request.form["email"], request.form["password"])
        return redirect(url_for("home"))
    return render_template("sync.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home.html"))


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/rules")
def rules():
    with open("docs/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        # add link to edit if logged in
        if session.get("user_id"):
            firstLine = html.split("\n")[0]
            html = html.replace(
                firstLine, firstLine +
                f"<a href=\"{r'https://github.com/redreceipt/kpffl/edit/master/docs/rules.md'}\">(Edit)</a>"
            )
        return render_template("rules.html", html=html)


@app.route("/teams")
def teams():
    return render_template("teams.html", teams=getTeams())


@app.route("/rankings", methods=['POST', 'GET'])
def rankings():

    rankings = {"standings": getStandings(), "cp": getCoachesPoll()}
    if request.method == "POST" and session.get("profile"):
        # validate form
        if set([int(teamID)
                for teamID in request.form.values()]) != set(range(1, 13)):
            error = "Number teams 1-12"
            return render_template("rankings.html",
                                   rankings=rankings,
                                   voting=True,
                                   error=error)
        else:
            # submit votes
            addCoachesPollVote(request.form, session["user_id"])

    voting = request.args.get("voting") == "true" and session.get("profile")
    return render_template("rankings.html", rankings=rankings, voting=voting)


