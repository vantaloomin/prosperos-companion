"""Export a chat or the story as one file to keep: HTML or Markdown, built from the stored messages (Hit List #38).

The file is made here and handed to the browser as a download; nothing is sent anywhere else. It holds what
the chat shows: each message with who wrote it and when (in the user's timezone, as the app shows times), the
app's join and leave lines, voice notes as their transcripts, and the pictures sent either way. Deleted
messages, replies set aside or replaced by an edit, failed or stopped attempts, alternatives that are not the
chosen one and replies still being held for later are left out, as the chat leaves them out. The sidecar is
never stored, so it never appears.

HTML is one self-contained page: inline CSS, each picture embedded as a data: URI, every piece of text escaped,
and a Content-Security-Policy that loads nothing from anywhere. Markdown stays plain text: pictures are
described in place rather than embedded, because a chat's photos run to megabytes each and base64 in a .md
makes a file most editors and viewers struggle with; the note at the top points to the HTML export for them.
"""
import base64
import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from companion import chats, pictures
from companion.characters import for_timeline
from companion.clock import parse, stamp, zone
from companion.database import many, optional, settings
from companion.errors import DomainError, require
from companion.images import photos, storage
from companion.local_zone import valid
from companion.voice import notes as voice_notes

FORMATS = {'html': 'text/html; charset=utf-8', 'md': 'text/markdown; charset=utf-8'}
IMAGE_TYPES = frozenset(storage.TYPES.values())
YOU, NARRATOR = 'You', 'Narrator'
NAME_LIMIT = 80


@dataclass
class Picture:
    caption: str
    path: Path | None = None
    media_type: str = ''


@dataclass
class Entry:
    """One line of the transcript: a message (`speaker` set) or a note from the app (`speaker` empty)."""
    speaker: str
    text: str
    at: datetime
    mine: bool = False
    voice: bool = False
    pictures: list[Picture] = field(default_factory=list)


@dataclass
class Transcript:
    title: str
    kind: str
    zone: str
    exported_at: datetime
    entries: list[Entry]
    places: list[str] = field(default_factory=list)


# Reading the transcript ---------------------------------------------------------------------------

def user_zone(connection) -> str:
    return valid(settings(connection)['user_timezone']) or 'UTC'


def chat(database, thread_id: str) -> Transcript:
    """A companion's chat (its timeline's id, the one on screen) or a group chat (the group's id)."""
    now = database.clock.now()
    with database.connect() as connection:
        companion = for_timeline(connection, thread_id)
        if companion is not None:
            entries = companion_entries(database, connection, thread_id, companion['version']['name'], now)
            return Transcript(companion['version']['name'], 'chat', user_zone(connection), now, entries)
        group = optional(connection, 'SELECT * FROM group_chats WHERE id=?', (thread_id,))
        require(group is not None, 'This chat could not be found.', 404)
        from companion import groups
        return Transcript(groups.title(connection, group), 'group chat', user_zone(connection), now,
                          group_entries(connection, thread_id))


def companion_entries(database, connection, timeline_id: str, name: str, now) -> list[Entry]:
    """The user's messages and the replies the chat shows (the chosen, finished ones whose time has come)."""
    rows = many(connection, 'SELECT * FROM messages WHERE timeline_id=? AND redacted_at IS NULL AND superseded_at IS NULL '
                f"AND (role='user' OR ({chats.shown()})) ORDER BY seq", (timeline_id, stamp(now)))
    ids = [row['id'] for row in rows]
    sent = pictures.for_messages(connection, ids)
    made = photos.for_messages(connection, ids)
    voiced = voice_notes.for_messages(connection, ids)
    folder = pictures.folder_of(connection)
    entries = []
    for row in rows:
        mine = row['role'] == 'user'
        shown = [user_picture(folder, item) for item in sent.get(row['id'], [])]
        if row['id'] in made:
            shown.append(chat_photo(database, connection, made[row['id']]))
        entries.append(Entry(YOU if mine else name, row['text'], parse(row['created_at']), mine,
                             row['id'] in voiced, [item for item in shown if item]))
    return entries


def user_picture(folder: Path, row: dict) -> Picture:
    caption = row['description'] if row['status'] == 'seen' and row['description'] else ''
    path = folder / row['file']
    return Picture(caption, path if path.is_file() else None, row['media_type'])


def chat_photo(database, connection, photo: dict) -> Picture | None:
    """A photo the companion sent, once it was made; one still being made or that failed shows nothing."""
    if photo['ref'] is None:
        return None
    job = optional(connection, 'SELECT output_file FROM image_jobs WHERE id=?', (photo['ref'],))
    try:
        path = storage.path_of(database, job['output_file']) if job and job['output_file'] else None
    except FileNotFoundError:
        path = None
    if path is None:
        return None
    meme = ' / '.join(part for part in (photo['top_text'], photo['bottom_text']) if part)
    return Picture(meme or photo['summary'], path, storage.TYPES.get(path.suffix.lstrip('.'), ''))


