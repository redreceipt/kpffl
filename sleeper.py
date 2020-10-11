import asyncio
import json
import os
import pprint

import requests
from gql import AIOHTTPTransport, Client, gql

from database import getDB

# from flask import session


class SleeperGraphQLClient:
    def __init__(self):
        # TODO remove once PR 135 makes it into gql
        asyncio.set_event_loop(asyncio.new_event_loop())
        transport = AIOHTTPTransport(url="https://sleeper.app/graphql")
        self.client = Client(transport=transport, fetch_schema_from_transport=False)

    def request(self, body, variables=None):
        return self.client.execute(body, variable_values=variables)


def _getLeague():
    leagueID = os.getenv("LEAGUE_ID")
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}")
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


def getOwner(user, pw):
    """Verifies user is an owner in the league."""
    client = SleeperGraphQLClient()
    query = gql(
        """
        query getUserID ($user: String! $pw: String!) {
            login(email_or_phone_or_username: $user password: $pw) {
                user_id
            }
        }
        """
    )
    data = client.request(query, {"user": user, "pw": pw})
    userID = data["login"]["user_id"]
    r = requests.get(f"https://api.sleeper.app/v1/user/{userID}/leagues/nfl/2020")
    leagues = json.loads(r.text)
    leagueIDs = [league["league_id"] for league in leagues]
    if os.getenv("LEAGUE_ID") in leagueIDs:
        return userID
    return None


def updatePlayers():
    """Gets players from Sleepers database."""
    # NOTE: should be used sparingly
    # TODO: players should be cached in a seperate call
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    players = json.loads(r.text)

    # update players in database
    db = getDB()
    db.drop_collection("players")
    db.create_collection("players")
    db.players.insert_many(players.values())
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
                    "name": getPlayerName(allPlayers[playerId])
                    if playerId != "0"
                    else "(Empty)",
                    "pos": positions.pop(0) if len(positions) else "",
                },
                ids,
            )
        )

    for i, roster in enumerate(rosters):

        players = []
        if not skipPlayers:
            allPlayers = updatePlayers()

            # build player groups
            starters = getPlayerGroup(
                roster["starters"],
                ["QB", "RB", "RB", "WR", "WR", "TE", "Flex", "DEF"],
                allPlayers,
            )
            reserve = getPlayerGroup(roster["reserve"] or [], ["IR"], allPlayers)
            taxi = getPlayerGroup(roster["taxi"] or [], ["Taxi"] * 3, allPlayers)

            # bench players are the ones remaining
            others = set(roster["players"]) - set(
                roster["starters"] + (roster["reserve"] or []) + (roster["taxi"] or [])
            )
            bench = getPlayerGroup(list(others), ["Bench"] * 12, allPlayers)
            players = {
                "starters": starters,
                "bench": bench,
                "reserve": reserve,
                "taxi": taxi,
            }

        owner = owners[roster["owner_id"]]
        teamName = (
            owner["metadata"]["team_name"]
            if "team_name" in owner["metadata"].keys()
            else f"Team {i+1}"
        )
        team = {
            # convert sleeper ID to KPFFL ID
            "id": "team|" + str(roster["roster_id"]),
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
