import os

import markdown
from flask import Flask, redirect, render_template, request, session, url_for

from kpffl import addCoachesPollVote, getCoachesPoll, sendProposal
from sleeper import getTeams, verifyOwner

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")


@app.route("/login", methods=["POST", "GET"])
def login():

    if request.method == "POST":
        session["user_id"] = verifyOwner(
            request.form["email"], request.form["password"]
        )
        if not session["user_id"]:
            print("hello")
            return render_template("login.html", error=True)
        if session.get("voting"):
            session["voting"] = False
            return redirect(url_for("rankings", subpath="vote"))
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


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
                firstLine,
                firstLine
                + f"<a class=\"btn btn-default\" href=\"{url_for('proposal')}\" role=\"button\">Submit Proposal</a>"
                # f"<small><a href=\"{r'https://github.com/redreceipt/kpffl/edit/master/docs/rules.md'}\">(Edit)</a></small>"
            )
        return render_template("rules.html", html=html)


@app.route("/proposal", methods=["GET", "POST"])
def proposal():
    if request.method == "POST":
        sendProposal(request.form)
        return redirect(url_for("rules"))
    return render_template("proposal.html")


@app.route("/teams")
def teams():
    return render_template("teams.html", teams=getTeams())


@app.route("/rankings")
@app.route("/rankings/<path:subpath>", methods=["GET", "POST"])
def rankings(subpath=None):

    voting = subpath == "vote"

    # submit votes and refresh the page
    if request.method == "POST":
        # convert vote form into an array
        votes = [field for field in request.form]
        addCoachesPollVote(votes, session["user_id"])
        return redirect(url_for("rankings"))

    # redirect to login if they want to vote
    if voting and not session.get("user_id"):
        session["voting"] = True
        return redirect(url_for("login"))

    return render_template(
        "rankings.html", rankings={"cp": getCoachesPoll()}, voting=voting
    )


@app.route("/chat")
def chat():
    return redirect(os.getenv("CHAT_URL"), code=301)


@app.route("/video")
def video():
    return redirect(os.getenv("VIDEO_URL"), code=301)


@app.route("/league")
def league():
    return redirect(os.getenv("LEAGUE_URL"), code=301)
