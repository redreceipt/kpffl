import os
from functools import wraps

import markdown
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, request, session, url_for
from six.moves.urllib.parse import urlencode

from database import getDB
from kpffl import addCoachesPollVote, getCoachesPoll
from sleeper import getStandings, getTeams, verifyOwner

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id='x1wWsLZAZlLgrSeboClluZcNwbSbeK2Z',
    client_secret=os.getenv("AUTH0_SECRET"),
    api_base_url='https://dev-xydv0aul.auth0.com',
    access_token_url='https://dev-xydv0aul.auth0.com/oauth/token',
    authorize_url='https://dev-xydv0aul.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

# use this to wrap methods that need authentication like this:
'''
@app.route('/dashboard')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))

Dashboard template
------------------
<div class="logged-in-box auth0-box logged-in">
    <h1 id="logo"><img src="//cdn.auth0.com/samples/auth0_logo_final_blue_RGB.png" /></h1>
    <img class="avatar" src="{{userinfo['picture']}}"/>
    <h2>Welcome {{userinfo['name']}}</h2>
    <pre>{{userinfo_pretty}}</pre>
    <a class="btn btn-primary btn-lg btn-logout btn-block" href="/logout">Logout</a>
</div>
'''


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            return redirect(url_for("home"))
        return f(*args, **kwargs)

    return decorated


@app.route('/callback')
def callback():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect(url_for("home"))


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=url_for("callback"))


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {
        'returnTo': url_for('home'),
        'client_id': 'x1wWsLZAZlLgrSeboClluZcNwbSbeK2Z'
    }
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/rules")
def rules():
    with open("docs/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        # add link to edit if logged in
        if session.get("profile"):
            firstLine = html.split("\n")[0]
            html = html.replace(
                firstLine, firstLine +
                f"<a href=\"{r'https://github.com/redreceipt/kpffl/edit/master/docs/rules.md'}\">(Edit)</a>"
            )
        return render_template("rules.html", html=html)


@app.route("/teams")
def teams():
    return render_template("teams.html", teams=getTeams())


@app.route("/rankings", methods=['POST', 'GET'])
def rankings():

    rankings = {"standings": getStandings(), "cp": getCoachesPoll()}
    if request.method == "POST" and session.get("profile"):
        # validate form
        if set([int(teamID)
                for teamID in request.form.values()]) != set(range(1, 13)):
            error = "Number teams 1-12"
            return render_template("rankings.html",
                                   rankings=rankings,
                                   voting=True,
                                   error=error)
        else:
            # submit votes
            addCoachesPollVote(request.form, session["profile"]["user_id"])

    voting = request.args.get("voting") == "true" and session.get("profile")
    return render_template("rankings.html", rankings=rankings, voting=voting)


@app.route("/sync", methods=["POST", "GET"])
@requires_auth
def sync():

    if request.method == "POST":
        verified = verifyOwner(request.form["email"], request.form["password"])
        session["isOwner"] = verified
        return redirect(url_for("home"))
    return render_template("sync.html")


@app.route('/meet')
def meet():
    return redirect(os.getenv("GOOGLE_MEET_URI"), code=301)


@app.route('/chat')
def chat():
    return redirect(os.getenv("DISCORD_URI"), code=301)
