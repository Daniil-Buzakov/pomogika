from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(30))
    city = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    is_business = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ads = db.relationship("Ad", backref="author", cascade="all, delete-orphan")

    @property
    def kind(self):
        return "Бизнес" if self.is_business else "Частное лицо"


class Ad(db.Model):
    __tablename__ = "ads"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    price_unit = db.Column(db.String(10), default="task")
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    status = db.Column(db.String(20), default="active")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    photos = db.relationship("AdPhoto", backref="ad", cascade="all, delete-orphan")
    chats = db.relationship("Chat", backref="ad", cascade="all, delete-orphan")

    @property
    def price_label(self):
        return f"{self.price} ₽/час" if self.price_unit == "hour" else f"{self.price} ₽"


class AdPhoto(db.Model):
    __tablename__ = "ad_photos"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)


class Chat(db.Model):
    __tablename__ = "chats"
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey("ads.id"), nullable=False)
    user1_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user1 = db.relationship("User", foreign_keys=[user1_id])
    user2 = db.relationship("User", foreign_keys=[user2_id])
    messages = db.relationship("Message", backref="chat", cascade="all, delete-orphan",
                               order_by="Message.created_at")

    def other_user(self, me_id):
        return self.user2 if me_id == self.user1_id else self.user1

    def unread_for(self, me_id):
        return sum(1 for m in self.messages if m.sender_id != me_id and not m.is_read)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chats.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[sender_id])


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewed_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", foreign_keys=[author_id])
    reviewed = db.relationship("User", foreign_keys=[reviewed_id])
