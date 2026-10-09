# Voice notes

Now and then a companion sends a short voice note instead of a text, in a voice the app picks to suit them. The
chat shows it as a bubble with a play button, its length, and the words underneath. The words are the message
itself, so memory, search and the next reply read it like any other text.

## When a note is sent

Rules decide, in `companion/voice/notes.py`. Only a first text can be a voice note (a message the companion sends
without being asked, `companion/life/openers.py`), so everything that holds a first text back holds a note back
too: quiet hours, the companion's sleep, the daily cap on first texts and the shared allowance while you are away.
Then:

- Voice notes are on (the default) and the chosen engine can speak: the built-in voice is downloaded, or the
  hosted engine has a key. Until then every first text stays a text.
- Seeded dice on the trigger send about one first text in three as a note (`CHANCE`).
- At most 3 notes per companion in 24 hours (Settings can change this, 1 to 20).
- The message is short (320 characters at most) and has no link, which should stay something you can tap.

When a note is planned, the model is told the message is a voice note (the **Voice notes** prompt in Settings >
Advanced), so it writes spoken words. Emoji, `*actions*` and links are left out of what is read aloud whatever it
writes. If recording fails, the message goes as a plain text; a voice note is never the reason a message is lost.

## Which voice

`companion/voice/voices.py` picks from the engine's stock voices, so there is nothing to set up:

- Their pronouns (she or he in their description) give a woman's or a man's voice. Without either, a woman's.
- Their home city's country gives the accent: the UK, Ireland, Australia and New Zealand get a British voice,
  everywhere else an American one. Without a city country, the time zone decides. Fantasy and historical cities
  follow the same rule from whatever country they name.
- Their id seeds the choice among the best few voices that fit, so two companions rarely share one and a voice
  never changes by itself.

Settings > Models > Voice notes lists every companion with their voice, a list to choose another and a Preview
button. A choice is kept per engine. Real people's voices are never cloned.

## Engines

| Engine | Where it runs | Key | Audio |
| --- | --- | --- | --- |
| Built-in voice (default) | This PC's processor | None | WAV, 24 kHz |
| OpenAI (`gpt-4o-mini-tts`) | OpenAI | Saved here, else an OpenAI text model's key, else `OPENAI_API_KEY` | MP3 |
| ElevenLabs (`eleven_multilingual_v2`, stock voices) | ElevenLabs | Saved here, else `ELEVENLABS_API_KEY` | MP3 |
| Google Cloud Text-to-Speech (Chirp 3 HD first) | Google | Saved here, else `GOOGLE_TTS_API_KEY` | MP3 |

Only each note's words and the voice go to a hosted engine. Keys are kept in the OS credential vault
(`voice-openai`, `voice-elevenlabs`, `voice-google`) and never sent back to the browser.

### The built-in voice

`companion/voice/kokoro.py` runs [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) (Apache 2.0) with
sherpa-onnx's ready-made `sherpa-onnx-offline-tts` program (Apache 2.0), so the Companion needs no new Python
packages. Both come from sherpa-onnx's GitHub releases, pinned (sherpa-onnx 1.13.8, `kokoro-multi-lang-v1_0`) and
checked against their SHA-256: about 378 MB in all, into the workspace's `voice/` folder, which backups leave out.
Because voice notes are on by default, the download starts by itself when the app starts with background activity
on and the built-in voice is the engine; Settings also has a Download button.

The program runs once per note in its own process, on the processor with at most four threads, one note at a time.
A note takes a few seconds. British voices read with British pronunciation. `COMPANION_SHERPA_TTS` and
`COMPANION_KOKORO_MODEL` point at a program and model folder of your own, for a computer without a pinned build.

## Storage

- `voice_settings`: on or off, the engine and the daily limit. Kept by a restore, like other settings.
- `companion_voices`: a voice the user picked for a companion on one engine. Goes with the character.
- `voice_notes`: the message a note belongs to, its file in the workspace's `voice-notes/` folder, its length,
  engine and voice. Goes with the history; backups carry the files. A branched timeline's copy shares the file.

## API

| Method | Path | What it does |
| --- | --- | --- |
| GET, PUT | `/api/voice` | Settings: `voice_notes`, `engine`, `daily_limit`; where each key comes from; the built-in voice's state |
| PUT | `/api/voice/key` | Save (`api_key`) or remove (empty) a hosted engine's key |
| POST | `/api/voice/builtin/download` | Download the built-in voice |
| GET | `/api/voice/companions?engine=` | Each companion's voice and the voices to choose from |
| PUT | `/api/voice/companions/{id}` | Choose a voice (`voice`), or go back to the app's pick (empty) |
| POST | `/api/voice/preview` | A short sample, not kept |
| GET | `/api/voice/notes/{message_id}` | A note's audio |
