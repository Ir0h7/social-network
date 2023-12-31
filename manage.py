from flask.cli import FlaskGroup
from flask import current_app
from app import db
from app.models import User, Post
from mimesis import Generic
from mimesis.locales import Locale
from faker import Faker
import random


cli = FlaskGroup(current_app)

generic = Generic(locale=Locale.EN)
fake = Faker()


@cli.command("create_db")
def create_db():
    db.create_all()
    db.session.commit()


@cli.command("generate_random_users")
def generate_random_users(count=10000):
    for _ in range(count):
        user = User(
            username=generic.person.username(),
            email=generic.person.email(),
            last_seen=generic.datetime.datetime(start=2022, end=2023),
        )
        user.set_password(generic.person.password(length=20))
        db.session.add(user)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@cli.command("generate_random_posts")
def generate_random_posts(count=4):
    users = User.query.all()
    for user in users:
        for _ in range(count):
            post = Post(
                body=generic.text.text(),
                timestamp=generic.datetime.datetime(
                    start=2022, end=user.last_seen.year
                ),
                user_id=user.id,
            )
            db.session.add(post)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@cli.command("generate_followers")
def generate_followers():
    users = User.query.all()
    count_user = db.session.query(User).count()
    for user in users:
        random_following = fake.random_elements(
            elements=users, length=random.randint(1, count_user), unique=True
        )
        for random_user in random_following:
            if not user.is_following(random_user) and user.id != random_user.id:
                user.follow(random_user)
        db.session.commit()


if __name__ == "__main__":
    cli()
