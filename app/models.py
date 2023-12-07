from datetime import datetime
from app import db, login
from flask import current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
from app.search import add_to_index, remove_from_index, query_index
import json


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total_dict = query_index(cls.__tablename__, expression, page, per_page)
        total = total_dict.get("value")
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = {}
        for i in range(len(ids)):
            when[ids[i]] = i
        return (
            cls.query.filter(cls.id.in_(ids)).order_by(db.case(when, value=cls.id)),
            total,
        )

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            "add": list(session.new),
            "update": list(session.dirty),
            "delete": list(session.deleted),
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes["add"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["update"]:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes["delete"]:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


db.event.listen(db.session, "before_commit", SearchableMixin.before_commit)
db.event.listen(db.session, "after_commit", SearchableMixin.after_commit)

followers = db.Table(
    "followers",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id")),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    avatar_path = db.Column(db.Text)
    posts = db.relationship(
        "Post", backref="author", lazy="dynamic", cascade="all, delete-orphan"
    )
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    followed = db.relationship(
        "User",
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref("followers", lazy="dynamic"),
        lazy="dynamic",
        cascade="all",
    )

    notifications = db.relationship(
        "Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def chat_new_messages(self, chat_id):
        user_chat = (
            db.session.query(user_chats)
            .filter_by(user_id=self.id, chat_id=chat_id)
            .first()
        )
        last_read_time = user_chat.last_message_read_time or datetime(1900, 1, 1)
        chat_messages_count = (
            ChatMessage.query.filter(ChatMessage.chat_id == chat_id)
            .filter(ChatMessage.sender_id != self.id)
            .filter(ChatMessage.timestamp > last_read_time)
            .count()
        )
        return chat_messages_count

    def all_new_messages(self):
        messages_count = sum(
            [
                self.chat_new_messages(string.chat_id)
                for string in self.notifications.all()
            ]
        )
        return messages_count

    def add_notification(self, name, data, chat_id):
        self.notifications.filter_by(chat_id=chat_id).delete()
        n = Notification(
            name=name, payload_json=json.dumps(data), user=self, chat_id=chat_id
        )
        db.session.add(n)
        return n

    def __repr__(self):
        return f"<User {self.username}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_avatar(self, file):
        filename = secure_filename(file.filename)
        file.save("app/static/avatars/" + filename)
        self.avatar_path = url_for("static", filename="avatars/" + filename)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return "https://www.gravatar.com/avatar/{}?d=identicon&s={}".format(
            digest, size
        )

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)
        ).filter(followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            current_app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )["reset_password"]
        except:
            return
        return User.query.get(id)


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


user_likes = db.Table(
    "user_likes",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("post_id", db.Integer, db.ForeignKey("post.id")),
)


class Post(SearchableMixin, db.Model):
    __searchable__ = ["body"]
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    photo_path = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    likes = db.relationship(
        "User",
        secondary=user_likes,
        backref=db.backref("likes", lazy="dynamic"),
        lazy="dynamic",
    )

    def set_photo(self, file):
        filename = secure_filename(file.filename)
        file.save("app/static/photos/" + filename)
        self.photo_path = url_for("static", filename="photos/" + filename)

    def like(self, user):
        if not self.is_liked(user):
            self.likes.append(user)

    def unlike(self, user):
        if self.is_liked(user):
            self.likes.remove(user)

    def is_liked(self, user):
        return self.likes.filter(user_likes.c.user_id == user.id).count() > 0

    def get_likes_count(self):
        return self.likes.count()


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    participants = db.relationship(
        "User",
        secondary="user_chats",
        backref=db.backref("chats", lazy="dynamic"),
        lazy="dynamic",
    )
    messages = db.relationship(
        "ChatMessage", backref="chat", lazy="dynamic", cascade="all, delete-orphan"
    )

    def is_participant(self, user):
        return self.participants.filter_by(id=user.id).count() > 0

    def get_last_message_username(self, user):
        if self.messages.all()[-1].sender_id == user.id:
            return "You"
        return (
            self.participants.filter_by(id=self.messages.all()[-1].sender_id)
            .first()
            .username
        )


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    sender = db.relationship("User", foreign_keys=[sender_id])
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return "<ChatMessage {}>".format(self.body)


user_chats = db.Table(
    "user_chats",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("chat_id", db.Integer, db.ForeignKey("chat.id")),
    db.Column("last_message_read_time", db.DateTime),
)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))
