import click
import viewer
import logger
import db
import eralchemy
from flask_frozen import Freezer

@click.group()
def cli():
    pass

@cli.command()
def gen_erd():
    """Generate the database ERD using ERAlchemy."""
    eralchemy.render_er(db.Base, "erd.png")

@cli.command()
def freeze():
    """Freeze the viewer data using Frozen-Flask.
    
    Output data will be in the build/ directory."""
    viewer.app.config["FREEZER_RELATIVE_URLS"] = True

    freezer = Freezer(viewer.app)

    with click.progressbar(
        freezer.freeze_yield(),
        item_show_func=lambda p: p.url if p else 'Done!') as urls:
        for url in urls:
            pass

@cli.command()
def run_logger():
    """Start the logger."""
    logger.main()

@cli.command()
def run_viewer():
    """Run the debugging server.
    
    You generally do NOT want to call this command in production. Run viewer:app in a WSGI server instead.
    """
    viewer.app.run()

if __name__ == "__main__":
    cli()