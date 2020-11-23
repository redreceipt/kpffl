import asyncio
import os

import requests
from gql import AIOHTTPTransport, Client, gql
from gql.transport.exceptions import TransportQueryError

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
    return requests.get(f"https://api.sleeper.app/v1/league/{leagueID}").json()


def _getOwners():
    leagueID = os.getenv("LEAGUE_ID")
    owners = requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/users").json()
    ownerDict = {}
    for owner in owners:
        ownerDict[owner["user_id"]] = owner
    return ownerDict


def _getRosters():
    leagueID = os.getenv("LEAGUE_ID")
    return requests.get(f"https://api.sleeper.app/v1/league/{leagueID}/rosters").json()


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
                avatar
                display_name
                real_name
                email
                phone
                user_id
            }
        }
        """
    )
    try:
        data = client.request(query, {"user": user, "pw": pw})
    except TransportQueryError:
        return None
    userID = data["login"]["user_id"]
    season = getTimeframe()["season"]
    leagues = requests.get(
        f"https://api.sleeper.app/v1/user/{userID}/leagues/nfl/{season}"
    ).json()
    leagueIDs = [league["league_id"] for league in leagues]
    if os.getenv("LEAGUE_ID") in leagueIDs:
        db = getDB()
        db.users.update(
            {"user_id": data["login"]["user_id"]}, data["login"], upsert=True
        )
        return userID
    return None


def updatePlayers():
    """Gets players from Sleepers database and uploads to Mongo."""
    players = requests.get("https://api.sleeper.app/v1/players/nfl").json()

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


def getMatchups(week=None, teams=None):
    """Gets matchups for current week."""
    leagueID = os.getenv("LEAGUE_ID")
    week = week or getTimeframe()["week"]
    teams = teams or getTeams(True)

    data = requests.get(
        f"https://api.sleeper.app/v1/league/{leagueID}/matchups/{week}"
    ).json()

    # get all matchup IDs
    matchups = {
        str(matchupid): []
        for matchupid in set([matchup["matchup_id"] for matchup in data])
    }

    # add in team names and scores
    teamHash = {team["id"].split("|")[1]: team for team in teams}
    for matchup in data:
        matchups[str(matchup["matchup_id"])].append(
            {
                "team": teamHash[str(matchup["roster_id"])],
                "score": round(matchup["points"], 2),
            }
        )

    return matchups.values()


def getTrades(currentWeek=None, teams=None, n=5):
    """Gets recent transactions"""
    leagueID = os.getenv("LEAGUE_ID")
    currentWeek = currentWeek or getTimeframe()["week"]
    teams = teams or getTeams(True)
    db = getDB()

    # recursively search until I find 5 trades
    tradesData = []

    def findTrades(week):
        txns = requests.get(
            f"https://api.sleeper.app/v1/league/{leagueID}/transactions/{week}"
        ).json()

        # filter for only trades of two teams
        tradesData.extend(
            [
                trade
                for trade in txns
                if trade["type"] == "trade" and len(trade["roster_ids"]) == 2
            ]
        )
        if len(tradesData) < n:
            findTrades(week - 1)

    findTrades(currentWeek)
    tradesData = tradesData[:n]

    # get player info
    id_list_list = [trade["adds"].keys() for trade in tradesData]
    id_list = set([item for sublist in id_list_list for item in sublist])
    allPlayers = getPlayerData(db, id_list)

    trades = []

    def getTradeData(roster_id):
        players = [
            key
            for key in tradeData["adds"].keys()
            if tradeData["adds"][key] == roster_id
        ]
        picks = [
            pick for pick in tradeData["draft_picks"] if pick["owner_id"] == roster_id
        ]
        draftConvert = {1: "1st", 2: "2nd", 3: "3rd"}
        voteData = db.trade_votes.find(
            {
                "transaction_id": tradeData["transaction_id"],
                "roster_id": roster_id,
            }
        )
        voteUsers = [vote["user_id"] for vote in voteData]

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
            "votes": voteUsers,
        }

    for tradeData in tradesData:
        trade = {
            "transaction_id": tradeData["transaction_id"],
            "team1": getTradeData(tradeData["roster_ids"][0]),
            "team2": getTradeData(tradeData["roster_ids"][1]),
        }
        trades.append(trade)

    return trades


def addTradeVote(transaction_id, user_id, roster_id):
    """Adds Trade Vote to DB."""

    db = getDB()
    db.trade_votes.update(
        {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "roster_id": roster_id,
        },
        {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "roster_id": roster_id,
        },
        upsert=True,
    )


def deleteTradeVotes(transaction_id, user_id):
    """Delete Trade Votes per user."""

    db = getDB()
    db.trade_votes.delete_many(
        {
            "transaction_id": transaction_id,
            "user_id": user_id,
        },
    )
