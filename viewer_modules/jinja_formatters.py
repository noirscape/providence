import datetime

def date(value):
    """Convert a Datetime object to something nicer for a string."""
    return value.strftime("%Y-%m-%d")

def datetime(value):
    """Convert a Datetime object to something that doesn't have miliseconds."""
    return value.strftime("%Y-%m-%d %H:%M:%S")
