import os

from pymongo import MongoClient


def getDB():
    """Gets the KPFFL Mongo database."""
    uri = os.getenv("MONGO_URI")
    client = MongoClient(uri)
    return client.kpffl
