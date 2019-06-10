## Providence

The discord logger for paranoid people.

## Installation

- Install postgresql
- Create a user for peer connection (this will look like `sudo -u postgres createuser kyoko --interactive`). Say yes if asked if this will be a root user and if it can create databases.
- Create a database for Providence (for example `createdb providence`)
- Fill out `config.yml`
    - token: Place your accounts token here.
    - bot: Set to False if you're using a userbot. Otherwise, set to True.
    - database_url: Set this as the connection to your Postgres database (if you've been following along, this will be: `postgres://user@localhost/providence`)
    - local_avatars: Set to True to store all avatars locally.
    - local_attachments: Set to True to store all attachments locally.
    - Changing any of the local_ options will affect future storage/updates of attachments and avatars but will not localize existing avatars and attachments.
- Install dependencies (`pip3 install -r requirements.txt`)
- Run alembic migrations (`alembic upgrade head`)
- Run a logger process (`python logger.py`)
- Run a viewer process (Use a WSGI server. To for example use gunicorn, run `gunicorn -w 4 -b 127.0.0.1:4000 viewer:app`)
- It is recommended to run the logger and viewer processes using something like supervisord.

## Updating

- Shut down the logger and viewer process
- `git pull` the repository.
- Run alembic migrations (`alembic upgrade head`)
- Start the logger and viewer processes again.

## Stuff that won't be logged

- Reactions
- Voice channel joins and leaves.

## LICENSE

(c) Valentijn "noirscape" V. 2019, All Rights Reserved

This program uses various external libraries which are under their own license. These libraries are obtained through PIP and their license can be verified on PyPi by cross-referencing requirements.txt

Aside from that, this program makes use of the getskeleton.io framework, which is under the MIT. Where used, this library has been credited.

I might relicense this to something FOSS later. Until then, contact me if you want to use this code as a base.

## Credits

- Jisagi: Base database design.
- ihaveamac: Panopticon.