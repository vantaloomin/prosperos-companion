"""A picture a reply sent, changed by the user: another take of it, or taken out of the chat.

Another take keeps what the picture shows. A photo, selfie or view, or a meme an image model made, is the same
request with a new seed, classified and routed again like any other image (F6); the photo then follows the new
attempt, and a moment's feed post shows it too, since they share one picture. A meme on a template picks another
picture that fits its mood, and a reaction GIF another one found for its tag; the captions stay.

Removing takes the picture out of the chat and leaves the words: the reply said what it said. The row stays, so
the removal can be undone, and a moment's feed post keeps its own picture.
"""
import random

import httpx

from companion.database import decode, encode, one
from companion.errors import require
from companion.images import gifs, jobs, meme_pictures, photos


def reroll(database, message_id, vault=None) -> dict:
    photo = photos.get(database, message_id)
    require(photo is not None, 'This picture could not be found.', 404)
    require(photo['status'] not in jobs.ACTIVE, 'This picture is still being made.', 409)
    if photo['source'] == 'template':
        return another_template(database, message_id)
    if photo['source'] == 'gif':
        return another_gif(database, message_id, vault)
    require(photo['job_id'] is not None, 'No image service could take this picture. Check Settings > Images.', 409)
    with database.connect() as connection:
        job = one(connection, 'SELECT post_id, inputs FROM image_jobs WHERE id=?', (photo['job_id'],))
    inputs = {**decode(job['inputs']), 'seed': random.SystemRandom().randrange(1, 2**31)}
    made = jobs.enqueue(database, job['post_id'], 'retry', inputs=inputs, retry_of=photo['job_id'])
    with database.connect(write=True) as connection:
        connection.execute('UPDATE chat_photos SET job_id=? WHERE message_id=?', (made['id'], message_id))
    return photos.get(database, message_id)


def another_template(database, message_id) -> dict:
    with database.connect() as connection:
        row = one(connection, 'SELECT meme_picture FROM chat_photos WHERE message_id=?', (message_id,))
        classics = bool(jobs.image_settings(connection)['meme_formats'])
    shown = decode(row['meme_picture'])['id']
    pictures = meme_pictures.available(database.root, classics)
    moods = next((picture.moods for picture in pictures if picture.id == shown), ('any',))
    fits = [picture for picture in pictures if picture.id != shown and fitting(picture.moods, moods)]
    require(bool(fits), 'There is no other picture for this meme yet. Add your own in Settings > Images.', 409)
    picture = random.SystemRandom().choice(fits)
    with database.connect(write=True) as connection:
        connection.execute('UPDATE chat_photos SET meme_picture=?, summary=? WHERE message_id=?',
                           (encode(picture.view()), picture.about, message_id))
    return photos.get(database, message_id)


def fitting(moods, wanted) -> bool:
    """A "this, not that" pair only on its own format; anything else on a picture of its mood or of any mood."""
    if 'choice' in wanted:
        return 'choice' in moods
    return 'any' in moods or bool(set(moods) & set(wanted))


def another_gif(database, message_id, vault) -> dict:
    with database.connect() as connection:
        row = one(connection, 'SELECT gif FROM chat_photos WHERE message_id=?', (message_id,))
    shown = decode(row['gif'])
    found = gifs.kept(shown['tag']) or fresh_gifs(vault, shown['tag'])
    others = [gif for gif in found if gif.get('url') != shown['url']]
    require(bool(others), 'No other GIF came up for this one. Try again in a little while.', 409)
    gif = random.SystemRandom().choice(others)
    picked = {**{field: gif.get(field) or '' for field in ('url', 'width', 'height', 'page', 'still', 'title')},
              'tag': shown['tag']}
    with database.connect(write=True) as connection:
        connection.execute('UPDATE chat_photos SET gif=?, summary=COALESCE(NULLIF(?, \'\'), summary) WHERE message_id=?',
                           (encode(picked), picked['title'][:200], message_id))
    return photos.get(database, message_id)


def fresh_gifs(vault, tag) -> list[dict]:
    api_key = gifs.key(vault) if vault is not None and gifs.FETCH else None
    if not api_key:
        return []
    try:
        return gifs.search(api_key, tag, gifs.ASKED_WAIT)
    except (httpx.HTTPError, ValueError):
        return []


def remove(database, message_id, removed=True) -> dict:
    """Take the picture out of the chat, or with `removed` false put it back."""
    with database.connect(write=True) as connection:
        found = connection.execute('UPDATE chat_photos SET removed_at=? WHERE message_id=?',
                                   (database.now() if removed else None, message_id)).rowcount
    require(found > 0, 'This picture could not be found.', 404)
    return photos.get(database, message_id, removed=True)
