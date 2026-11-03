from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from flask import Flask, request, session
from flask import redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import Enum, select, Integer, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from wtforms.fields import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, InputRequired, NumberRange, length

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')