def group_entries(connection, group_id: str) -> list[Entry]:
    rows = many(connection, "SELECT * FROM group_messages WHERE group_id=? AND status='complete' ORDER BY seq",
                (group_id,))
    return [Entry('' if row['author'] == 'app' else YOU if row['author'] == 'user' else row['name'], row['text'],
                  parse(row['created_at']), row['author'] == 'user') for row in rows]


def story(database) -> Transcript:
    """The story so far, told by the narrator; arriving somewhere is a note, as the story shows it."""
    from companion.world import changes, custom
    now = database.clock.now()
    with database.connect() as connection:
        rows = many(connection, "SELECT * FROM story_messages WHERE status='complete' ORDER BY seq")
        cities = custom.all_cities(connection)
        places = []
        for city_id in dict.fromkeys(row['city_id'] for row in rows):
            data = changes.resolve(city_id, cities)
            places.append(data['name'] if data else city_id)
        speakers = {'user': YOU, 'narrator': NARRATOR, 'scene': ''}
        entries = [Entry(speakers[row['role']], row['text'], parse(row['created_at']), row['role'] == 'user')
                   for row in rows]
        return Transcript('Story', 'story', user_zone(connection), now, entries, places)


# Words shared by both formats ---------------------------------------------------------------------

def local(transcript: Transcript, instant: datetime) -> datetime:
    return instant.astimezone(zone(transcript.zone))


def day_text(moment: datetime) -> str:
    return f'{moment:%A, %B} {moment.day}, {moment.year}'


def date_text(moment: datetime) -> str:
    return f'{moment:%B} {moment.day}, {moment.year}'


def time_text(moment: datetime) -> str:
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def span_text(transcript: Transcript) -> str:
    if not transcript.entries:
        return 'No messages yet'
    first, last = (date_text(local(transcript, entry.at)) for entry in (transcript.entries[0], transcript.entries[-1]))
    return first if first == last else f'{first} – {last}'


def summary_lines(transcript: Transcript) -> list[str]:
    kind = transcript.kind[:1].upper() + transcript.kind[1:]
    where = f" in {', '.join(transcript.places)}" if transcript.places else ''
    return [f'{kind}{where} · {span_text(transcript)}',
            f'Times are in {transcript.zone}. Exported from Prospero’s Companion on '
            f'{date_text(local(transcript, transcript.exported_at))}.']


def by_day(transcript: Transcript) -> list[tuple[str, list[Entry]]]:
    days: list[tuple[str, list[Entry]]] = []
    for entry in transcript.entries:
        day = day_text(local(transcript, entry.at))
        if not days or days[-1][0] != day:
            days.append((day, []))
        days[-1][1].append(entry)
    return days


def has_pictures(transcript: Transcript) -> bool:
    return any(entry.pictures for entry in transcript.entries)


# HTML ---------------------------------------------------------------------------------------------

STYLE = """
:root { color-scheme: light; }
body { margin: 0; background: #fbfaf7; color: #1f1d1a; font: 16px/1.55 Georgia, 'Times New Roman', serif; }
main { max-width: 42rem; margin: 0 auto; padding: 2rem 1.25rem 3rem; }
header { border-bottom: 1px solid #ddd6cb; margin-bottom: 1.5rem; padding-bottom: 1rem; }
h1 { margin: 0 0 .35rem; font-size: 1.75rem; font-weight: normal; }
.meta { margin: .1rem 0; color: #6b645a; font: 14px/1.5 system-ui, sans-serif; }
h2 { margin: 2rem 0 1rem; color: #6b645a; font: 600 13px/1.4 system-ui, sans-serif; letter-spacing: .04em;
  text-transform: uppercase; }
.message { margin: 0 0 1.1rem; break-inside: avoid; }
.message.mine { padding-left: .9rem; border-left: 3px solid #c9b99f; }
.who { margin: 0 0 .15rem; font: 14px/1.4 system-ui, sans-serif; }
.who strong { font-weight: 600; }
.who time, .tag { color: #6b645a; }
.message p { margin: 0 0 .5rem; overflow-wrap: anywhere; }
.note { margin: 1rem 0; color: #6b645a; font: italic 14px/1.5 system-ui, sans-serif; text-align: center; }
figure { margin: .4rem 0 .8rem; }
figure img { display: block; max-width: 100%; max-height: 28rem; height: auto; border-radius: 6px; }
figcaption, .missing { color: #6b645a; font: 13px/1.4 system-ui, sans-serif; margin-top: .3rem; }
@media print { body { background: #fff; } main { max-width: none; padding: 0; } h2 { break-after: avoid; } }
"""
POLICY = "default-src 'none'; img-src data:; style-src 'unsafe-inline'"


def escaped(text: str) -> str:
    return html.escape(text, quote=True)


def paragraphs(text: str) -> str:
    parts = [part for part in re.split(r'\n\s*\n', text.strip()) if part.strip()]
    return ''.join(f"<p>{'<br>'.join(escaped(line) for line in part.splitlines())}</p>" for part in parts)


