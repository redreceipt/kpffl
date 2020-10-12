import os
import re
from math import floor
from statistics import mean

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from database import getDB
from sleeper import getTeams
from sportsdata import getTimeframe


def _getCoachesPoll(teams):

    # get current week from Sportsdata API
    time = getTimeframe()

    # initialize dict of team rankings
    ranks = {team["id"]: [] for team in teams}

    db = getDB()
    votes = db.coaches_polls.find({"week": time["week"], "season": time["season"]})
    for vote in votes:
        for i, team in enumerate(vote["rankings"]):
            ranks[team].append(i + 1)

    teamsWithRank = [
        {
            "id": team["id"],
            "name": team["name"],
            "owner": team["owner"],
            "rank": floor(mean(ranks[team["id"]] or [1])),
            "topVotes": ranks[team["id"]].count(1),
        }
        for team in teams
    ]

    return {
        "week": time["week"],
        "season": time["season"],
        "numVotes": votes.count(),
        "teams": sorted(teamsWithRank, key=lambda team: team["rank"]),
    }


def _getStandings(teams):
    # sorted(student_objects, key=attrgetter('age'))
    teamsByPoints = sorted(teams, key=lambda team: team["stats"]["pf"], reverse=True)
    teamsByWins = sorted(
        teamsByPoints, key=lambda team: team["stats"]["w"], reverse=True
    )
    return {"teams": teamsByWins}


def getRankings():
    """Gets Rankings."""

    # get team information, skipping players
    teams = getTeams(True)
    return {"cp": _getCoachesPoll(teams), "standings": _getStandings(teams)}


def addCoachesPollVote(votes, userID):
    """Adds one vote to the database."""

    # votes should be in the form ["team|3", "team|4", "team|1", etc...]
    db = getDB()
    time = getTimeframe()
    db.coaches_polls.update(
        {"user_id": userID, "week": time["week"], "season": time["season"]},
        {
            "user_id": userID,
            "week": time["week"],
            "season": time["season"],
            "rankings": votes,
        },
        upsert=True,
    )


def sendEmail(body, subject, email=""):
    """Sends email to commisioners."""
    print(body)
    dest = ["micneeley14@gmail.com", "hunterreid49@gmail.com"]
    if re.match(r"\w+@\w+\.\w+", email):
        dest.append(email)

    # TODO create a new proposal in the DB with rc_id = 0
    # fill in author, title, why, what, how
    # send email to commish with an embedded approve link in the form:
    # https://kpffl.com/rc/approve/<ID>
    # that link will set the rc_id to the next largest item and make the page live

    message = Mail(
        from_email="michael@neeley.dev",
        to_emails=dest,
        subject=subject,
        html_content=body,
    )
    try:
        sg = SendGridAPIClient(os.environ.get("SENDGRID_KEY"))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


def getProposal(rc_id):
    """This gets yes and no votes for a given proposal from the DB."""

    db = getDB()
    proposal = db.proposals.find_one({"rc_id": rc_id})
    if not proposal:
        return None
    votes = db.proposal_votes.find({"proposal_id": proposal["_id"]})
    yes, no = 0, 0
    for vote in votes:
        if vote["yes_vote"]:
            yes += 1
        else:
            no += 1
    proposal["yes"] = yes
    proposal["no"] = no
    return proposal


def addProposalVote(user_id, rc_id, vote):
    """Adds rule change proposal to the DB."""

    db = getDB()
    proposal = db.proposals.find_one({"rc_id": rc_id})
    db.proposal_votes.update(
        {"user_id": user_id, "proposal_id": proposal["_id"]},
        {"user_id": user_id, "yes_vote": vote == "yes", "proposal_id": proposal["_id"]},
        upsert=True,
    )
