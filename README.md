## Providence

The discord logger for paranoid people.

## Usage

Currently, the project is in early alpha.

There is no viewer or logger yet.

## Installation

- Install postgres
- Make a database and user.
- Rename `config.yml.example` to `config.yml`.
- Set connection url in `config.yml`.
- Run `alembic upgrade head`

## Stuff that won't be logged

- Reactions
- Voice channel joins and leaves.

## Credits

- Jisagi: Base database design.
- ihaveamac: Panopticon.