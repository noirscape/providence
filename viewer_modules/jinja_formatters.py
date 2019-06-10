import datetime
from flask_misaka import markdown 

def date(value):
    """Convert a Datetime object to something nicer for a string."""
    return value.strftime("%Y-%m-%d")

def datetime(value):
    """Convert a Datetime object to something that doesn't have miliseconds."""
    return value.strftime("%Y-%m-%d %H:%M:%S")

def markdown_discord(value):
    """Leverage misaka to generate something close to Discords own markdown."""
    return markdown(value, autolink=True, fenced_code=True, wrap=True, strikethrough=True)[:-3][3:]