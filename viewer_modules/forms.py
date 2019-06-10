from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, SelectField, IntegerField, DateField, validators

class GeneralSearchForm(FlaskForm):
    choices = [("DMs", "DMs"), ("Guilds", "Guilds")]
    search_choices = SelectField("Possiblities", choices=choices)
    text = StringField('Text', [validators.Optional()])
    author = IntegerField('Author ID', [validators.Optional()])
    submit = SubmitField('Search', [validators.Optional()])
    channel_id = IntegerField("Channel ID", [validators.Optional()])
    date = DateField('Date', [validators.Optional()])
    guild_id = IntegerField('Guild ID', [validators.Optional()])
    attachment = BooleanField("Has attachment?")