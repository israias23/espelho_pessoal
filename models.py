from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    company = db.Column(db.String(100))
    profile_photo = db.Column(db.String(200), default='static/default_profile.jpg')
    push_subscription = db.Column(db.Text)  # JSON for web push subscription
    records = db.relationship('Record', backref='user', lazy=True)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    type = db.Column(db.String(10))  # 'entry' or 'exit'
    note = db.Column(db.String(200))
    break_duration = db.Column(db.Integer, default=0)
    location = db.Column(db.String(200))
    photo_path = db.Column(db.String(200))