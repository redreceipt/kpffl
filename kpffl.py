from math import floor
from statistics import mean

from database import getDB
from sleeper import getTeams
from sportsdata import getCurrentWeek


def getCoachesPoll():
    """Gets coaches poll rankings."""

    teams = getTeams(None, True)
    week = getCurrentWeek()
    ranks = {team["id"]: [] for team in teams}

    db = getDB()
    votes = db.coaches_polls.find({"week": week})
    for vote in votes:
        for i, team in enumerate(vote["rankings"]):
            # convert kpffl ID to sleeper ID
            teamID = int(team)
            ranks[teamID].append(i + 1)

    teamsByRank = [{
        "id": team["id"],
        "name": team["name"],
        "rank": floor(mean(ranks[team["id"]])),
        "topVotes": ranks[team["id"]].count(1)
    } for team in teams]

    return {
        "week": week,
        "numVotes": votes.count(),
        "teams": sorted(teamsByRank, key=lambda team: team["rank"])
    }
