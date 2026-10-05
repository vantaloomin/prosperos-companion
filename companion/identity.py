"""Application identity kept separate from Prospero's Study.

The Companion never shares a data directory, credential service, port or archive
marker with the writing product, so running both cannot route one into the other.
"""
import os
import sys
from pathlib import Path

APP_ID = 'prospero-companion'
APP_NAME = 'Prospero Companion'
VERSION = '0.1.0'
SCHEMA_VERSION = 1
CREDENTIAL_SERVICE = 'Prospero Companion'
ARCHIVE_FORMAT = 'prospero-companion-archive'
ARCHIVE_VERSION = 1
DEFAULT_PORT = 8775
CLIENT_HEADER = 'x-companion-client'
DATA_ENV = 'COMPANION_DATA_DIR'
DATABASE_ENV = 'COMPANION_DB'


def data_dir() -> Path:
    if os.environ.get(DATA_ENV):
        return Path(os.environ[DATA_ENV])
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local'
        return Path(base) / 'ProsperoCompanion'
    base = os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share'
    return Path(base) / APP_ID


def database_path() -> Path:
    return Path(os.environ.get(DATABASE_ENV) or data_dir() / 'companion.sqlite3')
