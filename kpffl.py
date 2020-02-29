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
    print(votes)
    for vote in votes:
        print(vote["rankings"])
        for rank, team in enumerate(vote["rankings"]):
            print(ranks[team["id"]])
            ranks[team["id"]].append(rank)

    print(ranks)

    teamsByRank = [{
        "name": team["name"],
        "rank": 0,
        "topVotes": 1
    } for team in teams]

    return {
        "week": week,
        "teams": sorted(teamsByRank,
                        key=lambda team: team["rank"],
                        reverse=True)
    }
