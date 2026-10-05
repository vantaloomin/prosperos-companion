# Prospero Companion

A standalone companion application derived from the Companion Mode concept in [Prospero's Study](https://github.com/vantaloomin/prosperos-study). The backend covers workspace identity, character versions, conversation, typed personal memory, committed life events and backups. The local interface covers conversation with streaming replies, character creation and editing, memories, settings, Today and the private Feed.

On Windows, run `ProsperoCompanion-<version>-win-x64-setup.exe` (no administrator rights, no Python or Node needed) and start Prospero Companion from the Start menu. Until releases are published, the setup is a build artifact of the `Package` workflow. From a checkout, double-click `install.bat` once, then `launch.bat`. See [Development](docs/development.md) for other systems.

| Script | What it does |
| --- | --- |
| `install.bat` | Finds or installs Python 3.12+ and Node.js 22.12+, installs the locked dependencies and builds the interface. Run once, and again after changing dependencies. |
| `launch.bat` | Starts the Companion on http://127.0.0.1:8775 and opens it in the browser. Keep its window open; close it to stop. |
| `update.bat` | Pulls the latest `main` and reruns the install. Close the Companion first. |
| `status.bat` | Says whether the Companion is running, and on which address. |
| `stop.bat` | Stops a running Companion, for when its window is lost. Never stops another program on the port. |
| `create-shortcut.bat` | Puts a Prospero Companion shortcut to `launch.bat` on the desktop. |
| `dev.bat` | Development mode: the backend reloads on Python changes and Vite serves http://127.0.0.1:5175 with live interface updates. |

- [Product requirements (draft)](docs/product-requirements.md)
- [Backbone architecture](docs/architecture.md)
- [Development](docs/development.md)
- [Models](docs/models.md)
- [Character drafting](docs/character-drafting.md)
- [Life simulation API](docs/life-api.md)
- [World data](docs/world-data.md)
- [Image generation](docs/images.md)
- [Current context tools (MCP)](docs/context-tools.md)
- [Character LoRA maker](docs/lora.md)
- [Acceptance status](docs/acceptance-status.md)

Licensed under the GNU Affero General Public License v3.0, matching the Study code it reuses.
