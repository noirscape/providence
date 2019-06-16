import viewer
import click
from flask_frozen import Freezer

viewer.app.config["FREEZER_RELATIVE_URLS"] = True

freezer = Freezer(viewer.app)

if __name__ == '__main__':
    with click.progressbar(
        freezer.freeze_yield(),
        item_show_func=lambda p: p.url if p else 'Done!') as urls:
        for url in urls:
            pass