def picture_html(picture: Picture) -> str:
    caption = f'<figcaption>{escaped(picture.caption)}</figcaption>' if picture.caption else ''
    if picture.path is None or picture.media_type not in IMAGE_TYPES:
        said = f': {escaped(picture.caption)}' if picture.caption else ''
        return f'<p class="missing">[A picture that is no longer in the app{said}]</p>'
    data = base64.b64encode(picture.path.read_bytes()).decode('ascii')
    return (f'<figure><img src="data:{picture.media_type};base64,{data}" alt="{escaped(picture.caption or "Picture")}">'
            f'{caption}</figure>')


def entry_html(transcript: Transcript, entry: Entry) -> str:
    moment = local(transcript, entry.at)
    if not entry.speaker:
        return f'<p class="note">{escaped(entry.text)} <time>{time_text(moment)}</time></p>'
    voice = ' <span class="tag">· voice note</span>' if entry.voice else ''
    return (f'<article class="message{" mine" if entry.mine else ""}"><p class="who"><strong>{escaped(entry.speaker)}'
            f'</strong> <time datetime="{moment.isoformat(timespec="minutes")}">{time_text(moment)}</time>{voice}</p>'
            f"{paragraphs(entry.text)}{''.join(picture_html(item) for item in entry.pictures)}</article>")


def to_html(transcript: Transcript) -> str:
    meta = ''.join(f'<p class="meta">{escaped(line)}</p>' for line in summary_lines(transcript))
    body = ''.join(f'<section><h2>{escaped(day)}</h2>{"".join(entry_html(transcript, entry) for entry in entries)}'
                   '</section>' for day, entries in by_day(transcript)) or '<p class="note">Nothing was said here yet.</p>'
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta http-equiv="Content-Security-Policy" content="{POLICY}">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{escaped(transcript.title)}</title><style>{STYLE}</style></head>'
            f'<body><main><header><h1>{escaped(transcript.title)}</h1>{meta}</header>{body}</main></body></html>\n')


# Markdown -----------------------------------------------------------------------------------------

BLOCK_START = re.compile(r'^(\s*)([#>+\-=|`~]|\d+[.)])')


def md_line(line: str) -> str:
    """A line of text that reads as itself: no HTML gets through, and nothing turns into a heading or a list."""
    return BLOCK_START.sub(r'\1\\\2', line.replace('<', '&lt;'))


def md_text(text: str) -> str:
    parts = [part for part in re.split(r'\n\s*\n', text.strip()) if part.strip()]
    return '\n\n'.join('  \n'.join(md_line(line) for line in part.splitlines()) for part in parts)


def md_name(name: str) -> str:
    return re.sub(r'([\\*_`\[\]])', r'\\\1', name.replace('<', '&lt;'))


def entry_md(transcript: Transcript, entry: Entry) -> str:
    moment = local(transcript, entry.at)
    if not entry.speaker:
        return f'*{md_line(entry.text)} ({time_text(moment)})*'
    voice = ' · voice note' if entry.voice else ''
    lines = [f'**{md_name(entry.speaker)}** · {time_text(moment)}{voice}  ', md_text(entry.text)]
    lines += [f"*[Picture{': ' + md_line(item.caption) if item.caption else ''}]*" for item in entry.pictures]
    return '\n\n'.join(line for line in lines if line)


def to_markdown(transcript: Transcript) -> str:
    lines = [f'# {md_line(transcript.title)}', '  \n'.join(summary_lines(transcript))]
    if has_pictures(transcript):
        lines.append('*Pictures are described here; the HTML export keeps the pictures themselves.*')
    days = by_day(transcript)
    for day, entries in days:
        lines += [f'## {day}', *(entry_md(transcript, entry) for entry in entries)]
    if not days:
        lines.append('*Nothing was said here yet.*')
    return '\n\n'.join(lines) + '\n'


# The file -----------------------------------------------------------------------------------------

def render(transcript: Transcript, kind: str) -> str:
    return to_html(transcript) if kind == 'html' else to_markdown(transcript)


def filename(transcript: Transcript, kind: str) -> str:
    """'Sam - chat - 2026-10-12.html': who or what, the kind of chat, and the day it was exported."""
    title = ' '.join(re.sub(r'[\x00-\x1f<>:"/\\|?*]', ' ', transcript.title).split())[:NAME_LIMIT].strip(' .')
    title = title or 'Export'
    parts = [title] if title.casefold() == transcript.kind else [title, transcript.kind]
    return ' - '.join([*parts, local(transcript, transcript.exported_at).date().isoformat()]) + f'.{kind}'


def disposition(name: str) -> str:
    """The name for every browser: a plain ASCII one, and the exact one for browsers that read filename*."""
    plain = name.encode('ascii', 'ignore').decode('ascii').strip() or f'export{Path(name).suffix}'
    return f'attachment; filename="{plain}"; filename*=UTF-8\'\'{quote(name, safe="")}'


def download(transcript: Transcript, kind: str) -> tuple[str, str, str]:
    """(body, media type, Content-Disposition) for the route."""
    if kind not in FORMATS:
        raise DomainError('Export as html or md.', 422)
    return render(transcript, kind), FORMATS[kind], disposition(filename(transcript, kind))
