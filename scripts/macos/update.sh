#!/bin/bash
# Updates this checkout: pulls main, then reruns install.sh (locked dependencies and a fresh interface build).
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$COMPANION_ROOT" || exit 1

fail() {
    say_error "Update failed: $*"
    echo 'Your workspace in ~/Library/Application Support/ProsperoCompanion was not touched.'
    exit 1
}

echo 'Prospero Companion - update'
# On a Mac without the command line tools, /usr/bin/git is a stub that offers to install them.
git --version >/dev/null 2>&1 || fail 'Git is not installed. Run "xcode-select --install" in Terminal, or update by downloading the project again.'
companion_state "$COMPANION_PORT"
[ "$STATE" = running ] && fail 'Prospero Companion is running. Close its window (or double-click stop.command), then update again.'
branch="$(git rev-parse --abbrev-ref HEAD 2>&1)" || fail "git rev-parse failed: $branch"
[ "$branch" = main ] || fail "This checkout is on '$branch'. update.command only updates main; switch with 'git switch main' first."
before="$(git rev-parse HEAD)"
git pull --ff-only origin main || fail 'git pull failed; see above.'
after="$(git rev-parse HEAD)"
if [ "$before" = "$after" ]; then
    echo 'Already up to date. Reinstalling to make sure everything matches.'
else
    echo "Updated ${before:0:7} to ${after:0:7}:"
    git log --oneline --no-decorate "$before..$after"
fi
/bin/bash "$COMPANION_ROOT/scripts/macos/install.sh" || fail 'The reinstall failed; see above.'
