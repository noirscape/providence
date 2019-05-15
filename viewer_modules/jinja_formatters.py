import datetime

def date(value):
    """Convert a Datetime object to something nicer for a string."""
    return value.strftime("%Y-%m-%d")