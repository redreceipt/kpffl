import asyncio
import json
import os

import requests
from gql import AIOHTTPTransport, Client, gql

from database import getDB, getPlayerData
from sportsdata import getTimeframe

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


def _getRosterPlayers(rosters):

    # flatten player list
    simpleRosters = [roster["players"] for roster in rosters]
    allIds = [player for roster in simpleRosters for player in roster]

    # get players from DB
    db = getDB()
    return getPlayerData(db, allIds)


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
    """Gets players from Sleepers database and uploads to Mongo."""
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    players = json.loads(r.text)

    # update players in database
    db = getDB()
    db.drop_collection("players")
    db.create_collection("players")
    db.players.insert_many(players.values())
    db.players.create_index("player_id")


def getTeams(skipPlayers=False):
    """Gets the current teams in the league."""
    owners = _getOwners()
    rosters = _getRosters()
    players = _getRosterPlayers(rosters) if not skipPlayers else {}

    def getPlayerGroup(ids, positions):

        # pad positions with empty slots
        ids.extend(["0"] * (len(positions) - len(ids)))

        return list(
            map(
                lambda pId: {
                    "name": f"{players[pId]['first_name']} {players[pId]['last_name']}"
                    if pId != "0"
                    else "(Empty)",
                    "pos": positions.pop(0) if len(positions) else "",
                },
                ids,
            )
        )

    teams = []
    for i, roster in enumerate(rosters):

        # bench players are the ones remaining
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
            "players": {
                "starters": getPlayerGroup(
                    roster["starters"],
                    ["QB", "RB", "RB", "WR", "WR", "TE", "Flex", "DEF"],
                ),
                "bench": getPlayerGroup(
                    list(
                        set(roster["players"])
                        - set(
                            roster["starters"]
                            + (roster["reserve"] or [])
                            + (roster["taxi"] or [])
                        )
                    ),
                    ["Bench"] * 12,
                ),
                "reserve": getPlayerGroup(roster["reserve"] or [], ["IR"]),
                "taxi": getPlayerGroup(roster["taxi"] or [], ["Taxi"] * 3),
            }
            if len(players.keys())
            else {},
            "stats": {
                "w": roster["settings"]["wins"],
                "l": roster["settings"]["losses"],
                "pf": roster["settings"]["fpts"],
            },
        }
        teams.append(team)
    return teams


def getMatchups():
    """Gets matchups for current week."""
    leagueID = os.getenv("LEAGUE_ID")
    week = getTimeframe()["week"]
    r = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/matchups/{week}")
    data = json.loads(r.text)

    # get all matchup IDs
    matchups = {
        str(matchupid): []
        for matchupid in set([matchup["matchup_id"] for matchup in data])
    }

    # add in team names and scores
    teams = {team["id"].split("|")[1]: team for team in getTeams(True)}
    for matchup in data:
        matchups[str(matchup["matchup_id"])].append(
            {"team": teams[str(matchup["roster_id"])], "score": matchup["points"]}
        )

    return matchups.values()


def getTrades(n=5):
    """Gets recent transactions"""
    leagueID = os.getenv("LEAGUE_ID")
    currentWeek = getTimeframe()["week"]

    # recursively search until I find 5 trades
    tradesData = []

    def findTrades(week):
        r = requests.get(
            f"https://api.sleeper.app/v1/league/{leagueID}/transactions/{week}"
        )
        data = json.loads(r.text)

        # filter for only trades of two teams
        tradesData.extend(
            list(
                filter(
                    lambda trade: trade["type"] == "trade"
                    and len(trade["roster_ids"]) == 2,
                    data,
                )
            )
        )
        if len(tradesData) < n:
            findTrades(week - 1)

    findTrades(currentWeek)
    tradesData = tradesData[:n]

    # get player info
    id_list_list = [trade["adds"].keys() for trade in tradesData]
    id_list = set([item for sublist in id_list_list for item in sublist])
    db = getDB()
    allPlayers = getPlayerData(db, id_list)

    trades = []
    teams = getTeams(True)

    def extractTradeData(roster_id):
        players = [
            key
            for key in tradeData["adds"].keys()
            if tradeData["adds"][key] == roster_id
        ]
        picks = [
            pick for pick in tradeData["draft_picks"] if pick["owner_id"] == roster_id
        ]
        draftConvert = {1: "1st", 2: "2nd", 3: "3rd"}
        return {
            "team": [
                team for team in teams if team["id"].split("|")[1] == str(roster_id)
            ][0],
            "players": [allPlayers[player_id] for player_id in players],
            "picks": [
                {
                    "season": pick["season"],
                    "round": draftConvert[pick["round"]],
                    "owner": [
                        team
                        for team in teams
                        if team["id"].split("|")[1] == str(pick["roster_id"])
                    ][0]["owner"],
                }
                for pick in picks
            ],
        }

    for tradeData in tradesData:
        trade = {
            "team1": extractTradeData(tradeData["roster_ids"][0]),
            "team2": extractTradeData(tradeData["roster_ids"][1]),
        }
        trades.append(trade)

    return trades
