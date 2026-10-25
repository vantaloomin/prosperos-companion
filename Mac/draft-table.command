#!/bin/bash
# macOS: double-click in Finder, or run from Terminal. Starts Prospero Companion if it is not running and opens Prospero's Draft Table, the place builder, in the browser.
exec /bin/bash "$(dirname "$0")/../Program/scripts/macos/launch.sh" --draft "$@"
