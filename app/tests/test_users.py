import os
from dotenv import load_dotenv
import pytest
from app import create_app, db
from datetime import datetime, timedelta
from app.models import User, Post
from config import Config

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL")


@pytest.fixture()
def setup(request):
    app = create_app(TestConfig)
    app_context = app.app_context()
    app_context.push()
    db.create_all()

    def teardown():
        db.session.remove()
        db.drop_all()
        app_context.pop()

    request.addfinalizer(teardown)


def test_password_hashing(setup):
    u = User(username="susan")
    u.set_password("cat")
    assert not u.check_password("dog")
    assert u.check_password("cat")


def test_avatar(setup):
    u = User(username="john", email="john@example.com")
    assert (
        u.avatar(128) == "https://www.gravatar.com/avatar/"
        "d4c74594d841139328695756648b6bd6"
        "?d=identicon&s=128"
    )


def test_follow(setup):
    u1 = User(username="john", email="john@example.com")
    u2 = User(username="susan", email="susan@example.com")
    db.session.add(u1)
    db.session.add(u2)
    db.session.commit()
    assert len(u1.followed.all()) == 0
    assert len(u1.followers.all()) == 0

    u1.follow(u2)
    db.session.commit()
    assert u1.is_following(u2)
    assert u1.followed.count() == 1
    assert u1.followed.first().username == "susan"
    assert u2.followers.count() == 1
    assert u2.followers.first().username == "john"

    u1.unfollow(u2)
    db.session.commit()
    assert not u1.is_following(u2)
    assert u1.followed.count() == 0
    assert u2.followers.count() == 0


def test_follow_posts(setup):
    u1 = User(username="john", email="john@example.com")
    u2 = User(username="susan", email="susan@example.com")
    u3 = User(username="mary", email="mary@example.com")
    u4 = User(username="david", email="david@example.com")
    db.session.add_all([u1, u2, u3, u4])

    now = datetime.utcnow()
    p1 = Post(body="post from john", author=u1, timestamp=now + timedelta(seconds=1))
    p2 = Post(body="post from susan", author=u2, timestamp=now + timedelta(seconds=4))
    p3 = Post(body="post from mary", author=u3, timestamp=now + timedelta(seconds=3))
    p4 = Post(body="post from david", author=u4, timestamp=now + timedelta(seconds=2))
    db.session.add_all([p1, p2, p3, p4])
    db.session.commit()

    u1.follow(u2)  # john follows susan
    u1.follow(u4)  # john follows david
    u2.follow(u3)  # susan follows mary
    u3.follow(u4)  # mary follows david
    db.session.commit()

    # check the followed posts of each user
    f1 = u1.followed_posts().all()
    f2 = u2.followed_posts().all()
    f3 = u3.followed_posts().all()
    f4 = u4.followed_posts().all()
    assert f1 == [p2, p4, p1]
    assert f2 == [p2, p3]
    assert f3 == [p3, p4]
    assert f4 == [p4]
