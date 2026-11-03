from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # load from an env variable later
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

db = SQLAlchemy(app, model_class=Base)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/do_your_chores")
def do_your_chores():
    return render_template("index.html")