import os
from dotenv import load_dotenv


class Config(object):
    load_dotenv()

    SECRET_KEY = os.getenv("SECRET_KEY", "you-will-never-guess")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    ADMINS = ["dmitrys.test@yandex.ru"]

    POSTS_PER_PAGE = 25
