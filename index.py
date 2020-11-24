import os

import markdown
from flask import (Flask, abort, redirect, render_template, request, session,
                   url_for)

from database import getDB
from kpffl import (addCoachesPollVote, addProposalVote, getProposal,
                   getRankings, sendEmail)
from sleeper import (addTradeVote, deleteTradeVotes, getMatchups, getOwner,
                     getTeams, getTrades)
from sportsdata import getTimeframe

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")


@app.route("/login", methods=["POST", "GET"])
def login():
    src = request.args.get("src") or request.form.get("src")

    # if logging in
    if request.method == "POST":
        session["user_id"] = getOwner(request.form["email"], request.form["password"])
        if not session["user_id"]:
            return render_template("login.html", error=True, src=src)
        session["email"] = request.form["email"]
        return redirect(src or url_for("home"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/", methods=["POST", "GET"])
def home():

    if request.method == "POST":
        # delete old votes
        all_txns = set(
            [
                vote.split("-")[0]
                for vote in request.form
                if vote.split("-")[1] == "none"
            ]
        )
        for txn in all_txns:
            deleteTradeVotes(txn, session.get("user_id"))
        # add votes
        for txn in request.form:
            transaction_id, roster_id = txn.split("-")
            if roster_id != "none":
                addTradeVote(transaction_id, session.get("user_id"), int(roster_id))
        return redirect(url_for("home", _external=True))

    week = getTimeframe()["week"]
    teams = getTeams(True)
    return render_template(
        "home.html",
        matchups=getMatchups(week, teams),
        trades=getTrades(week + 1, teams),
        logged_in=session.get("user_id"),
    )


@app.route("/rules")
def rules():
    db = getDB()
    proposal = db.proposals.find_one({"open": True})
    with open("docs/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        return render_template(
            "rules.html",
            proposal=proposal,
            html=html,
        )


@app.route("/rules/edit")
def edit_rules():
    return redirect("https://github.com/redreceipt/kpffl/edit/master/docs/rules.md")


@app.route("/proposal", methods=["GET", "POST"])
def proposal():
    if request.method == "POST":
        sendEmail(
            str(request.form), "KPFFL Rule Change Proposal", request.form["email"]
        )
        return redirect(url_for("rules"))
    return render_template("proposal.html")


# TODO: remove in 2021 season
@app.route("/covid", methods=["GET", "POST"])
def covid():
    if request.method == "POST":
        sendEmail(str(request.form), "COVID Backups", request.form["email"])
        return redirect(url_for("home"))
    return render_template("covid.html")


@app.route("/teams")
def teams():
    return render_template("teams.html", teams=getTeams())


@app.route("/rankings")
@app.route("/rankings/<path:subpath>", methods=["GET", "POST"])
def rankings(subpath=None):

    voting = False
    if subpath:
        if subpath != "vote":
            return redirect(url_for("rankings"))
        voting = True

    # submit votes and refresh the page
    if request.method == "POST":
        # convert vote form into an array
        votes = [field for field in request.form]
        addCoachesPollVote(votes, session["user_id"])
        return redirect(url_for("rankings"))

    return render_template(
        "rankings.html",
        rankings=getRankings(),
        user_id=session.get("user_id"),
        voting=voting,
    )


@app.route("/rc/<int:rc_id>", methods=["GET", "POST"])
def rule_change_proposal(rc_id):
    if request.method == "POST":
        # add vote to DB
        if session.get("user_id"):
            addProposalVote(session.get("user_id"), rc_id, request.form["vote"])
        return redirect(url_for("rule_change_proposal", rc_id=rc_id))

    # get current votes
    proposal = getProposal(rc_id)
    if not proposal:
        abort(404)
    return render_template(
        "rc.html",
        rc_id=rc_id,
        proposal=proposal,
        logged_in=session.get("user_id"),
    )


@app.route("/chat")
def chat():
    return redirect(os.getenv("CHAT_URL"))


@app.route("/video")
def video():
    return redirect(os.getenv("VIDEO_URL"))


@app.route("/league")
def league():
    return redirect(os.getenv("LEAGUE_URL"))
