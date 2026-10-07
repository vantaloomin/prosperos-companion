# Story mode

The **Story** tab is the user's own free-form story: they play themself in one of the cities, and a
narrator describes the place and voices the people there. It is apart from every companion. The
story has its own tables (`story_scene`, `story_messages`), and no companion prompt reads them, so
nothing said in the story reaches the companion's chat, memories or life.

## Who decides what

The app decides the scene, the same way the life sim decides the companion's day
(`companion/story.py`):

- **Where:** the city and place the user picked under "Go somewhere else…". A new story starts in
  the companion's city (Baltimore without one) at its first cafe. Moving adds a line to the story
  ("You arrive at …") that the narrator sees as a note.
- **When:** the app clock (debug time included) in the city's own timezone.
- **Weather:** the city's typical weather for the date (`generators.conditions`).
- **Who is there:** the townsfolk rules at that moment (`encounters.present`): people seeded at the
  place and residents whose routines bring them there. These are the same people the companion's
  world has. When the story is in the companion's city, it uses the companion's own town seed and
  family names, so a name means the same person in both. Companions are never in the story, including
  ones who stepped back.

The narrator model only voices the scene. Its prompt is "The Story narrator" in Settings > Advanced
(`NARRATOR`, [prompts.md](prompts.md)), followed by a `## Scene` section with the facts above. The
narrator gets the names of the people present, with a rule not to use a name until that person
gives it. The screen lists them only as the user would see them ("the barista", "a
regular").

The narrator stays in the story as companions do. Sentences saying it is an AI are dropped
(`in_character.Guard`), and OOC: or ((…)) gets a plain answer. Its model is the **Story narrator**
job in Settings > Models, which is the conversation profile unless another is chosen.

## API

| Request | Does |
| --- | --- |
| `GET /api/story` | `{scene, messages, ready}`. `scene` has the city, place, `local_time` (city clock, no offset), `weather`, the city's `places` and `around` (who is there, unnamed). `ready` is false without a model. |
| `PUT /api/story/scene` `{city_id, place_id?}` | Moves there; a city alone means its opening place. 404 for an unknown city or place. |
| `POST /api/story/messages` `{text, client_id}` | Saves the user's line once per `client_id` and returns `{message, reply}`. A failed reply is saved with `status: failed` and its `error`. Sending the same `client_id` again returns the saved reply, or tries again if it failed. 409 `no_connection` without a model; the line stays saved. |
| `POST /api/story/retry` | Tells the reply to the latest user line again, replacing the one there. |
| `DELETE /api/story` | Starts a new story: the history goes, the scene stays. |

Start over and Delete character keep the story (it is in `start_over.WORKSPACE`).

## Planned

- Meeting people: the story records who the user has met and what they have learned, in a list of
  the user's own that is not the companion's. Anyone met can become the main character through the
  existing switch.
- A dating app for modern and future cities, and a lonely hearts column for older eras. Townsfolk
  would get seeded looks, orientation and what they are looking for. A match becomes a date in the story.
