#!/bin/bash
# Exercises the macOS checkout scripts (status, stop, launch, create-shortcut, dev, update) through their
# .command files after install.command. Used by CI. Expects COMPANION_DATA_DIR to point at a scratch
# workspace. The update check rewires this checkout's origin to a local repository, so run it on a
# throwaway checkout only.
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"
cd "$COMPANION_ROOT" || exit 1
temp="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
python="$COMPANION_ROOT/.venv/bin/python"

check() {
    # check <description> <command...>: the command must succeed.
    local description="$1"; shift
    if "$@"; then echo "ok  $description"; else say_error "FAILED  $description"; exit 1; fi
}

exits() {
    # exits <code> <script> [args]: runs a .command and compares its exit code.
    local expected="$1" script="$2"; shift 2
    "$COMPANION_ROOT/$script" "$@" >"$temp/helper-out.txt" 2>&1
    local code=$?
    cat "$temp/helper-out.txt"
    [ "$code" -eq "$expected" ]
}

background=''
cleanup() { [ -n "$background" ] && stop_tree "$background" 2>/dev/null; }
trap cleanup EXIT

# status, stop and launch
check 'status.command reports a stopped Companion with exit code 1' exits 1 status.command
check 'stop.command with nothing running succeeds and stops nothing' exits 0 stop.command
"$COMPANION_ROOT/launch.command" --no-browser >"$temp/launch-out.txt" 2>&1 &
background=$!
check 'launch.command answers on 8775' wait_for_state running 8775
check 'status.command reports the running Companion with exit code 0' exits 0 status.command
check 'stop.command stops the running Companion' exits 0 stop.command
check 'port 8775 is free after stop.command' wait_for_state stopped 8775 4
check 'launch.command reports a missing option' exits 1 launch.command --nonsense

# Another program on the port is reported and never stopped.
"$python" -m http.server 8790 --bind 127.0.0.1 >/dev/null 2>&1 &
background=$!
check 'a foreign server holds 8790' wait_for_state foreign 8790
check 'status.command reports a port held by another program with exit code 2' exits 2 status.command --port 8790
check 'stop.command refuses to stop another program' exits 1 stop.command --port 8790
check 'the other program is still running' kill -0 "$background"
stop_tree "$background"; background=''

# create-shortcut
apps="$temp/applications"
mkdir -p "$apps"
check 'create-shortcut.command succeeds' exits 0 create-shortcut.command --destination "$apps"
app="$apps/Prospero Companion.app"
check 'the app has a valid Info.plist' plutil -lint "$app/Contents/Info.plist"
check "the app opens this checkout's launch.command" grep -qF "$(printf '%q' "$COMPANION_ROOT/launch.command")" "$app/Contents/MacOS/launch"
check 'the app launcher is executable' test -x "$app/Contents/MacOS/launch"
check 'running create-shortcut.command again keeps one app' exits 0 create-shortcut.command --destination "$apps"
check '...under the same name' test ! -e "$apps/Prospero Companion (checkout).app"
printf '#!/bin/bash\nexec open -a TextEdit\n' > "$app/Contents/MacOS/launch"
check 'create-shortcut.command succeeds beside an installed app' exits 0 create-shortcut.command --destination "$apps"
check 'the existing app is left alone' grep -q TextEdit "$app/Contents/MacOS/launch"
check 'the checkout app gets its own name' test -x "$apps/Prospero Companion (checkout).app/Contents/MacOS/launch"

# dev: backend plus Vite, with /api forwarded to the backend
"$COMPANION_ROOT/dev.command" --no-browser >"$temp/dev-out.txt" 2>&1 &
background=$!
check 'dev mode starts the backend on 8775' wait_for_state running 8775
page_has() {
    local tries=120
    while [ "$tries" -gt 0 ]; do
        curl --noproxy '*' --silent --max-time 3 "$1" | grep -q "$2" && return 0
        sleep 0.5; tries=$((tries - 1))
    done
    return 1
}
check 'Vite serves the interface on 5175' page_has 'http://127.0.0.1:5175/' 'Prospero Companion'
check 'Vite forwards /api to the backend' page_has 'http://127.0.0.1:5175/api/health' "$COMPANION_APP_ID"
# A background job ignores SIGINT, so stand in for Ctrl+C with SIGTERM; dev.sh traps both.
kill -TERM "$background"
wait "$background" 2>/dev/null
background=''
check 'closing dev mode stops its backend' wait_for_state stopped 8775
check 'closing dev mode stops Vite' test -z "$(port_owner 5175)"

# update: fast-forward from a local origin, then reinstall. CI checkouts are shallow, so the local
# origin accepts shallow pushes.
git config --global user.email ci@example.invalid
git config --global user.name CI
remote="$temp/update-origin.git"
clone="$temp/update-clone"
git init --quiet --bare "$remote"
git -C "$remote" config receive.shallowUpdate true
git checkout --quiet -B main
git push --quiet "$remote" HEAD:refs/heads/main
git clone --quiet --branch main "$remote" "$clone"
echo pulled > "$clone/update-marker.txt"
git -C "$clone" add update-marker.txt
git -C "$clone" commit --quiet -m 'Marker for the update test'
git -C "$clone" push --quiet origin main
git remote set-url origin "$remote"
check 'update.command pulls main and reinstalls' exits 0 update.command
check 'the new commit was pulled' test -f update-marker.txt
check 'the interface was rebuilt' test -f dist/index.html
"$python" -m companion.launch --no-browser >/dev/null 2>&1 &
background=$!
check 'the Companion launches after updating' wait_for_state running 8775
check 'update.command refuses while the Companion runs' exits 1 update.command
stop_tree "$background"; background=''
wait_for_state stopped 8775 >/dev/null
git checkout --quiet -b elsewhere
check 'update.command refuses a branch other than main' exits 1 update.command

echo 'All checkout helper checks passed.'
