from functools import wraps

from flask import Flask, render_template, session, redirect, url_for, flash, abort, request, jsonify
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
# Each user has a username, password hash, and role (admin or member). Each chore has a title, done status, and an assignee (user).
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="member")  # "admin" or "member"

#Each chore has a title, done status, and an assignee (user).
#I wonder if in order to make it so that members can't assign chores to other members I should add a check in the route that adds chores to make sure that the assignee is not a member if the user adding the chore is a member.
class Chore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    done = db.Column(db.Boolean, default=False, nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assignee = db.relationship("User")


class Preference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    chore_id = db.Column(db.Integer, db.ForeignKey("chore.id"), nullable=False)
    dislike = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.UniqueConstraint("user_id", "chore_id", name="unique_user_chore_preference"),
    )


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
    form = ChoreForm()
    form.assignee.choices = [(0, "Unassigned")] + [(u.id, u.username) for u in User.query.all()]
    if form.validate_on_submit():
        assignee_id = form.assignee.data or None  # 0 -> None (unassigned)
        if session["role"] != "admin" and assignee_id not in (None, session["user_id"]):
            flash("Members can only assign chores to themselves.", "danger")
            return redirect(url_for("chores"))
        db.session.add(Chore(title=form.title.data, assignee_id=assignee_id))
        db.session.commit()
        flash("Chore added!", "success")
        return redirect(url_for("chores"))
    all_chores = Chore.query.all()
    preference_lookup = {
        (preference.user_id, preference.chore_id): preference.dislike
        for preference in Preference.query.all()
    }
    preferences = {
        chore.id: preference_lookup[(chore.assignee_id, chore.id)]
        for chore in all_chores
        if chore.assignee_id is not None
        and (chore.assignee_id, chore.id) in preference_lookup
    }
    return render_template("chores.html", form=form,
                           users=User.query.all(), chores=all_chores,
                           preferences=preferences)


@app.route("/mychores")
@login_required
def mychores():
    mine = (Chore.query.filter_by(assignee_id=session["user_id"])
            .order_by(Chore.done, Chore.id).all())  # unfinished first
    preferences = {
        preference.chore_id: preference.dislike
        for preference in Preference.query.filter_by(user_id=session["user_id"]).all()
    }
    return render_template("mychores.html", chores=mine, preferences=preferences)


@app.patch("/api/chores/<int:chore_id>")
@login_required
def move_chore(chore_id):
    """Updates a chore. Send {"assignee_id": ...} to move it and/or {"done": true/false} to check it off."""
    data = request.get_json(silent=True) or {}
    chore = db.session.get(Chore, chore_id)
    if chore is None:
        return jsonify(ok=False, error="Chore not found"), 404

    me = session["user_id"]
    is_admin = session["role"] == "admin"

    if "assignee_id" in data:
        target = data["assignee_id"]  # an int user id, or None for Unassigned
        if not is_admin and (chore.assignee_id not in (None, me) or target not in (None, me)):
            return jsonify(ok=False, error="Not allowed"), 403
        if target is not None and db.session.get(User, target) is None:
            return jsonify(ok=False, error="No such user"), 400
        chore.assignee_id = target

    if "done" in data:
        if not isinstance(data["done"], bool):
            return jsonify(ok=False, error="done must be true or false"), 400
        if not is_admin and chore.assignee_id != me:  # only the assignee (or an admin) can check it off
            return jsonify(ok=False, error="Not allowed"), 403
        chore.done = data["done"]

    db.session.commit()
    return jsonify(ok=True)


@app.patch("/api/chores/<int:chore_id>/preference")
@login_required
def update_preference(chore_id):
    data = request.get_json(silent=True) or {}
    dislike = data.get("dislike")
    if isinstance(dislike, bool) or not isinstance(dislike, int) or not 1 <= dislike <= 5:
        return jsonify(ok=False, error="dislike must be an integer from 1 to 5"), 400

    chore = db.session.get(Chore, chore_id)
    if chore is None:
        return jsonify(ok=False, error="Chore not found"), 404
    if chore.assignee_id != session["user_id"]:
        return jsonify(ok=False, error="Not allowed"), 403

    preference = Preference.query.filter_by(
        user_id=session["user_id"],
        chore_id=chore_id,
    ).first()
    if preference is None:
        preference = Preference(
            user_id=session["user_id"],
            chore_id=chore_id,
            dislike=dislike,
        )
        db.session.add(preference)
    else:
        preference.dislike = dislike
    db.session.commit()
    return jsonify(ok=True, dislike=dislike)

# ---------- Setup ----------
DEMO_USERS = [
    # username, password, role, chores they start with
    ("admin", "admin123", "admin", []),
    ("sam", "member123", "member", []),
    ("alex", "member123", "member", ["Clean the bathroom", "Water the plants"]),
    ("jordan", "member123", "member", ["Mow the lawn", "Cook dinner on Friday"]),
]
UNASSIGNED_CHORES = ["Wash the dishes", "Vacuum the living room", "Do the laundry", "Take out the trash"]


def seed_database():
    """Creates tables and adds any missing demo users, so new ones also show up in an existing site.db."""
    db.create_all()
    first_run = User.query.first() is None
    for username, password, role, chores in DEMO_USERS:
        if User.query.filter_by(username=username).first():
            continue
        user = User(username=username, password_hash=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.add_all([Chore(title=title, assignee=user) for title in chores])
    if first_run:
        db.session.add_all([Chore(title=title) for title in UNASSIGNED_CHORES])
    db.session.commit()


with app.app_context():
    seed_database()

if __name__ == "__main__":
    app.run(debug=True)