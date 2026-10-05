# Development

[Back to the README](../README.md)

The backend is Python 3.12, FastAPI and SQLite; the interface is React 19, TypeScript and Vite.
Development and CI run on Linux and Windows, while Windows x64 is the launch target.

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt      # Windows: .\.venv\Scripts\python.exe
.venv/bin/python -m companion                                  # serves http://127.0.0.1:8775
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
```

Writes require the `x-companion-client: workspace` header, which the local interface sends.

## Installing on Windows

Double-click `install.bat` once. It finds Python 3.12+ and Node.js 22.12+ (installing them with
WinGet if they are missing), creates `.venv`, installs the locked dependencies and builds the
interface. Then double-click `launch.bat`: it starts the Companion on http://127.0.0.1:8775 and
opens it in the browser. Keep its window open while using the app; close it or press Ctrl+C to
stop. Launching again while it runs reuses the running copy, and a port taken by another program
is never stopped. `install.ps1 -CheckOnly` verifies an existing installation. CI runs the
installer and a launch on Windows.

The other root `.bat` files wrap scripts in `scripts/windows/`; `common.ps1` there holds the shared
port checks. `update.bat` runs `git pull --ff-only origin main` and then `install.ps1`; it refuses
while the Companion runs (Windows locks the files a reinstall replaces) or when the checkout is on
another branch. `status.bat` exits 0 when the Companion answers, 1 when nothing does and 2 when
another program holds the port. `stop.bat` ends the process tree that owns the port, but only after
the port answers as the Companion. `status.bat` and `stop.bat` take `-Port`, like `launch.bat`.
`create-shortcut.bat -Destination <folder>` writes the shortcut elsewhere, and names it
`Prospero Companion (checkout)` when the installed app already has a `Prospero Companion` shortcut.
`dev.bat` starts the backend with `uvicorn --reload` in its own window (or reuses one already
running), runs `npm run dev` in its own, and stops the backend it started when Vite exits.
Dev mode uses the real workspace unless `COMPANION_DATA_DIR` points elsewhere. CI runs
`scripts/windows/helpers-test.ps1` after the installer to exercise each helper through its `.bat`.

On Linux or macOS, follow the commands above and below, then run
`.venv/bin/python -m companion.launch`.

## Windows bundle

`python scripts/package/build_bundle.py` (after `npm run build`) assembles a self-contained
Windows x64 bundle in `build/package/`: `ProsperoCompanion-<version>-win-x64.zip` and
`SHA256SUMS.txt`. Inside, `Prospero Companion.cmd` starts the app with its own Python runtime, so
the machine needs neither Python, Node nor Prospero's Study.

| Part | Contents |
| --- | --- |
| `runtime/` | Python 3.12.10 from the python.org NuGet package, pinned by SHA-256, with the locked runtime dependencies as Windows wheels; pip and build headers removed |
| `app/` | `companion/`, the built interface in `dist/`, and `LICENSE` |
| `bundle.json` | Version, schema version, commit and the SHA-256 of every file |

The runtime's `python312._pth` fixes its import paths and the launcher runs it with `-I`, so
`PYTHONPATH`, `PYTHONHOME`, user site-packages and any other Python on the machine are ignored.
The workspace still lives in `%LOCALAPPDATA%\ProsperoCompanion`, separate from the program files.

The `Package` workflow builds the bundle on Windows and uploads it as a workflow artifact; it never
tags or publishes a release. A second job downloads it onto a fresh runner, checks the checksum,
unpacks it into a path with spaces and runs `scripts/package/smoke-test.ps1`: with no Python or
Node on `PATH`, poisoned Python variables and the Study's port 8765 taken, the app must verify
against `bundle.json`, answer on 8775, serve the interface, run on its bundled runtime, keep its
workspace and backups in its own data directory, and reuse the running copy on a second launch.

### Per-user installer

`scripts/package/companion.iss` wraps the unpacked bundle in an Inno Setup installer,
`ProsperoCompanion-<version>-win-x64-setup.exe`. It installs into
`%LOCALAPPDATA%\Programs\Prospero Companion` without administrator rights, adds a Start menu
shortcut (a desktop shortcut is optional) and a per-user uninstall entry, and offers to close a
running Companion before replacing files. An upgrade clears the old `app/` and `runtime/` first so
modules a release drops do not linger. The workspace in `%LOCALAPPDATA%\ProsperoCompanion` is
never installed, replaced or removed: uninstalling keeps it, and the app upgrades it on first open
as described under [Upgrades](#upgrades).

```powershell
ISCC.exe /DAppVersion=0.1.0 /DSourceDir=build\package\ProsperoCompanion /DOutputDir=build\package scripts\package\companion.iss
```

The `Package` workflow builds the setup from the bundle artifact, publishes both with one
`SHA256SUMS.txt` as the `windows-release` artifact, and runs `scripts/package/installer-test.ps1`
on a fresh runner: install, launch, install again as an upgrade, launch, restore a backup with the
installed launcher, launch, uninstall, with no Python or Node on `PATH`.

A `beside-the-study` job installs Prospero's Study from its repository (pinned to `bbcbde4`),
starts it on 8765, installs the Companion and runs `scripts/package/beside-study-test.ps1`: a
Companion pointed at the Study's port refuses and stops nothing, the Companion runs on 8775 while
the Study keeps answering, neither data folder holds the other's files, and the Study's database
never gains the Companion's identity marker.

The bundle and setup are not code signed yet, so Windows SmartScreen may warn on first launch. Signing is an
open release decision.

## Interface

Node 22 or newer. `npm run build` writes `dist/`, which the backend serves at
http://127.0.0.1:8775 when it exists. For development, run the backend and Vite side by side;
Vite serves http://127.0.0.1:5175 and forwards `/api` to the backend.

```sh
npm ci
npm run dev        # http://127.0.0.1:5175
npm run lint
npm test           # pure UI logic in tests/ui, run with Node's test runner
npm run build
```

Views live in `src/features/<view>/`. Logic that can be tested without a browser (turn grouping,
draft handling) sits in plain `.ts` modules beside the components that use it.

Settings is split into tabs listed in `src/features/settings/sections.ts`, with the section
headings and keywords its search box looks through. A new settings section goes in that list and
in `TabContent` in `Settings.tsx`. Tabs are deep-linkable: `go('settings/models')` from any view,
or `#settings/<tab>` in the address; an unknown tab, or one that needs a companion before there is
one, opens the first tab available.

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

