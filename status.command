#!/bin/bash
# macOS: double-click in Finder, or run from Terminal. Says whether Prospero Companion is running.
exec /bin/bash "$(dirname "$0")/scripts/macos/status.sh" "$@"
