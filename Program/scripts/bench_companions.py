"""How the app's own work grows as companions are added by switching to townsfolk (docs/scale.md).

Run from Program/:  python scripts/bench_companions.py [--max 100] [--speed 0.5] [--out results.json]

It builds a throwaway workspace in a temporary folder (nothing of yours is touched), creates a companion
in Baltimore, then repeatedly lives a week, picks someone met in town and makes them the main character,
the way a user would. At each checkpoint it times the requests that grow with the number of companions.
No model is used: replies come from the user's model service, which this does not measure.

`--speed` caps this process at a share of one CPU core (0.5 = half a core) to stand in for a slower
computer. It runs the benchmark as a child process: on Windows under a job object CPU rate limit, elsewhere
(or if Windows refuses the job) by pausing and resuming it.
`--score` prints only this computer's CPU score, to compare machines.
"""
import argparse
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHECKPOINTS = (1, 2, 5, 10, 25, 50, 100, 200, 400)
START = datetime(2026, 10, 5, 12, tzinfo=UTC)
WORKDAY = [{'days': [0, 1, 2, 3, 4], 'start': '09:00', 'end': '17:00', 'kind': 'work', 'label': 'Work'},
           {'days': list(range(7)), 'start': '23:00', 'end': '07:00', 'kind': 'sleep', 'label': 'Sleep'}]
HEADERS = {'X-Companion-Client': 'workspace'}


# Standing in for a slower computer ------------------------------------------------------------------

def cap_windows(speed: float):
    """Runs the benchmark as a child process under a job object CPU hard cap. Where Windows will not put it
    in a job (the console's own job can forbid it), the child is paused and resumed instead, as elsewhere."""
    import ctypes
    from ctypes import wintypes

    class Rate(ctypes.Structure):
        _fields_ = [('ControlFlags', wintypes.DWORD), ('CpuRate', wintypes.DWORD)]

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
    kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
    kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    child = subprocess.Popen([sys.executable, *sys.argv], env={**os.environ, 'BENCH_THROTTLED': '1'},
                             creationflags=0x4)  # CREATE_SUSPENDED: capped before it runs a line
    handle = kernel.OpenProcess(0x0100 | 0x0001 | 0x0800 | 0x0400, False, child.pid)  # SET_QUOTA, TERMINATE, SUSPEND_RESUME, QUERY
    job = kernel.CreateJobObjectW(None, None)
    # CpuRate is in 1/100 of a percent of the whole machine; one core is 1/cpu_count of it.
    rate = Rate(0x1 | 0x4, max(1, round(speed * 10000 / os.cpu_count())))  # ENABLE | HARD_CAP
    capped = bool(job and kernel.SetInformationJobObject(job, 15, ctypes.byref(rate), ctypes.sizeof(rate))
                  and kernel.AssignProcessToJobObject(job, handle))
    ntdll = ctypes.WinDLL('ntdll')
    ntdll.NtSuspendProcess.argtypes = ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
    ntdll.NtResumeProcess(handle)
    if capped:
        print('CPU capped with a job object.', flush=True)
        child.wait()
    else:
        print(f'No job object (error {ctypes.get_last_error()}); pausing and resuming instead.', flush=True)
        while child.poll() is None:
            time.sleep(0.1 * speed)
            ntdll.NtSuspendProcess(handle)
            time.sleep(0.1 * (1 - speed))
            ntdll.NtResumeProcess(handle)
    sys.exit(child.returncode)


def cap_posix(speed: float):
    """Runs the benchmark as a child process and pauses it for the rest of every 100 ms slice. The parent
    stays running, so a shell does not see a stopped job."""
    child = subprocess.Popen([sys.executable, *sys.argv], env={**os.environ, 'BENCH_THROTTLED': '1'})
    while child.poll() is None:
        time.sleep(0.1 * speed)
        try:
            child.send_signal(signal.SIGSTOP)
            time.sleep(0.1 * (1 - speed))
            child.send_signal(signal.SIGCONT)
        except ProcessLookupError:
            break
    sys.exit(child.returncode)


def cap(speed: float):
    if speed >= 1 or os.environ.get('BENCH_THROTTLED'):
        return None
    return cap_windows(speed) if platform.system() == 'Windows' else cap_posix(speed)


def cpu_score() -> float:
    """Simple Python work per second (thousands): compares single-core speed between computers."""
    best = 0.0
    for _ in range(3):
        began, total = time.perf_counter(), 0
        for number in range(400_000):
            total += hash((number, str(number))) % 7
        best = max(best, 400 / (time.perf_counter() - began))
    return round(best, 1)


# The workspace -------------------------------------------------------------------------------------

