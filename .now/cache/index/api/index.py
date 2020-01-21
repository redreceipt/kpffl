from flask import Flask, Response, render_template
import markdown
app = Flask(__name__)

@app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
def catch_all(path):
    return Response("<h1>Flask on Now</h1><p>You visited: /%s</p>" % (path), mimetype="text/html")

@app.route('/rules')
def rules():
    with open("static/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        return render_template("rules.html", html=html)
