from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    SubmitField,
    TextAreaField,
    SelectMultipleField,
)
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User, followers
from flask import request
from sqlalchemy import and_


class EditProfileForm(FlaskForm):
    avatar = FileField(
        "Upload Image", validators=[FileAllowed(["jpg", "png", "jpeg", "gif"])]
    )
    username = StringField("Username", validators=[DataRequired()])
    about_me = TextAreaField("About me", validators=[Length(min=0, max=140)])
    submit = SubmitField("Submit")

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError("Please use a different username.")


class PostForm(FlaskForm):
    photo = FileField(
        "Upload Image", validators=[FileAllowed(["jpg", "png", "jpeg", "gif"])]
    )
    post = TextAreaField(
        "Say something", validators=[DataRequired(), Length(min=1, max=1000)]
    )
    submit = SubmitField("Submit")


class EmptyForm(FlaskForm):
    submit = SubmitField("Submit")


class SearchForm(FlaskForm):
    q = StringField("Search", validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if "formdata" not in kwargs:
            kwargs["formdata"] = request.args
        if "meta" not in kwargs:
            kwargs["meta"] = {"csrf": False}
        super(SearchForm, self).__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField(
        "Message", validators=[DataRequired(), Length(min=0, max=700)]
    )
    submit = SubmitField("Submit")


class CreateChatForm(FlaskForm):
    name = StringField("Chat Name", validators=[DataRequired()])
    participants = SelectMultipleField(
        "Participants", coerce=int, validators=[DataRequired()]
    )
    submit = SubmitField("Create Chat")

    def __init__(self, current_user, *args, **kwargs):
        super(CreateChatForm, self).__init__(*args, **kwargs)
        mutual_followers = (
            User.query.join(
                followers,
                and_(
                    followers.c.follower_id == current_user.id,
                    followers.c.followed_id == User.id,
                ),
            )
            .filter(User.followed.any(id=current_user.id))
            .all()
        )
        self.participants.choices = [
            (user.id, user.username) for user in mutual_followers
        ]
