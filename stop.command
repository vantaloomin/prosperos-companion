#!/bin/bash
# macOS: double-click in Finder, or run from Terminal. Stops a running Prospero Companion, never another program on its port.
exec /bin/bash "$(dirname "$0")/scripts/macos/stop.sh" "$@"