def make_app(path: Path, clock):
    from companion.life import encounters
    from companion.main import create_app
    from companion.providers.vault import MemoryVault
    encounters.ACTIVE = True
    return create_app(path, clock=clock, vault=MemoryVault(), life_tasks=False)


def ok(response):
    if response.status_code != 200:
        raise RuntimeError(f'{response.request.method} {response.request.url.path}: {response.text[:300]}')
    return response.json()


def live(client, clock, days: int):
    for _ in range(days):
        clock.instant += timedelta(days=1)
        ok(client.post('/api/life/reconcile', json={}))


def unmet(client) -> list[dict]:
    return [item for item in ok(client.get('/api/life/townsfolk')) if not item.get('cast')]


def add_companion(client, clock) -> bool:
    """Live until someone new is met in town, then make them the main character. A companion who meets
    nobody new for three weeks hands over to one of the others, as a user might switch between them."""
    for attempt in range(12):
        live(client, clock, 7)
        if known := unmet(client):
            key = known[-1]['key']
            drafted = ok(client.get('/api/companion/cast/draft', params={'key': key}))
            ok(client.post('/api/companion/cast/switch', json={'key': key, 'definition': drafted['definition']}))
            return True
        if attempt % 3 == 2:
            members = [member for member in ok(client.get('/api/companion/cast'))['members'] if not member['main']]
            if members:
                pick = members[attempt // 3 % len(members)]
                ok(client.post('/api/companion/cast/focus', json={'companion_id': pick['id']}))
    return False


def timed(action, runs: int = 5) -> float:
    times = []
    for _ in range(runs):
        began = time.perf_counter()
        action()
        times.append((time.perf_counter() - began) * 1000)
    return round(statistics.median(times), 1)


def measure(client, clock, path: Path) -> dict:
    from fastapi.testclient import TestClient

    def next_day():
        clock.instant += timedelta(days=1)
        ok(client.post('/api/life/reconcile', json={}))

    def cold_start():
        with TestClient(make_app(path, clock), headers=HEADERS) as fresh:
            ok(fresh.get('/api/companion'))

    return {
        'next_day_ms': timed(next_day),
        'around_town_ms': timed(lambda: ok(client.get('/api/life/townsfolk'))),
        'today_ms': timed(lambda: ok(client.get('/api/today'))),
        'chat_prompt_ms': timed(lambda: ok(client.get('/api/context/preview'))),
        'companions_list_ms': timed(lambda: ok(client.get('/api/companion/cast'))),
        'story_ms': timed(lambda: ok(client.get('/api/story'))),
        'start_up_ms': timed(cold_start, 3),
        'database_mb': round(sum(item.stat().st_size for item in path.parent.glob(path.name + '*')) / 2 ** 20, 1),
    }


def run(limit: int, out: Path | None, speed: float):
    from fastapi.testclient import TestClient

    from companion.clock import FixedClock
    clock = FixedClock(START)
    results = {'computer': {'system': platform.platform(), 'processor': platform.processor(), 'python':
                            platform.python_version(), 'speed': speed, 'cpu_score': cpu_score()}, 'rows': []}
    print(json.dumps(results['computer']))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'companion.sqlite3'
        with TestClient(make_app(path, clock), headers=HEADERS) as client:
            ok(client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York', 'schedule': WORKDAY,
                                                    'location': 'Fells Point, Baltimore', 'personality': 'Warm.'}))
            client.put('/api/settings', json={'story_mode': True})  # Opt-in where the setting exists.
            count, began = 1, time.perf_counter()
            stuck = False
            for checkpoint in [point for point in CHECKPOINTS if point <= limit]:
                while count < checkpoint and not stuck:
                    stuck = not add_companion(client, clock)
                    count += 0 if stuck else 1
                if stuck:
                    print(f'Nobody new was met in twelve weeks at {count} companions; stopping.')
                row = {'companions': count, 'simulated_days': (clock.instant - START).days,
                       'setup_s': round(time.perf_counter() - began, 1), **measure(client, clock, path)}
                results['rows'].append(row)
                print(json.dumps(row), flush=True)
                if out:
                    out.write_text(json.dumps(results, indent=2), encoding='utf-8')
                if stuck:
                    break
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--max', type=int, default=100, help='companions to reach (default 100)')
    parser.add_argument('--speed', type=float, default=1.0, help='share of one CPU core, e.g. 0.5 (default: no cap)')
    parser.add_argument('--out', type=Path, help='write results as JSON here as they come')
    parser.add_argument('--score', action='store_true', help="print this computer's CPU score and stop")
    args = parser.parse_args()
    cap(args.speed)  # with a cap, this runs the benchmark in a capped child process and exits with it
    if args.score:
        print(json.dumps({'cpu_score': cpu_score(), 'speed': args.speed}))
        return
    run(args.max, args.out, args.speed)


if __name__ == '__main__':
    main()
