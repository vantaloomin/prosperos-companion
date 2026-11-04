# Keeping model numbers in bounds (Feature Hit List #98)

The audit for 1.4 "Another Storm Brewing": every place a model's answer, a service's reply or old saved words hands
the world a number or a choice, and what stops a bad one. Tests: `tests/test_bounds_audit.py`.

A place passes when a missing, wrong-typed, out-of-range or non-finite value (JSON allows `NaN` and `Infinity`, and
Python's `json.loads` reads them) is dropped, clamped or replaced by the rule's own default, and never stops a reply,
a background pass or a page.

## Fixed in this pass

| Where | What a bad value did | Now |
| --- | --- | --- |
| `memory/dates.py` `month_day` | "February 29" said in a leap year rolled to a year without one and raised `ValueError`, failing whatever was reading it through `dates.resolve` (memory dates, the companion's own plans). | February 29 in a year without one is the 28th, marked not certain; a day no month has ("April 31") is still no date. |
| `mcp/weather.py` `readings` | A weather service's structured `high_f: 9999` became the day's high; `Infinity` or `NaN` raised `OverflowError`/`ValueError`. Only text readings were range-checked. | Structured and text readings both keep only finite values from -60 to 135 °F; garbage structured fields fall back to the text. |
| `life/ages.py` `born_from` | An age older than the calendar ("she is 3000 years old", which `world/looks.py` allows for long-lived kinds and a draft can write) gave a birth year before 1 and raised `ValueError` in the ages sync and Back when. | The birth year floors at year 1; `age_from` already keeps the age they were written at, so they stay 3000. |
| `life/pets.py` `from_home_item` | An old pet description "about 99999 years old" dated its birth before year 1 (`OverflowError`). | That legacy age is capped at 60 years. |
| `memory/suggest.py`, `memory/self_suggest.py` | `"message": true` passed `isinstance(index, int)` and was read as message 1. | The message number must be a real integer. |
| `memory/suggest.py` `supported` | The prompt's own correction example ("I don't garden anymore" gives "no longer gardens") failed the app's own word-support check, so a model that copied it exactly had its correction dropped. | A negated answer to a negated message is also compared on word stems without the negation words. No prompt change. |

## Already in bounds (checked, no change)

| Where | Number or choice | Guard |
| --- | --- | --- |
| `memory/suggest.py`, `memory/self_suggest.py` | Message index, layer/category, subject and value lengths | Index 1..batch, closed sets, cuts at 200/1000 (40/50) characters, words must come from the message. |
| `memory/look_back.py` | `[[recall: ...]]` request | One per reply, query at most 200 characters, rate limit per model. |
| `drafting.py` `block`, `models.RoutineBlock` | Drafted schedule days and times | Days 0..6 and distinct, `HH:MM` validated, start differs from end, at most 24 blocks; a draft without sleep every day falls back to the career's schedule. |
| `drafting.py` traits, lists | Emotional trait intensity, list lengths | Pydantic enum; lists de-duplicated and cut. |
| `drafting.py` `adults_only`, `world/intimacy.py` | Drafted and stated ages | Under 18 refused; ages are read by rules from the text, never a model number field. |
| `world/draft/polish.py` | Names and summaries | Only ids it was sent; names 120, summaries 300 characters; prices, months and links stay the rules'. |
| `sidecar.py` | Proposed changes | Kinds from a closed set, references must be ones it was shown, every value goes through the field's own check. |
| `life/synthesis.py` | Phrased summary and post | Both required, length caps, no clock times, the place name kept. |
| `life/planned_week.py` | Week lines | At most `LINES`, each line's weekdays, clock times and words must come from what it was given. |
| `life/own_plans.py` | Times and "the 24th" the companion says | Hour 0..23, minute 0..59, day must exist in one of the next three months. |
| `moods.py`, `life/narrator.py` | Mood intensity | Rules only, capped 1..3 on save and on read. |
| `providers/discovery.py`, `providers/config.py` | Reported context and output token limits | Only positive integers; the profile itself is 1024..2,000,000 context and 64..128,000 output. |
| `world/schema.py`, `world/routes.py` | Roadworks delay | 1..60 minutes. |
| `world/mix.py` | Townsfolk mix shares | Clamped to each share's low and high. |

## Found, not fixed here

- `drafting.draft_tokens` takes a provider's reported output limit as a ceiling with no floor, so a server that
  reports 16 output tokens makes every draft fail as too long. Rare and the error says why; left as is.
- Editable prompts (Settings > Advanced) let the user change these examples. The tests guard the defaults that
  ship; a saved edit is checked for placeholders and list lines, not for its JSON example.
