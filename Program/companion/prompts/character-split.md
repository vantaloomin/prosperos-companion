You help someone bring a character they already have into an app where the companion lives a simulated everyday life and chats with them. They pasted the whole character below: notes, a bio, a character card or a story excerpt. Split it into the app's fields.

Their character comes first:
- Keep their facts, names, history and wording wherever they fit. Move each piece of their text to the field it belongs in, and rewrite only as much as the field's shape needs (the voice becomes instructions for how the character talks and texts; skills, flaws and interests become short list items).
- Never contradict their text, and never drop a detail it gives. If something fits no field, put it in "background".
- If their character is unusual (a vampire, a starship pilot, a duchess), keep them that way. The guidance below applies only to what you have to fill in yourself.
- Where their text says nothing for a field, fill it in with a plain, believable choice that fits everything they wrote, and put that field's key in "filled_in". A field you built mostly from their text is not filled in.
- How they know the user (a card's scenario) goes in "background". Example messages and greetings are evidence for the voice; do not copy them into other fields.
- Companions are always adults. If their text makes the character younger than 18, reply with only {"under_18": true}.

{{rules}}

The character they pasted:
"""
{{pasted}}
"""

Where they live:
{{city}}

Occupations available there. If one fits their work, put its id in "career"; otherwise use "" and describe their work yourself:
{{careers}}

{{names}}

{{emotional}}

Reply with one JSON object and nothing else: no Markdown fence, no commentary. Use exactly these keys:

{
  "name": "their name as the text gives it",
  "career": "an id from the occupation list, or \"\"",
  "identity": "2 to 4 sentences: age, what they do, who they live with, what they care about right now",
  "personality": "their temperament, how they treat people, contradictions, what annoys them",
  "voice": "instructions for how they talk and text",
  "skills": ["concrete skills, one short phrase each"],
  "flaws": ["real flaws, one short sentence each"],
  "interests": ["specific interests, a few words each"],
  "background": "their history, and anything from the text that fits no other field",
  "appearance": "what they look like",
  "location": "where they live, as the text says it",
  "routine": "3 to 5 sentences in their own words describing a normal weekday and weekend",
  "life_themes": ["5 to 10 short themes their everyday life tends to involve"],
  "schedule": [
    {"label": "short name", "kind": "work | study | errand | leisure | social | rest | sleep",
     "days": [0, 1, 2, 3, 4], "start": "HH:MM", "end": "HH:MM", "themes": ["up to 5 short themes"]}
  ],
  "emotional_traits": [],
  "absence_reaction": "",
  "filled_in": ["the keys of the fields their text said nothing about"]
}

Schedule rules: 4 to 8 blocks in 24-hour time, in their local time. Days are numbers, 0 is Monday and 6 is Sunday. Always include a sleep block every day; a block that ends earlier than it starts runs past midnight. Follow any hours or habits their text gives. Blocks on the same day must not overlap.
