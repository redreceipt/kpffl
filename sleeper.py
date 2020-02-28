import json

import requests

# TODO come from the session and linked to the user
LEAGUE_ID = 515543543873765376


def _getLeague(leagueID):
    r = requests.get(
        f"https://api.sleeper.app/v1/league/{leagueID or LEAGUE_ID}")
    return json.loads(r.text)


def _getOwners(leagueID):
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/users")
    owners = json.loads(r.text)
    ownerDict = {}
    for owner in owners:
        ownerDict[owner["user_id"]] = owner
    return ownerDict


def _getRosters(leagueID):
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/rosters")
    return json.loads(r.text)


def getPlayers():
    """Gets players from Sleepers database."""
    # NOTE: should be used sparingly
    # TODO: players should be cached in a seperate call
    print("hello")
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    return json.loads(r.text)


def getTeams(leagueID=None, skipPlayers=False):
    """Gets the current teams in the league."""
    owners = _getOwners(leagueID or LEAGUE_ID)
    rosters = _getRosters(leagueID or LEAGUE_ID)

    # assemble teams
    teams = []

    def getPlayerName(player):
        return f"{player['first_name']} {player['last_name']}"

    def getPlayerGroup(ids, positions, allPlayers):
        # pad positions with empty slots
        ids.extend(["0"] * (len(positions) - len(ids)))

        return list(
            map(
                lambda playerId: {
                    # TODO: ternary only necessary because there's a bug
                    # in the sleeper API
                    "name":
                    getPlayerName(allPlayers[playerId])
                    if playerId != "0" else "(Empty)",
                    "pos":
                    positions.pop(0),
                },
                ids,
            ))

    for i, roster in enumerate(rosters):

        players = []
        if not skipPlayers:
            allPlayers = getPlayers()

            # build player groups
            starters = getPlayerGroup(
                roster["starters"],
                ["QB", "RB", "RB", "WR", "WR", "TE", "Flex", "DEF"],
                allPlayers,
            )
            reserve = getPlayerGroup(roster["reserve"] or [], ["IR"],
                                     allPlayers)
            taxi = getPlayerGroup(roster["taxi"] or [], ["Taxi"] * 3,
                                  allPlayers)

            # bench players are the ones remaining
            others = set(roster["players"]) - set(roster["starters"] +
                                                  (roster["reserve"] or []) +
                                                  (roster["taxi"] or []))
            bench = getPlayerGroup(list(others), ["Bench"] * 12, allPlayers)
            players = starters + bench + reserve + taxi

        owner = owners[roster["owner_id"]]
        teamName = owner["metadata"]["team_name"] if "team_name" in owner[
            "metadata"].keys() else f"Team {i+1}"
        team = {
            "id": roster["roster_id"],
            "name": teamName,
            "owner": owner["display_name"],
            "players": players,
            "stats": {
                "w": roster["settings"]["wins"],
                "l": roster["settings"]["losses"],
                "pf": roster["settings"]["fpts"],
            },
        }
        teams.append(team)
    return teams


def getStandings(leagueID=None):
    """Gets standings of the most recent active league."""

    league = _getLeague(leagueID or LEAGUE_ID)
    winnerID = None
    loserID = None
    if league["status"] != "in_season":
        league = _getLeague(league["previous_league_id"])

    teams = getTeams(league["league_id"], True)

    # get post-season results
    r = requests.get(
        f"https://api.sleeper.app/v1/league/{league['league_id']}/winners_bracket"
    )
    winners = json.loads(r.text)
    winnerID = list(
        filter(lambda round: "p" in round.keys() and round["p"] == 1,
               winners))[0]["w"]
    r = requests.get(
        f"https://api.sleeper.app/v1/league/{league['league_id']}/losers_bracket"
    )
    losers = json.loads(r.text)
    loserID = list(
        filter(lambda round: "p" in round.keys() and round["p"] == 1,
               losers))[0]["w"]
    playoffTeams = set()
    for round in winners:
        playoffTeams.add(round["t1"])
        playoffTeams.add(round["t2"])

    def getPostSeasonStatus(teamID):
        if teamID == winnerID:
            return "trophy"
        if teamID == loserID:
            return "toilet"
        if teamID in playoffTeams:
            return "football-ball"

    teamsByRank = [{
        "postSeasonIcon":
        getPostSeasonStatus(team["id"]),
        "name":
        team["name"],
        "stats":
        team['stats'],
        "record":
        f"{team['stats']['w']}-{team['stats']['l']} ({team['stats']['pf']})"
    } for team in teams]

    # TODO: need to sort by playoff bracket then by wins and losses
    # rostersById = {}
    # for roster in rosters:
    # rostersById[roster["roster_id"]]: roster

    # first six positions are from the playoffs
    # r = requests.get(
    # f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/winners_bracket")
    # bracket = json.loads(r.text) or []
    # for matchup in bracket:
    # pass

    return {
        "league":
        league,
        "teams":
        sorted(teamsByRank, key=lambda team: team["stats"]["w"], reverse=True)
    }
