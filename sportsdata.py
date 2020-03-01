import json
import os

import requests


def getCurrentWeek():
    """Gets current NFL week."""

    headers = {"Ocp-Apim-Subscription-Key": os.getenv("SPORTSDATA_KEY")}
    r = requests.get(
        "https://api.sportsdata.io/v3/nfl/scores/json/CurrentWeek",
        headers=headers)
    return json.loads(r.text)
