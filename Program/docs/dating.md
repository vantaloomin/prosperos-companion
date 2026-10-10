# Matchlight, the dating app

**Matchlight** is a made-up dating app in the sidebar, and the main way to find new companions. It starts
with a download badge on its icon. Opening it shows its "store page"; after a short install the user sets up
their profile over four screens (first name and age, who they are and who they want to see, what they are
looking for and the ages, an optional bio). Then they swipe through the townsfolk of a city they pick.

Everyone on the app is a townsperson (`companion/world/townsfolk.py`), and everything about them is decided by
rules, never by a model. A match can become a companion through the same path as switching the main
character to a townsperson (`companion/cast.py`), and is then chatted with like any companion.

## Townsfolk dating details

`companion/world/dating.py` draws each person's details from their sheet's seed, so they are the same every
time and nothing is stored:

- **Looks:** height (from a bell curve by gender, a little shorter in older eras), build, hair (colouring
  by the heritage their name comes from, greying with age, balding for some men, the odd dye job in modern
  cities), eyes, a beard for some men, a style of dress for the era, and one distinguishing detail.
- **Orientation**, at rough real-world rates by age: most people are straight; under 30 about 4% are gay or
  lesbian and 6% (men) to 15% (women) bisexual, falling to about 3% in all over 60. Nonbinary townsfolk are
  queer and drawn to everyone or to women or men and nonbinary people.
- **Single or not:** the chance of a partner rises with age (30% at 18-24 to 65% in midlife), and a person
  whose desire is "someone to come home to" is mostly single. Older single people are sometimes widowed.
- **What they are looking for:** only single and widowed people are on the app. Some are not looking at
  all (more of the older ones and those who want a quiet life; fewer gay, lesbian and bisexual people, who
  use dating apps about twice as often, Pew 2023). The rest want a relationship, something
  casual or new friends, swayed by their desire and age; in older eras casual is rare.
- **Who they would date:** never anyone under 18, and within an age range around their own.
- **Pickiness:** a seeded number that lowers their chance of saying yes.
- **Bio:** three short first-person lines from what their sheet already says (their current goal, their
  quirk, their usual spot). No family name.

## The deck and matches

`companion/dating.py` keeps what the user did: their profile (`dating_profile`), their swipes
(`dating_swipes`) and Story mode dates (`dating_dates`). These are workspace tables, kept through Start over.

- The deck is everyone on the app in the city the user is looking in: people at its places, its residents,
  and 500 more neighbors per neighborhood who only turn up on the app (`townsfolk.APP_MEMBERS`, keyed after
  the residents, since a city has far more singles than the few dozen neighbors anyone runs into). That is
  about 3,000 people in Baltimore, worked out once per city and town (a few seconds the first time). Never a
  companion. They are filtered to adults who are single, looking, in the user's age range and of
  a gender they want, and who would date someone of the user's gender and age. Someone looking for friends
  sees only others looking for friends, of the genders they chose, whatever their orientation. The order is
  fixed for the user's profile.
- A like is a match only if the person's rules say yes: a chance from their pickiness, temperament, the age
  gap and whether they want the same thing, rolled once for this person and this user's profile. A like
  that is not returned simply never comes back, as on a real app.
- A match can be **started talking to**: the Make-the-main-character form opens with their profile drafted
  from their sheet (`#match/<key>`). It starts as a romance, or a friendship if they matched for friends,
  and says they matched through the app. It works with no companion yet (they become the first) or with
  one (who steps back as in a cast switch). The new companion lives in the town they were found in.
- A companion never sees the app, who the user swiped on or who they matched with.
- **Delete your profile** removes the profile, likes and matches; companions made from matches stay.

## Show photo

Nobody has a picture until the user asks. With an image backend set up, a card has **Show photo**, which makes
one portrait of that person (`companion/dating_photos.py`) and keeps it (`dating_photos`), so they look the same
afterwards and asking again makes nothing new. Pictures are never made in bulk.

- The prompt is a fixed fill-in template from their seeded looks (age, build, hair, eyes, beard, detail, style
  of dress, a setting from their usual spot), framed as a smartphone dating photo, a cabinet-card photograph
  (personal column) or a painted miniature (matchmaker). No model rewrites it.
- It is classified and routed like every other image (`images/content.py`, `images/routing.py`), so anything
  classified NSFW could only go to a local backend and prohibited requests go nowhere.
- It goes through the image runner's adapters, counts against each backend's limit, and waits while a chat
  reply is written. A photo cut off when the app closed can be asked for again.

## Older eras

The same deck has a period form: a **personal column** in the paper for Victorian, steampunk, frontier and Jazz Age
cities (a notice with initials and a box number, "Write to them", "Turn the page"), and **the matchmaker**
for medieval and fantasy cities ("Ask for an introduction").

## Dates in Story mode

With Story mode on (Settings > Advanced, `story_mode`), a match can be met in the story: the user picks a place in their city (their usual spot
first), the story moves there and the narrator is told the date is there, what they look like and what they
are looking for. Story mode's only hook is `dating.with_date`, which `story.present` calls to add the date
to whoever the townsfolk rules put there; the date's line in the scene comes from its `note`, and the screen
shows them as "your date, Maya". Going somewhere else, starting a new story or **End the date** ends it. A date also adds them to the user's people-met list (`story_people.meet`).

## API

| Request | Does |
| --- | --- |
| `GET /api/dating/status` | `{installed, name}`: whether the profile is set up, for the sidebar badge. |
| `GET /api/dating` | `{surface, words, city, profile, story, deck, remaining, matches, date}`. |
| `PUT /api/dating/profile` | Saves the profile; 422 under 18. |
| `DELETE /api/dating/profile` | Deletes the profile and every swipe. |
| `PUT /api/dating/city` `{city_id}` | Looks in another city. |
| `POST /api/dating/swipes` `{key, like}` | Pass or like; returns the state with `matched` set to the person on a match. 409 for someone not in the deck or already answered. |
| `DELETE /api/dating/swipes/passed` | Shows people the user passed on again. |
| `DELETE /api/dating/matches/{key}` | Unmatches. |
| `POST /api/dating/dates` `{key, place_id}` | Meets a match in Story mode (409 with it off); returns the story. |
| `DELETE /api/dating/dates/current` | Ends the date. |
| `POST /api/dating/photos` `{key}` | Their photo: the saved one, or one queued now (409 with the refusal when no backend may make it). |
| `GET /api/dating/photos/{key}` | `{status, error, url}`; `status` is `none`, `queued`, `running`, `completed` or `failed`. |
| `GET /api/dating/photos/{key}/file` | The picture. |
| `GET /api/companion/cast/draft?key=` and `POST /api/companion/cast/switch` | Also accept a match who is not a companion yet. |
