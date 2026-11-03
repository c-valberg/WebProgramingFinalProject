from functools import wraps

from flask import Flask, render_template, session, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length

APP_NAME = "Chore Tracker"  # change this once and it updates everywhere

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # move to an environment variable later
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

db = SQLAlchemy(app)
CSRFProtect(app)  # protects every POST form


# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="member")  # "admin" or "member"


class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assignee = db.relationship("User")


# ---------- Forms ----------
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class ChoreForm(FlaskForm):
    title = StringField("Chore", validators=[DataRequired(), Length(max=100)])
    assignee = SelectField("Assign to", coerce=int)
    submit = SubmitField("Add chore")


# ---------- Helpers ----------
@app.context_processor
def inject_globals():
    """Makes app_name available in every template."""
    return {"app_name": APP_NAME}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to see your chores.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("chores"))
        flash("That username and password don't match. Try again.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/chores", methods=["GET", "POST"])
@login_required
def chores():
    is_admin = session["role"] == "admin"
    form = ChoreForm()
    form.assignee.choices = [(u.id, u.username) for u in User.query.order_by(User.username)]

    # Only admins can add chores
    if form.validate_on_submit():
        if not is_admin:
            abort(403)
        db.session.add(Chore(title=form.title.data, assignee_id=form.assignee.data))
        db.session.commit()
        flash("Chore added.", "success")
        return redirect(url_for("chores"))

    query = Chore.query.order_by(Chore.done, Chore.id)
    if not is_admin:  # members only see their own chores
        query = query.filter_by(assignee_id=session["user_id"])
    return render_template("chores.html", chores=query.all(), form=form, is_admin=is_admin)


@app.route("/chores/<int:chore_id>/toggle", methods=["POST"])
@login_required
def toggle_chore(chore_id):
    chore = db.get_or_404(Chore, chore_id)
    if session["role"] != "admin" and chore.assignee_id != session["user_id"]:
        abort(403)
    chore.done = not chore.done
    db.session.commit()
    return redirect(url_for("chores"))


# ---------- Setup ----------
def seed_database():
    """Creates tables and two demo users the first time the app runs."""
    db.create_all()
    if not User.query.first():
        db.session.add_all([
            User(username="admin", password_hash=generate_password_hash("admin123"), role="admin"),
            User(username="sam", password_hash=generate_password_hash("member123"), role="member"),
        ])
        db.session.commit()


with app.app_context():
    seed_database()

if __name__ == "__main__":
    app.run(debug=True)