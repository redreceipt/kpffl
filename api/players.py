import json

import requests
from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/players')
def players():
    r = requests.get("https://api.sleeper.app/v1/players/nfl")
    return jsonify(json.loads(r.text))
