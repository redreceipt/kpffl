from math import floor
from statistics import mean

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from database import getDB
from sleeper import getTeams
from sportsdata import getTimeframe


def getCoachesPoll():
    """Gets coaches poll rankings."""

    # get team information, skipping players
    teams = getTeams(True)

    # get current week from Sportsdata API
    time = getTimeframe()

    # initialize dict of team rankings
    ranks = {team["id"]: [] for team in teams}

    db = getDB()
    votes = db.coaches_polls.find({"week": time["week"], "season": time["season"]})
    for vote in votes:
        for i, team in enumerate(vote["rankings"]):
            ranks[team].append(i + 1)

    teamsByRank = [{
        "id": team["id"],
        "name": team["name"],
        "owner": team["owner"],
        "rank": floor(mean(ranks[team["id"]] or [1])),
        "topVotes": ranks[team["id"]].count(1)
    } for team in teams]

    return {
        "week": time["week"],
        "season": time["season"],
        "numVotes": votes.count(),
        "teams": sorted(teamsByRank, key=lambda team: team["rank"])
    }


def addCoachesPollVote(votes, userID):
    """Adds one vote to the database."""

    # votes should be in the form ["team|3", "team|4", "team|1", etc...]
    db = getDB()
    time = getTimeframe()
    db.coaches_polls.update({
        "user_id": userID,
        "week": time["week"],
        "season": time["season"]
    }, {
        "user_id": userID,
        "week": time["week"],
        "season": time["season"],
        "rankings": votes
    },
                            upsert=True)

def sendProposal(proposal):
    """This will assemble a proposal from the submission form and email commisioners."""
    print(proposal)

    message = Mail(
        from_email='michael@neeley.dev',
        to_emails='micneeley14@gmail.com',
        subject='KPFFL Rule Change Proposal',
        html_content=str(proposal))
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)
