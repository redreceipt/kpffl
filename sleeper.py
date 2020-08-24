import json
import os

import requests


def _getLeague():
    leagueID = os.getenv("LEAGUE_ID")
    r = requests.get(
        f"https://api.sleeper.app/v1/league/{leagueID or os.getenv('LEAGUE_ID')}"
    )
    return json.loads(r.text)


def _getOwners():
    leagueID = os.getenv("LEAGUE_ID")
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/users")
    owners = json.loads(r.text)
    ownerDict = {}
    for owner in owners:
        ownerDict[owner["user_id"]] = owner
    return ownerDict


def _getRosters():
    leagueID = os.getenv("LEAGUE_ID")
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/rosters")
    return json.loads(r.text)


def verifyOwner(username, pw):
    """Verifies user is an owner in the league."""
    loginQuery = f" {{ login( email_or_phone_or_username: \"{username}\" password: \"{pw}\") {{ user_id }} }} "
    r = requests.post("https://sleeper.app/graphql",
                      json={"query": loginQuery})
    userID = json.loads(r.text)["data"]["login"]["user_id"]
    r = requests.get(
        f"https://api.sleeper.app/v1/user/{userID}/leagues/nfl/2020")
    leagues = json.loads(r.text)
    leagueIDs = [league["league_id"] for league in leagues]
    if os.getenv("LEAGUE_ID") in leagueIDs:
        return userID
    return None


def getPlayers():
    """Gets players from Sleepers database."""
    # NOTE: should be used sparingly
    # TODO: players should be cached in a seperate call
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    return json.loads(r.text)


def getTeams(skipPlayers=False):
    """Gets the current teams in the league."""
    owners = _getOwners()
    rosters = _getRosters()

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
                    positions.pop(0) if len(positions) else "",
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
