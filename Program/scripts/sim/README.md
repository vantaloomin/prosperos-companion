# Simulated end-to-end runs

Builds worlds through the app's own API the way a user would, lets time pass with debug time, then checks what
the screens' endpoints say and walks every screen in a browser. It looks for the kinds of bugs testers found in
1.1.5 to 1.1.8:

- **World fit**: a ship, a fantasy city or a city someone wrote showing today's Earth (dollars, tacos, TV, rain
  boots aboard, horses in a cabin, "Retired" 22-year-olds where the city has no jobs).
- **What the user set by hand**: a pastime, an age, a job, a pet, a mom added by hand: still there after time
  passes and a new version of the character, not read as new, not doubled by what the app made.
- **App-made beside user-made**: two moms, a person shared into a second circle.
- **Several companions**: everyone reacting to the user's own post and to each other's.
- **Errors**: API calls that fail, errors in the app's log, page and console errors.
- **On screen** (browse.mjs): text cut off, placeholders wider than their box, sideways scroll, text boxes the
  browser would autofill, "the user", and the world-fit words, at desktop (1440), narrow desktop (1024) and phone
  (390) sizes, for every companion.

The model and ComfyUI are the acceptance stand-ins (scripts/acceptance/standins.py), so replies are canned: this
checks how features meet, not what a model writes.

## Run it

From `Program/`, with the interface built (`npm run build`):

    uv run python scripts/sim/run.py --out <folder> --days 4 --keep
    node scripts/sim/browse.mjs <folder>            # while the apps are still up (--keep)

`--worlds town ship` runs only some (worlds.py has `town`, `ship`, `camelot`, `grandport` and `own-city`, a
medieval city written from the template with no careers, currency or media of its own). `--check-only` checks a
run already saved. Results: `<folder>/report.md` and `findings.json` (API side), `browse.json` and `screens/`
(screen walk). Each world gets its own app and data folder under `<folder>/apps/`; the apps' logs are there too.

Time passes with Settings > Debug's debug time, which walks the skipped hours as if the app had stayed open; four
days takes several minutes a world, longer for the bigger fantasy cities.

## Adding a check

drive.py saves each world's endpoints three times (`fresh`, `after-edits`, `later`); checks.py reads them. A new
bug class is usually a new function in checks.py over `later`, plus anything the user would do by hand added to
`Driver.edits`.
