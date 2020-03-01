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
            teamID = int(team.split("|")[1])
            ranks[teamID].append(i + 1)

    teamsByRank = [{
        "id": team["id"],
        "name": team["name"],
        "rank": floor(mean(ranks[team["id"]] or [1])),
        "topVotes": ranks[team["id"]].count(1)
    } for team in teams]

    return {
        "week": week,
        "numVotes": votes.count(),
        "teams": sorted(teamsByRank, key=lambda team: team["rank"])
    }


def addCoachesPollVote(vote, userID):
    """Adds one vote to the database."""

    rankings = []

    # swap vote hash
    voteDict = {value: key for key, value in vote.items()}
    for i in range(12):
        rankings.append(voteDict[str(i + 1)])

    db = getDB()
    db.coaches_polls.update({
        "user_id": userID,
        "week": getCurrentWeek()
    }, {
        "user_id": userID,
        "week": getCurrentWeek(),
        "rankings": rankings
    },
                            upsert=True)
