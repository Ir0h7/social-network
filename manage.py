from flask.cli import FlaskGroup
from flask import current_app
from app import db


cli = FlaskGroup(current_app)


@cli.command("create_db")
def create_db():
    db.create_all()
    db.session.commit()


if __name__ == "__main__":
    cli()
