import json

import requests

from database import getDB

LEAGUE_ID = 515543543873765376


def getLeague():
    """Gets league info."""
    r = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}")
    return json.loads(r.text)


def getPlayers():
    """Gets players from Sleepers database."""
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    return json.loads(r.text)


def getOwners():
    """Gets owners in a sleeper league."""
    r = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users")
    owners = json.loads(r.text)
    ownerDict = {}
    for owner in owners:
        ownerDict[owner["user_id"]] = owner
    return ownerDict


def _getRosters():
    r = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters")
    return json.loads(r.text)


def getTeams():
    """Gets the current teams in the league."""
    # get all the player info, should be used sparingly
    # TODO should be cached in a seperate call
    players = getPlayers()
    owners = getOwners()

    # get rosters
    rosters = _getRosters()

    # assemble teams
    teams = []

    def _getPlayerName(player):
        return f"{player['first_name']} {player['last_name']}"

    # starters have their own positions listed.
    # TODO: ternary only necessary because there's a bug
    # in the sleeper API
    def _getSimplePlayerGroup(ids, positions):

        # pad positions with empty slots
        ids.extend(['0'] * (len(positions) - len(ids)))

        return list(
            map(
                lambda playerId: {
                    "name":
                    _getPlayerName(players[playerId])
                    if playerId != "0" else "(Empty)",
                    "pos":
                    positions.pop(0)
                }, ids))

    for i, roster in enumerate(rosters):
        owner = owners[roster["owner_id"]]

        # build player groups
        starters = _getSimplePlayerGroup(
            roster["starters"],
            ["QB", "RB", "RB", "WR", "WR", "TE", "Flex", "DEF"])
        reserve = _getSimplePlayerGroup(roster["reserve"] or [], ["IR"])
        taxi = _getSimplePlayerGroup(roster["taxi"] or [], ["Taxi"] * 3)

        # bench players are the ones remaining
        others = set(roster["players"]) - set(roster["starters"] +
                                              (roster["reserve"] or []) +
                                              (roster["taxi"] or []))
        bench = _getSimplePlayerGroup(list(others), ["Bench"] * 12)

        team = {
            "name":
            owner["metadata"]["team_name"]
            if "team_name" in owner["metadata"].keys() else f"Team {i+1}",
            "owner":
            owner["display_name"],
            "players":
            starters + bench + reserve + taxi
            # + bench + reserve + taxi
        }
        teams.append(team)
    return teams


def getStandings():
    """Gets standings from a given league ID."""

    # get rosters
    rosters = _getRosters()
    rostersById = {}
    for roster in rosters:
        rostersById[roster["roster_id"]]: roster

    # first six positions are from the playoffs
    r = requests.get(
        f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/winners_bracket")
    bracket = json.loads(r.text)
    for matchup in bracket:
        pass
    # TODO: need to sort by playoff bracket then by wins and losses
    return [{"rank": 1, "name": "team 1", "record": "8-4", "points": 953}]
