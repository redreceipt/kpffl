from math import floor
from statistics import mean

from database import getDB
from sleeper import getTeams
from sportsdata import getCurrentWeek


def getCoachesPoll():
    """Gets coaches poll rankings."""

    # get team information, skipping players
    teams = getTeams(True)

    # get current week from Sportsdata API
    week = getCurrentWeek()

    # initialize dict of team rankings
    ranks = {team["id"]: [] for team in teams}

    db = getDB()
    votes = db.coaches_polls.find({"week": week})
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
        "week": week,
        "numVotes": votes.count(),
        "teams": sorted(teamsByRank, key=lambda team: team["rank"])
    }


def addCoachesPollVote(votes, userID):
    """Adds one vote to the database."""

    # votes should be in the form ["team|3", "team|4", "team|1", etc...]
    db = getDB()
    db.coaches_polls.update({
        "user_id": userID,
        "week": getCurrentWeek()
    }, {
        "user_id": userID,
        "week": getCurrentWeek(),
        "rankings": votes
    },
                            upsert=True)
