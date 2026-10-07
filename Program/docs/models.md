# Models

[Back to the README](../../README.md)

Settings > Models picks the text models the Companion uses. It is the model selection from
Prospero's Study (`server/providers/`, `server/profiles.py`, `src/features/models/` at `bbcbde4`),
copied into this repository and adapted; see [Development](development.md#code-reused-from-prosperos-study).

## Profiles

A profile is one provider, one model and its settings, plus an API key kept in the OS credential
vault under the service name `Prospero Companion` (never the Study's). Saving a profile never
contacts the service.

| Provider | Address | Key | Request |
| --- | --- | --- | --- |
| OpenAI | official | `OPENAI_API_KEY` or saved | Responses API |
| Anthropic | official | `ANTHROPIC_API_KEY` or saved | Messages API |
| OpenRouter | official | `OPENROUTER_API_KEY` or saved | Chat Completions, provider fallbacks off |
| Google / Gemini | official | `GEMINI_API_KEY` or saved | `streamGenerateContent` |
| OpenAI-compatible API | any HTTPS, or HTTP on loopback | optional; `COMPANION_API_KEY` | Chat Completions |
| Local / LM Studio | loopback only | optional; `COMPANION_API_KEY` | Chat Completions |
| Kobold | loopback only | none | native `/generate` |
| Codex / ChatGPT | none | the Codex CLI's own login | `codex exec` in an empty read-only folder |

**Test connection** lists the service's models (`GET /models`) without generating text, and fills
the context size and longest reply from what the service reports; unreported limits stay manual,
and nothing is guessed. Generation settings offer only the controls each adapter supports:
sampling, reasoning effort, thinking mode and budget, chat-template thinking and the output-limit
parameter, as in the Study. A saved key stays with its provider and address: changing either drops
it from the vault rather than sending it somewhere new.

Not copied from the Study: the LM Studio native protocol and its verified background interruption
(local servers use the OpenAI-compatible API, and background work here yields between streamed
chunks through the scheduler), versioned profiles and exact retries, and usage and cost summaries.

## Jobs

| Job | What uses it |
| --- | --- |
| Conversation | Chat replies. Every other job uses this profile unless given its own, like the Study's Primary Writer. |
| Life phrasing | Wording the companion's day in the background (`phrase_with_model`). |
| Memory suggestions | Model memory suggestions in the background. |
| Character drafting | Quick start and Help me write. |
| Seeing pictures | Describes each picture you send in chat, once, before the reply (OpenAI, Anthropic, Google, OpenRouter, local or compatible profiles with a vision model; Kobold and Codex cannot look at pictures here). |
| Semantic recall | Embeddings, from the profile's `embedding_model` (OpenAI, local or compatible profiles only), or from built-in recall when it is on ([architecture](architecture.md#built-in-recall)). |

There is no automatic fallback to another profile when a request fails; like the Study, a failed
request reports its error, and OpenRouter requests forbid OpenRouter's own provider fallbacks. The one
exception is a rate limit (HTTP 429) before any text arrives: hosted models answer it for a few
seconds at busy times, so the same request is sent once more after its `Retry-After` wait (1 to 5 seconds).
Image prompts are assembled without a model, and image backends (and their NSFW routing) have
their own settings under Images.

## Upgrading from a single connection

Earlier versions had one OpenAI-compatible connection. The first start after upgrading turns it
into a profile named "Text model" doing the conversation, so every other job keeps using it: a
loopback address becomes a Local profile and any other a compatible one, so requests are unchanged.
Its saved key and embedding model carry over. `GET /api/connection` still describes the
conversation profile, and `PUT /api/connection` remains a one-call setup for a compatible or
local server.

## API

| Request | Purpose |
| --- | --- |
| `GET /api/models` | Profiles, job assignments and the job list |
| `POST /api/models/profiles`, `PUT`/`DELETE /api/models/profiles/{id}` | Add, edit (with `expected_revision`), delete |
| `POST /api/models/discover` | Test an unsaved form; reuses a profile's saved key when given its `profile_id` |
| `POST /api/models/profiles/{id}/check` | Test a saved profile |
| `PUT /api/models/routes` | `{job, profile_id}`; `null` returns the job to the conversation profile |