### Upgrades

The marker also records the schema version, the app version and a digest of `schema.sql` plus
`ADDED_COLUMNS`, so any schema change is noticed without anyone bumping a number. When a workspace
was written with a different digest, `companion/upgrade.py` runs before the server listens:

1. A workspace from a newer schema version, or another app's database, is refused untouched.
2. A verified backup in the original schema is written to `backups/pre-upgrade-<time>.zip`
   (the three most recent are kept).
3. The upgrade runs on a copy, which must pass `PRAGMA integrity_check`.
4. Only then does the copy replace the workspace. On any failure the original is left exactly as
   it was and the launcher names the backup, which restores like any other.

Bump `SCHEMA_VERSION` only when older releases must refuse the new schema.

### Backups and restore

`POST /api/backups` writes `backups/companion-<time>.zip` (archive format 2): the database snapshot
plus the files its records name, at their workspace paths and each with its SHA-256 in
`manifest.json`: finished images (`images/`, `images/raw/`) and adapters that have not been removed
(`lora/adapters/`). Training reference pictures (`lora/references/`) are included only with
`?include_datasets=true`. Training work folders (`lora/runs/`, checkpoints and trainer logs) are
never included; a chosen checkpoint is already copied into `lora/adapters/`.

Restoring checks the marker, the schema version and every digest before writing anything, refuses
any path outside those folders, and then checks each record's file: completed images, reference
pictures and adapters (with their digests), and whether the selected appearance version's adapter
came back. The restored workspace is paused for review: automatic memory, background activity and
automatic images are off, saved keys and context tool approvals are dropped, queued or running
images and evaluations become interrupted, and a running training job becomes interrupted without
its old process id. Nothing resumes until the user reviews it.

