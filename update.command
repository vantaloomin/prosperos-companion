#!/bin/bash
# macOS: double-click in Finder, or run from Terminal. Pulls the latest main and reinstalls. Close Prospero Companion first.
exec /bin/bash "$(dirname "$0")/scripts/macos/update.sh" "$@"
