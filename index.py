from flask import Flask, Response, render_template
import markdown

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/rules")
def rules():
    with open("docs/rules.md") as f:
        text = f.read()
        html = markdown.markdown(text)
        return render_template("rules.html", html=html)