In the app, Settings > Backups lists the archives in `backups/` (`GET /api/backups`, read from
their manifests) and **Restore…** chooses one (`POST /api/backups/{name}/restore`, which verifies
it in full first and can be cancelled with `DELETE /api/backups/restore`). The running app cannot
replace its own open workspace, so the choice is recorded in `pending-restore.json` and the
launcher applies it on the next start, before the workspace opens; the request is consumed whether
or not the restore succeeds, so a failure is reported once and never retried. Outside the app, close
it and run the launcher with `--restore <backup.zip>` (`"Prospero Companion.cmd" --restore <file>`
in the bundle). The current workspace moves to
`replaced-<time>/` beside it, not deleted, and moves back if the restore fails. Its deletion
records then apply to the restored workspace, so memories deleted and messages redacted after the
backup was made stay gone (PRD M5). Pre-upgrade backups hold only the database, since an upgrade
never changes media.

### Logs

`python -m companion.launch` logs to its window and to `logs/companion.log` in the data directory
(1 MB, three older files kept). Request logging is off, since a URL can carry a search query, and
`companion/logs.py` masks anything shaped like a credential (bearer tokens, `api_key=` values,
`sk-`/`hf_`-style keys) in messages and tracebacks before a line is written. The app itself never
logs message text.

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
| `companion/providers/scheduling.py` | `server/providers/scheduling.py` | Companion work kinds |
| `companion/providers/chat.py` | `server/providers/http.py`, `completion.py` | Conversation messages; token-limit and filter stops stay visible incomplete replies |
| `companion/providers/config.py` | `server/providers/config.py` | No LM Studio native protocol; Companion environment fallbacks |
| `companion/providers/capabilities.py` | `server/providers/capabilities.py` | No native protocol or safety margin |
| `companion/providers/requests.py` | `server/providers/requests.py` | System text plus alternating messages |
| `companion/providers/events.py` | `server/providers/events.py` | Companion `Chunk` with a normalized finish reason |
| `companion/providers/discovery.py`, `discovery_errors.py` | same files | No native model list |
| `companion/providers/codex.py` | `server/providers/codex.py` | Conversation sent as one transcript |
| `companion/providers/vault.py` | `server/providers/vault.py` | Companion credential service; delete; in-memory vault for tests |
| `companion/providers/urls.py` | `server/providers/config.py` | URL checks only |
| `companion/text_models.py`, `text_model_routes.py` | `server/profiles.py`, `profile_routes.py`, `roles.py` | Unversioned profiles; workspace job assignments |
| `src/features/settings/models/` | `src/features/models/` | Opens in Settings, not a dialog; no native protocol |
| `companion/database.py`, `errors.py`, `models.py` | `server/database.py`, `errors.py`, `models.py` | Identity marker and Companion helpers |
| `src/api.ts` | `src/api.ts` | Companion client header; offline and error codes |
| `src/styles.css` (palette, type, focus) | `src/styles.css` | Companion layout; one palette |
| `eslint.config.js`, `tsconfig.json` | same files | Companion paths |
| `companion/launch.py` | `scripts/launch_interface.py` | Companion identity, port and health check |
| `install.bat`, `install.ps1`, `launch.bat`, `start.ps1` | same files | Companion name, checks and launcher |
| `companion/life/chance.py` | `server/mechanics/randomness.py` (`Draws`), `server/mechanics/table_engine.py` (`face`, `resolve`) | `Draws` unchanged; tables are plain dicts with no versions, disabled tables or excluded rows |
| `tests/test_study_import.py` (`STUDY_SCHEMA`) | `server/schema.sql` | Library, story, Sidebar, profile and backup tables only, as a test fixture |

The Study's `assemble_memory` was not copied: it assumes an accepted Story path. The Companion
context builder in `companion/memory/context.py` replaces it.
