# How many companions to keep

Every companion you have ever had keeps living in the background, and their whole history stays in the
database. This page shows how the app's own work grows as companions are added. It measures
everything except the model: chat replies take whatever time your model service takes, which is
usually seconds and the same with one companion or a hundred.

## Recommendation

| Computer | Comfortable | Notes |
|---|---|---|
| A recent desktop or laptop | 100 or more | Nothing measured passed a quarter of a second. |
| An older laptop (about a 2012 Core i3) | Up to about 50 | Still works at 100. A new day takes up to about a second, and opening the app and the Story tab take half a second. |

In both tests the town ran out of new people before the computer struggled. A single city's
townsfolk gave 71 to 247 companions, depending on who happened to be met. The database grows by
roughly half a megabyte per companion per year of their life, about 50 MB for 100 companions.

## How it was measured

`Program/scripts/bench_companions.py` builds a throwaway workspace in a temporary folder and creates
a companion in Baltimore. It then repeatedly lives a week, picks someone met in town and makes them
the main character, the way a user would. At 1, 2, 5, 10, 25, 50, 100, 200 and 400 companions it
times the requests that grow with their number. Each figure is the median of several runs.

| Column | What it is |
|---|---|
| New day | Living one more day for everyone (`/api/life/reconcile`). The app does this in the background as time passes. |
| Around town | Who is where in the city right now. |
| Chat prompt | Building the prompt for one chat reply, without the model (`/api/context/preview`). |
| Story | Opening the Story tab (only when Story mode is on). |
| Start-up | Opening the database when the app starts. |

`--speed 0.25` holds it to a quarter of one CPU core to stand in for a slower computer. On Windows it
uses a job object CPU hard cap, and elsewhere it pauses and resumes the process. A quarter of one
core of the test PC (Ryzen 9 9950X3D) is close to one core of a 2012 laptop Core i3. The cap is
enforced over short intervals, so requests that finish in a few milliseconds can slip under it. The
longer steps (new day, story, start-up) show the slowdown.

```
cd Program
python scripts/bench_companions.py --max 100 --out results.json
python scripts/bench_companions.py --max 100 --speed 0.25 --out capped.json
```

## Results

Windows 11, Ryzen 9 9950X3D, Python 3.12, 2026-10-07. Times are in milliseconds.

**Full speed** (stopped at 71: nobody new was met in twelve weeks)

| Companions | New day | Around town | Chat prompt | Story | Start-up | Database |
|---|---|---|---|---|---|---|
| 1 | 192 | 4 | 9 | 32 | 65 | 1.2 MB |
| 10 | 179 | 8 | 13 | 39 | 54 | 6.9 MB |
| 25 | 165 | 10 | 12 | 35 | 42 | 16 MB |
| 50 | 235 | 16 | 37 | 61 | 64 | 30 MB |
| 71 | 202 | 16 | 37 | 45 | 44 | 44 MB |

**A quarter of one core** (about a 2012 Core i3)

| Companions | New day | Around town | Chat prompt | Story | Start-up | Database |
|---|---|---|---|---|---|---|
| 1 | 587 | 3 | 6 | 27 | 49 | 1.2 MB |
| 10 | 573 | 6 | 10 | 31 | 54 | 5.6 MB |
| 25 | 584 | 10 | 17 | 64 | 61 | 12 MB |
| 50 | 1,097 | 19 | 38 | 489 | 117 | 26 MB |
| 100 | 731 | 35 | 62 | 504 | 504 | 53 MB |

A Linux cloud machine gave the same picture. At full speed it reached 247 companions, with a new
day taking at most about a quarter of a second, a chat prompt 94 ms and a 168 MB database.

## Worlds and automatic backups

Each world is its own database, and only the world the user is in lives day to day; another world catches up
when the user goes back to it. `Program/scripts/bench_worlds.py` grows a first world to 25 companions, then adds
personas and worlds (each with its own townsfolk and starter companion, living a month), and at 1, 2, 5, 10, 25
and 50 worlds times the things that grow with them.

```
cd Program
python scripts/bench_worlds.py --max 50 --heavy 25 --out worlds.json
```

Linux cloud machine (4 cores, shared with other tests), Python 3.13, 2026-10-10. Times are in milliseconds.

| Worlds | Worlds page | Switch | Start-up | Back up every world | All databases | All automatic backups | Largest backup |
|---|---|---|---|---|---|---|---|
| 1 | 17 | 16 | 122 | 3,305 | 86 MB | 12 MB | 12 MB |
| 5 | 35 | 90 | 120 | 3,873 | 98 MB | 13 MB | 12 MB |
| 10 | 133 | 97 | 102 | 4,733 | 109 MB | 14 MB | 12 MB |
| 25 | 120 | 113 | 98 | 5,955 | 139 MB | 16 MB | 13 MB |
| 50 | 637 | 213 | 126 | 10,806 | 189 MB | 19 MB | 13 MB |

Fifty worlds are fine. The Worlds page reads every world's companion names, so it takes longer with many worlds,
and switching stays well under a quarter of a second. Automatic backups run in the background and skip a world
nobody has opened since its last backup (a second run took 6 to 16 ms). A backup is about a seventh of its
world's database.

Coming back to a world after a month away (its 25 companions' lives caught up for the one in focus) took 11 s
before the fixes in this round and takes about 3 s now: a new day used to read the city's weather afresh for
every person and day, and work out every companion's perception lines from scratch many times over.

**A new day with many companions** now also lives a turn of three companions out of focus ("Everyone keeps
living", added after the measurements above). On the same cloud machine, a new day with 25 companions took about
1.5 s for the one in focus and 1.5 to 3 s for the turn of the others, in the background.
