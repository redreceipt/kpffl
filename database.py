import os

from pymongo import MongoClient


def getDB():
    """Gets the KPFFL Mongo database."""
    uri = os.getenv("MONGO_URI")
    client = MongoClient(uri)
    return client.kpffl


def getPlayerData(db, player_ids=[]):
    """Takes a list of player ids and returns their metadata from the database."""
    data = db.players.find(
        {"$or": [{"player_id": player_id} for player_id in player_ids]}
    )
    return {player["player_id"]: player for player in data}
