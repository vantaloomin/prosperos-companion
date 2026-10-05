# Development

[Back to the README](../README.md)

The backend is Python 3.12, FastAPI and SQLite. There is no interface yet; the API is the
product surface for now. Development and CI run on Linux and Windows, while Windows x64 is the
launch target.

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt      # Windows: .\.venv\Scripts\python.exe
.venv/bin/python -m companion                                  # serves http://127.0.0.1:8775
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
```

Writes require the `x-companion-client: workspace` header, which the local interface will send.

## Workspace and identity

The Companion has its own identity so it can run beside Prospero's Study without collisions:

| Item | Companion | Study |
| --- | --- | --- |
| Data directory | `%LOCALAPPDATA%\ProsperoCompanion` (Windows), `$XDG_DATA_HOME/prospero-companion` elsewhere; `COMPANION_DATA_DIR` overrides | `data/` in the checkout |
| Database | `companion.sqlite3`; `COMPANION_DB` overrides | `roleplay.sqlite3` (`ROLEPLAY_DB`) |
| Port | 8775 | 8765 |
| Credential service | `Prospero Companion` (`COMPANION_API_KEY` fallback) | `Roleplay Interface` |
| Backup marker | `prospero-companion-archive` | Study archive format |

Every workspace database carries an `app_identity` marker. Opening any other non-empty SQLite
file, including a Study database, is refused with a read-only check before anything is written.

## Code reused from Prospero's Study

Modules were copied from [prosperos-study](https://github.com/vantaloomin/prosperos-study) at
commit `bbcbde4` and now evolve independently. Each copied file names its source path and the
changes made.

| Companion file | Study source | Changes |
| --- | --- | --- |
| `companion/memory/retrieval.py` | `server/memory/retrieval.py` | Removed Story stopwords (`continue`, `story`); in-process memoization only |
| `companion/memory/hybrid_recall.py` | `server/memory/hybrid_recall.py` | Takes chunks and a read limit from the caller |
| `companion/memory/chunks.py` | `server/memory/chunks.py` | No persistent cache format |
| `companion/memory/cache.py` | `server/memory/cache.py` | Persistent index backing removed |
| `companion/memory/budget.py` | `server/memory/budget.py` | Estimates plain text |
| `companion/providers/scheduling.py` | `server/providers/scheduling.py` | Companion work kinds; one connection type |
| `companion/providers/chat.py` | `server/providers/http.py` | OpenAI-compatible streaming only |
| `companion/providers/vault.py` | `server/providers/vault.py` | Companion credential service; in-memory vault for tests |
| `companion/providers/urls.py` | `server/providers/config.py` | URL checks only |
| `companion/database.py`, `errors.py`, `models.py` | `server/database.py`, `errors.py`, `models.py` | Identity marker and Companion helpers |

The Study's `assemble_memory` was not copied: it assumes an accepted Story path. The Companion
context builder in `companion/memory/context.py` replaces it.
