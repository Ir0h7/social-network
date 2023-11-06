import os
from dotenv import load_dotenv


class Config(object):
    SECRET_KEY = os.getenv("SECRET_KEY", "you-will-never-guess")
    load_dotenv()
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
