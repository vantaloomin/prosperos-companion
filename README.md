# Prospero Companion

A standalone companion application derived from the Companion Mode concept in [Prospero's Study](https://github.com/vantaloomin/prosperos-study). The backend covers workspace identity, character versions, conversation, typed personal memory, committed life events and backups. The local interface covers conversation with streaming replies, character creation and editing, memories, settings, Today and the private Feed.

## Which folder is for you

| Folder | Who it is for |
| --- | --- |
| [`Windows`](Windows) | Running the Companion on a Windows PC. Double-click `install.bat` once, then `launch.bat`. |
| [`Mac`](Mac) | Running it on a Mac. Double-click `install.command` once, then `launch.command`; see [Installing on a Mac](Program/docs/macos.md), including what macOS shows the first time. |
| [`Program`](Program) | The app itself: code, interface, tests, build scripts and docs. You never need to open it to use the Companion. |

On Windows you can instead run `ProsperoCompanion-<version>-win-x64-setup.exe` (no administrator rights, no Python or Node needed) and start Prospero Companion from the Start menu. Until releases are published, the setup is a build artifact of the `Package` workflow. See [Development](Program/docs/development.md) for Linux.

| Script | What it does |
| --- | --- |
| `install.bat` | Finds or installs Python 3.12+ and Node.js 22.13+, installs the locked dependencies and builds the interface. Run once, and again after changing dependencies. |
| `launch.bat` | Starts the Companion on http://127.0.0.1:8775 and opens it in the browser. Keep its window open; close it to stop. |
| `update.bat` | Pulls the latest `main` and reruns the install. Close the Companion first. |
| `status.bat` | Says whether the Companion is running, and on which address. |
| `stop.bat` | Stops a running Companion, for when its window is lost. Never stops another program on the port. |
| `create-shortcut.bat` | Puts a Prospero Companion shortcut to `launch.bat` on the desktop. |
| `dev.bat` | Development mode: the backend reloads on Python changes and Vite serves http://127.0.0.1:5175 with live interface updates. |

Each script has a Mac twin in `Mac` with the same name ending in `.command`. Your companion's data never lives in this folder: it is in `%LOCALAPPDATA%\ProsperoCompanion` on Windows and `~/Library/Application Support/ProsperoCompanion` on a Mac.

- [Product requirements (draft)](Program/docs/product-requirements.md)
- [Backbone architecture](Program/docs/architecture.md)
- [Development](Program/docs/development.md)
- [Installing on a Mac](Program/docs/macos.md)
- [Models](Program/docs/models.md)
- [Character drafting](Program/docs/character-drafting.md)
- [Life simulation API](Program/docs/life-api.md)
- [World data](Program/docs/world-data.md)
- [Image generation](Program/docs/images.md)
- [Current context tools (MCP)](Program/docs/context-tools.md)
- [Character LoRA maker](Program/docs/lora.md) (hidden unless switched on)
- [Phone access](Program/docs/phone-access.md)
- [Acceptance status](Program/docs/acceptance-status.md)

Licensed under the GNU Affero General Public License v3.0, matching the Study code it reuses.
