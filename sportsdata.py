import json
import os

import requests


def getTimeframe():
    """Gets current NFL season and week."""

    headers = {"Ocp-Apim-Subscription-Key": os.getenv("SPORTSDATA_KEY")}
    r = requests.get(
        "https://api.sportsdata.io/v3/nfl/scores/json/Timeframes/current",
        headers=headers)
    timeframe = json.loads(r.text)[0]
    week = timeframe["Week"]
    season = timeframe["Season"]

    # preseason
    if timeframe["SeasonType"] in (2, 4):
        week = 0

    # postseason
    if timeframe["SeasonType"] in (3, 5):
        week = 0
        season += 1

    return {"season": season, "week": week}
