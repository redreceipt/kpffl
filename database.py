import os

from pymongo import MongoClient


def getDB():
    """Gets the KPFFL Mongo database."""
    host = os.getenv("MONGO_HOST")
    user = os.getenv("MONGO_USER")
    pw = os.getenv("MONGO_PW")
    client = MongoClient(f"mongodb+srv://{user}:{pw}@{host}")
    return client.kpffl
