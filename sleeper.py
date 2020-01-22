import json

import requests

LEAGUE_ID = 515543543873765376


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


def getTeams():
    """Gets the current teams in the league."""
    # get all the player info, should be used sparingly
    # TODO should be cached in a seperate call
    players = getPlayers()
    owners = getOwners()

    # get rosters
    r = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters")
    rosters = json.loads(r.text)

    # assemble teams
    teams = []
    for i, roster in enumerate(rosters):
        owner = owners[roster["owner_id"]]

        # starters have their own positions listed.
        starters = list(
            map(
                lambda x: {
                    "name":
                    f"{players[x]['first_name']} {players[x]['last_name']}",
                    "pos": players[x]["position"]
                } if players[x]["player_id"] != "0" else {
                    "name": "(Empty)",
                    "pos": ""
                }, roster["starters"]))

        team = {
            "name":
            owner["metadata"]["team_name"]
            if "team_name" in owner["metadata"].keys() else f"Team {i+1}",
            "owner":
            owner["display_name"],
            "players":
            starters
        }
        teams.append(team)
    return teams

    # return [
    # {
    # "name":
    # "Team 1",
    # "owner":
    # "Michael Neeley",
    # "players": [{
    # "pos": "WR",
    # "name": "OBJ"
    # }, {
    # "pos": "WR",
    # "name": "AB84"
    # }]
    # },
    # {
    # "name":
    # "Team 2",
    # "owner":
    # "Daniel Crowe",
    # "players": [{
    # "pos": "RB",
    # "name": "Beast Mode"
    # }, {
    # "pos": "TE",
    # "name": "Gronk"
    # }]
    # },
    # ]
