"""Runs the built-in recall server and stops it when the Companion goes away.

Started as `python -I embedding_guard.py <server> <arguments...>` with a pipe on stdin. The Companion
never writes to the pipe; when it closes, because the Companion stopped the server or exited or was
killed, the guard stops the server too, so a model is never left holding memory in the background.
Only the standard library is used, so the script runs without the Companion on the import path.
"""
import subprocess
import sys
import threading

STOP_SECONDS = 5


def stop(server):
    if server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=STOP_SECONDS)
        except subprocess.TimeoutExpired:
            server.kill()


def watch(server):
    try:
        while sys.stdin.buffer.read(4096):
            pass
    except OSError:
        pass
    stop(server)


def main(command: list[str]) -> int:
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    server = subprocess.Popen(command, stdin=subprocess.DEVNULL, creationflags=flags)
    threading.Thread(target=watch, args=(server,), daemon=True).start()
    return server.wait()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
