from sleeper import getTeams
from sportsdata import getCurrentWeek


def getCoachesPoll():
    """Gets coaches poll rankings."""

    teams = getTeams(None, True)

    teamsByRank = [{
        "name": team["name"],
        "rank": 0,
        "topVotes": 1
    } for team in teams]

    return {
        "week": getCurrentWeek(),
        "teams": sorted(teamsByRank,
                        key=lambda team: team["rank"],
                        reverse=True)
    }
