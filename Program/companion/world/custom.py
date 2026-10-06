"""The user's own cities (PRD W5), stored in the workspace so backups and restores carry them.

A user city is validated exactly like a built-in one, so every generator works on it. Ids are
shared with the built-in cities and cannot shadow them.
"""
from pydantic import ValidationError

from companion.characters import current
from companion.database import decode, encode, optional
from companion.errors import DomainError, require
from companion.world import catalog

TEMPLATE_SOURCE = 'user'


def _invalid(error: Exception) -> DomainError:
    if isinstance(error, ValidationError):
        details = '; '.join(f"{'.'.join(map(str, issue['loc'])) or 'city'}: {issue['msg']}"
                            for issue in error.errors()[:8])
    else:
        details = str(error)
    return DomainError(f'This city is not valid. {details}', 422, 'invalid_city')


def check(definition: dict) -> dict:
    """The prepared city, or a DomainError listing what is wrong."""
    try:
        return catalog.prepare(definition)
    except (ValidationError, ValueError) as error:
        raise _invalid(error) from None


def _view(row) -> dict:
    data = catalog.prepare(decode(row['definition']))
    return data | {'builtin': False, 'origin': 'user', 'revision': row['revision'], 'created_at': row['created_at'],
                   'updated_at': row['updated_at']}


def all_cities(connection) -> dict[str, dict]:
    rows = connection.execute('SELECT * FROM world_cities ORDER BY id').fetchall()
    return {row['id']: _view(row) for row in rows}


def read(database) -> dict[str, dict]:
    with database.connect() as connection:
        return all_cities(connection)


def _definition(data: dict) -> dict:
    return {key: value for key, value in data.items()
            if key not in {'data_version', 'builtin', 'origin', 'pack_file', 'revision', 'created_at', 'updated_at'}}


def create(database, definition: dict) -> dict:
    data = check(definition)
    require(data['id'] not in catalog.cities(), f'{data["id"]!r} is a built-in or pack city. Choose another id.',
            409)
    with database.connect(write=True) as connection:
        exists = optional(connection, 'SELECT id FROM world_cities WHERE id=?', (data['id'],))
        require(exists is None, f'You already have a city with id {data["id"]!r}.', 409)
        now = database.now()
        connection.execute('INSERT INTO world_cities (id, definition, created_at, updated_at) VALUES (?, ?, ?, ?)',
                            (data['id'], encode(_definition(data)), now, now))
        return all_cities(connection)[data['id']]


def _not_builtin(city_id: str) -> None:
    require(city_id not in catalog.cities(), 'Built-in and pack cities cannot be changed here. Copy one to make it '
            'yours.', 409)


def update(database, city_id: str, definition: dict, expected_revision: int) -> dict:
    _not_builtin(city_id)
    data = check(definition)
    require(data['id'] == city_id, 'A city keeps its id. Copy it to use a new one.', 422)
    with database.connect(write=True) as connection:
        row = optional(connection, 'SELECT * FROM world_cities WHERE id=?', (city_id,))
        if row is None:
            raise DomainError(_missing(city_id), 404, 'unknown_city')
        require(row['revision'] == expected_revision, 'This city changed since you opened it. Reload it first.', 409)
        connection.execute('UPDATE world_cities SET definition=?, revision=revision+1, updated_at=? WHERE id=?',
                           (encode(_definition(data)), database.now(), city_id))
        return all_cities(connection)[city_id]


def delete(database, city_id: str) -> None:
    _not_builtin(city_id)
    with database.connect(write=True) as connection:
        if optional(connection, 'SELECT id FROM world_cities WHERE id=?', (city_id,)) is None:
            raise DomainError(_missing(city_id), 404, 'unknown_city')
        companion = current(connection)
        home = companion['version']['definition'].get('home_city') if companion else None
        require(home != city_id, 'Your companion lives in this city. Move them to another city first.', 409)
        connection.execute('DELETE FROM world_cities WHERE id=?', (city_id,))


def copy(database, source_id: str, new_id: str, name: str) -> dict:
    """Start a city of one's own from any city, built-in or the user's."""
    with database.connect() as connection:
        source = catalog.city(source_id, all_cities(connection))
    return create(database, _definition(source) | {'id': new_id, 'name': name, 'aliases': []})


def template(today: str) -> dict:
    """The smallest valid city, for the interface's "start from scratch"."""
    return {
        'schema_version': 1, 'id': 'my-city', 'name': 'My city', 'setting': 'original', 'era': 'modern',
        'region': 'Region', 'country': 'Country', 'timezone': 'UTC', 'summary': 'A few words about the city.',
        'lat': 0.0, 'lon': 0.0,
        'sources': {TEMPLATE_SOURCE: {'kind': 'user', 'title': 'Written by the user', 'license': 'User content',
                                      'retrieved': today}},
        'neighborhoods': [{'id': 'old-town', 'name': 'Old Town', 'summary': 'The oldest streets in the city.',
                           'vibe': ['historic'], 'lat': 0.0, 'lon': 0.0, 'housing': ['apartment'],
                           'walkability': 'high', 'source': TEMPLATE_SOURCE}],
        'places': [{'id': 'corner-cafe', 'name': 'The corner cafe', 'kind': 'cafe', 'neighborhood': 'old-town',
                    'summary': 'A small cafe on the main square.', 'cost': '$', 'setting': 'indoor',
                    'good_for': ['solo', 'friends'], 'day_parts': ['morning', 'afternoon'],
                    'source': TEMPLATE_SOURCE}],
    }


def _missing(city_id: str) -> str:
    return f'You have no city with id {city_id!r}.'
