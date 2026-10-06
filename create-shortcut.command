#!/bin/bash
# macOS: double-click in Finder, or run from Terminal. Adds a Prospero Companion app to ~/Applications that starts this checkout.
exec /bin/bash "$(dirname "$0")/scripts/macos/create-shortcut.sh" "$@"
