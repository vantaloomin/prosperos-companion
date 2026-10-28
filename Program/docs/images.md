# Image generation

[Back to the README](../../README.md)

Feed posts can carry an illustration made by one of three kinds of backend (PRD F3 to F9). Every
backend is off until the user sets it up, and text never waits for an image. The code is in
`companion/images/`.

## Backends (F5, F7 to F9)

| Kind | Adapter | Receives | Runs |
| --- | --- | --- | --- |
| `comfyui` | `adapters/comfyui.py`: ComfyUI HTTP API (`/prompt`, `/history`, `/view`) | Safe; NSFW too when local | One job at a time |
| `codex` | `adapters/codex.py`: the Codex CLI's built-in image generation (`codex exec`) | Safe only | One job at a time across every Codex backend |
| `hosted` | `adapters/hosted.py`: OpenAI-style `/images/generations` or OpenRouter-style `/chat/completions` with image output | Safe only; NSFW too when the user switches it on (OpenRouter, NanoGPT and other APIs only) | Its configured limit (1 to 4) |

- **ComfyUI** is local when its address is a loopback address, or when the user marks it as a
  machine they control. A remote address otherwise counts as hosted (F6). The app only connects to
  the server the user entered; it never starts, stops or restarts one. Cancelling removes the
  app's own prompt from the queue, or interrupts it only when it is the prompt running.
- **Model family.** Each ComfyUI backend has a **Model family** (Vanta, 2026-10-13: not Krea 2
  every time), stored as `family` in its config and Krea 2 when unset. It picks the built-in
  workflow, which files the pickers list first, the sampling the workflow starts on, and whether there
  it uses for pictures made from a reference. Changing it clears file and sampling choices made for the old
  family; style LoRAs and the user's own workflows stay. The built-in workflows are made from Vanta's own
  TXT2IMG and reference workflows (2026-10-13), on public default files; they are untested on a real
  server except Krea 2's text workflow:

  | Family | Built-in workflow | Files (defaults) | Sampling | Reference workflow |
  | --- | --- | --- | --- | --- |
  | Krea 2 (`krea2`) | `krea2-turbo.json`, empty negative | as below | 8 steps, CFG 1, euler_ancestral, simple | `krea2-turbo-reference.json`: Identity Edit LoRA + comfyui-krea2edit nodes (below) |
  | Qwen Image 2.1 (`qwen21`) | `qwen-image-2.1.json`, empty negative | `qwen_image_2.1_int8_convrot`, `qwen3vl_8b_int8_convrot` (type `qwen_image`), `qwen_image_2.1_vae_bf16` | 25 steps, CFG 1, euler, simple | `qwen-image-2.1-reference.json`: the picture goes to core `TextEncodeQwenImage21` as `<image1>` |
  | Z-Image Turbo (`zimage`) | `z-image-turbo.json`, empty negative | `z_image_turbo_bf16`, `qwen_3_4b` (type `lumina2`), `ae` (Flux VAE); `ModelSamplingAuraFlow` shift 3 | 9 steps, CFG 1, res_multistep, simple | `z-image-turbo-reference.json`: image-to-image at denoise 0.7, core nodes; keeps the picture's pose and colours |
  | Anima (`anima`) | `anima.json`, `masterpiece, best quality, score_7, newest` ahead of the prompt (no rating tag) | `anima-base-v1.0`, `qwen_3_06b_base` (type `stable_diffusion`), `qwen_image_vae` | 30 steps, CFG 4, er_sde, simple | `anima-reference.json`: the Anima Edit LoRA (`AnimeEditV2.safetensors`, on Civitai; no link in the app) and `ApplyCosmosReferenceLatent` from ComfyUI-Cosmos-Reference |
  | Booru (`booru`: SDXL, Pony, Illustrious) | `booru-sdxl.json`, `masterpiece, best quality, amazing quality, very aesthetic, absurdres, newest` ahead of the prompt | one checkpoint (`ckpt_name`, `Illustrious-XL-v2.0`), clip skip 2 | 30 steps, CFG 6, euler_ancestral, normal | `booru-sdxl-reference.json`: IP-Adapter Plus (ComfyUI_IPAdapter_plus; weight 0.7 ending at 0.5) |

  The adopted character LoRA is trained on Krea 2, so only Krea 2 applies it. Anima and Booru
  backends start their prompts as an "Anime illustration" unless the backend has a style of its own
  (`backends.own_style`). A reference workflow that needs a custom node pack is still offered; the check
  names the missing nodes and their page. Only the Krea 2 pack installs with one press. Krea 2 can use a
  separate model for pictures from a reference (`ref_unet_name`, "Same as the Model" by default). With a
  Krea 2 Edit merge (a name with "Edit", such as the KREA 2 Edit SNOFS Merge, recognised by name only), the
  Identity Edit LoRA is left out, since the merge has it built in, and `ref_boost` goes to 2.5.
- **The built-in Krea 2 workflow** (`workflows/krea2-turbo.json`) targets Krea 2 Turbo with the files
  ComfyUI's own Krea 2 template uses: `UNETLoader` with `krea2_turbo_fp8_scaled.safetensors`,
  `CLIPLoader` of type `krea2` with `qwen3vl_4b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`,
  8 steps at CFG 1 (euler and simple then; euler_ancestral and an empty negative since Vanta's workflow). Verified on Windows with an RTX 5090 and ComfyUI 0.39.0,
  unchanged, with a Krea 2 fine-tune in NVFP4 (Muse Krea2 V3.5) and a Qwen3-VL 4B NVFP4 text encoder
  chosen for its loaders: about 3 seconds an image once loaded, after a first load of about 216
  seconds. Text drawn inside a picture usually comes out garbled. The default files themselves
  have not been run.
- **Model files.** Under the backend, **Model files for the built-in workflow** asks the server
  (`/object_info/UNETLoader`, `/object_info/CLIPLoader`, `/object_info/VAELoader`, at the address
  entered only) which files it has and offers them in dropdowns: Model, Text encoder, Text encoder
  type and VAE, with the current choice selected and a **Refresh list** button. The choices are
  stored in the backend's config (`unet_name`, `clip_name`, `clip_type`, `vae_name`); an empty one
  means the default file. Names are kept exactly as the server lists them, subfolder and all (a
  Windows server lists `Krea 2\model.safetensors`). When the server cannot be reached the names can
  be typed. A custom workflow is used as given and ignores these choices. Krea 2's files are listed
  first and **Only Krea 2 files** (on by default; named for the backend's family) narrows each list to them: a model or LoRA whose
  path matches `krea`, `kr2` or `kera` (so a `Krea 2\` folder counts), the Qwen3-VL 4B encoder and
  a Qwen VAE (`adapters/comfyui.KREA_FILES`). ComfyUI cannot say a file's model family, so this only
  sorts; the current choice always stays in the list, and the toggle shows everything.
- **Sampling.** **Sampling** sets the built-in workflow's KSampler for a model that wants other
  settings: Steps, CFG, Sampler and Scheduler, the last two from the server's own lists
  (`/object_info/KSampler`). It starts on Krea 2 Turbo's (8 steps, CFG 1, euler, simple: the
  workflow's own); a value equal to those is stored as unset, so **Use the defaults** clears them.
  Saved per backend as `steps`, `cfg`, `sampler_name`, `scheduler`. A job's workflow name records
  changed settings (`krea2-turbo (10 steps, CFG 1, euler/beta)`). A custom workflow keeps its own.
- **Style LoRAs.** **Style LoRAs** offers up to three files from the server's loras folder
  (`/object_info/LoraLoaderModelOnly`), each with a strength (0.7 by default) and trigger words,
  stored as `style_loras` in the backend's config and used by any workflow. Each becomes a
  `LoraLoaderModelOnly` chained after the character's adopted LoRA, so the likeness applies first;
  the trigger words follow the character's at the start of the prompt. The character's own file is
  never offered here or applied twice. Check reports a style LoRA missing from the loras folder. A
  style LoRA never makes a server less strict: one whose name or trigger words do not classify as
  safe is refused on any server that does not accept NSFW requests (`backends.require_safe_loras`).
  LoRA names go only to the ComfyUI server they belong to.
- **Where to get models.** Beside the dropdowns is a short list of download pages from
  `companion/images/model_links.json`. Each entry links to the official model page, never straight
  to a file, with its licence: the Krea 2 Turbo files repackaged for ComfyUI by Comfy-Org (Krea 2
  Community License, not gated), Krea's own Krea 2 Turbo page (gated: accept the licence on Hugging
  Face first), and Comfy-Org's Qwen3-VL text encoder and Qwen Image VAE pages (Apache 2.0; the same
  files as in the Krea 2 repackage). Community fine-tunes are not listed; any file on the server can
  still be chosen.
- **Check** asks the server for its node list and reports every missing node or model file, using
  the chosen file names; nothing is installed or downloaded. A custom workflow in ComfyUI's API
  format replaces the built-in one, with `{{prompt}}`, `{{negative}}`, `{{seed}}`, `{{width}}` and
  `{{height}}` where the request's values belong. On the PC, **Workflow** and **Workflow for pictures
  made from a reference** under the backend show the workflows, indented, to read or edit. Each box
  starts filled in with the built-in one (with the chosen model files and sampler settings in
  place); saving an edited or pasted one makes it the backend's own, and **Use the built-in one**
  goes back (saving the built-in text unchanged stores nothing). A paired phone never sees or
  changes them.
- **The built-in reference workflow** (`workflows/krea2-turbo-reference.json`) follows the Krea 2
  Identity Edit setup Vanta runs: the built-in workflow's model with the
  `krea2_identity_edit_v1_2.safetensors` LoRA, the `{{reference_image}}` scaled to 1 megapixel and
  read by `Krea2EditModelPatch` (appearance, `ref_boost` 1) and `Krea2EditGroundedEncode` (the
  prompt read with the picture), a zeroed negative, then the usual sampler. Those two nodes come
  from the [comfyui-krea2edit](https://github.com/lbouaraba/comfyui-krea2edit) pack (Apache-2.0, no
  Python dependencies); ComfyUI has no core equivalent. The LoRA's page is in the model links. It
  takes the same file and sampler choices. Check lists what it is missing with where to get it,
  but that does not fail the backend: only profile pictures need it.
- **Installing the nodes** (Vanta's one exception to "the app never writes into ComfyUI",
  2026-10-13). When Check finds a node a listed pack provides (`images/node_packs.py`) on a ComfyUI
  at a loopback address, it offers **Install the Krea 2 Identity Edit nodes**. The press asks
  ComfyUI for its custom_nodes folder (`/internal/folder_paths`; only a folder named custom_nodes with
  main.py, comfy/ or models/ beside it is used, anything else is refused), downloads the pack's files from
  the pinned commit, checks each against its SHA-256, and moves them in as a new
  `comfyui-krea2edit` folder. An existing folder is never replaced, no Python package is installed
  (the pack needs none), and nothing else is touched. ComfyUI loads it on its next start. Never from
  a paired phone.
- **Codex** uses Codex's own `image_generation` feature (stable and on by default in codex-cli
  0.160.1). Each image is one turn of `codex exec --json --skip-git-repo-check --ephemeral
  --ignore-user-config --ignore-rules --sandbox read-only --cd <empty scratch folder> -`, with a
  prompt on stdin asking for exactly one image of a verified size. Codex saves the PNG under
  `CODEX_HOME/generated_images/<thread id>/`; the app takes the path from the turn's `saved_path`
  event, or the newest PNG in that thread's folder, and copies it to `images/raw/`. A turn can take
  a few minutes (600-second limit) and counts against the plan's Codex usage limits. The CLI is
  found from `cli_path` or `codex` on `PATH`; a location saved for the retired `chatgpt-imagegen`
  method is ignored. The app only checks that `auth.json` exists in `CODEX_HOME` (or `~/.codex`),
  and **Check** runs `codex login status`; it never reads the token. A Codex signed in with an API
  key works but bills that key, and Check says so. An authentication error fails that job, marks
  the backend blocked and leaves its other jobs queued, shown as waiting for sign-in, until the
  user runs `codex login` and chooses **Signed in again**. Nothing is retried automatically. The
  raw output stays in `images/raw/` until it passes the image check. The path is labelled
  experimental and has only been tested against a stand-in `codex`, not a real login.
- **Hosted APIs** default to OpenRouter (`chat` style), Google's OpenAI-compatible endpoint
  (`images` style), the OpenAI API or NanoGPT (`https://nano-gpt.com/api/v1`, `images` style;
  **Check** reads its image list at `/images/models`, since its `/models` lists text models only,
  also for a NanoGPT address entered as another API). A base URL saved with a request path on the
  end (`/images/generations`, `/chat/completions`, `/models`, `/images`) is trimmed to the base.
  Each backend's **Connection** panel edits its name, model, API key and address (another API's
  base URL or a ComfyUI address) in place; saving a new address accepts its disclosure again. Keys are stored in the OS vault as `image-backend:<id>`.
  Enabling a hosted backend, a Codex backend or a remote ComfyUI server requires accepting a
  disclosure of what each request sends. Requests carry the prompt only. Provider-reported
  `usage` is stored as given. The tested request shapes are the two above; a model behind an
  aggregator is not assumed to work until an image comes back.
- **NSFW on an image API** (Vanta, 2026-10-07): an OpenRouter, NanoGPT or other image API backend has an
  **Also take NSFW requests** switch (`allows_nsfw`), off by default, for a provider whose terms
  allow such images. Google and the OpenAI API never offer it, and Codex stays safe-only. With it on,
  the disclosure adds that NSFW requests go to that provider under its terms, and turning it on for
  an existing backend asks for the disclosure again. The local check still runs before every
  dispatch and still fails closed; the switch only adds that backend to where NSFW requests may go.
  Prohibited requests are refused everywhere regardless. NovelAI's own image API is not an
  OpenAI-style endpoint, so it cannot be added as "Other" yet.

## One graphics card or two

The Companion never loads or unloads models: KoboldCPP, LM Studio or Ollama hold the text model and
ComfyUI holds the picture model, each in its own graphics memory. Local ComfyUI jobs wait while a reply
is being written and while a LoRA trains, so they never start at the same moment, but both models stay
loaded. When they don't both fit on one card, ComfyUI runs very slowly from system memory or fails.

- **Two cards:** start ComfyUI with `--cuda-device 1` (the second card) and keep the text model on the
  bigger one.
- **One card:** a smaller text model leaves room (Krea 2 Turbo's FP8 file needs about 14 GB, its NVFP4
  file about 9 GB and its Q4_K_M GGUF about 9 GB), or use a hosted image service for pictures.
- **Cards under about 8 GB:** a hosted image service.

### Krea 2 on smaller cards

ComfyUI moves the text encoder off the card while the model draws, so Krea 2 needs about its diffusion
model's file size plus 2 GB (sizes from the files on Comfy-Org/Krea-2 and the community GGUF repos,
2026-10-28): bf16 26.5, FP8 14.2, NVFP4 9.1, Q6_K 11.9, Q5_K_M 10.3, Q4_K_M 9.0, Q3_K_M 7.6 GB.

When the built-in FP8 file is too big for the biggest card, a Krea 2 server on this computer starts on
one that fits (Vanta, 2026-10-28: the app decides, the user overrides): a fitting Turbo file the server
already lists (Raw/Base and Edit models aside), else the one to download. NVFP4 comes first on a
Blackwell card (RTX 50-series), which runs it natively; other cards get the largest GGUF that fits. The
pick is kept as `unet_fit` (`hardware.fit_images`, run by Settings > Images, Check, the file list and
saving a backend) and used only while the user hasn't chosen a model; Model files shows it as the
default. A `.gguf` model loads through the ComfyUI-GGUF nodes' `UnetLoaderGGUF` in place of
`UNETLoader` (the one node swapped); their file list is merged into the model choices, and Check names
the nodes when the server lacks them. They need the `gguf` Python package, so the app doesn't install
them.

Settings > Models > This computer checks this for you (see [models.md](models.md#this-computer)), and
Settings > Images repeats any picture warnings.

## Content routing (F6)

`content.py` classifies the whole request (prompt, negatives, the events and captions it was
built from, the appearance description and relationship) with fixed local term lists. It never
asks a service. `routing.py` then decides where it may go:

| Tier | Goes to |
| --- | --- |
| `prohibited`: sexual content with a minor or someone presented as one, sexual depictions of real people, sexual violence | Nowhere; refused with the reason |
| `nsfw`: sexual content, nudity, graphic gore, anything not confidently safe, a classifier error, or marked by the user | A local ComfyUI, or an image API with the NSFW switch on; refused with a pointer to Settings when none is enabled |
| `safe` | Any enabled backend, in the user's order |

- The request is classified again at every dispatch, retry and fallback, and a job never becomes
  less strict than it was.
- A hosted provider's content refusal reclassifies the request as NSFW. With fallback on, it is
  offered only to a backend that accepts NSFW (never back to the one that refused it), so a
  safe-only provider is never tried.
- Known false positives: wording such as "steamy", "injured" or "chicken breasts" routes as NSFW.
  On the shipped city data that is 4 of 3,749 names and descriptions; the composer's own captions
  produce none (`tests/test_images.py`).

## Prompts

`companion/images/prompts.py` writes one descriptive paragraph in the shape Krea 2's guide asks for
(github.com/krea-ai/krea-2, `docs/prompting.md`), with no model: the style line as the medium (or a
chat photo's selfie or view framing), then the person as a camera would see them, what they wear in
this moment, what they are doing (a fixed present-tense line per activity, `prompts.PICTURES`; a
corrected event or one without an activity uses its summary) and where, an expression for the event's mood, the light for the
local hour and weather, and camera details when the style is a plain photograph. The character's
name is said as she, he or they (read from the appearance description; "they" when it never says),
impressions ("looks like someone who...") are dropped and backstory is cut from a clause ("a scar
from a derby fall" keeps the scar). The post's caption is not in the prompt: the feed shows it
under the picture. Other backends get the same paragraph, which reads as a plain description.

**Looks sheet.** Before the appearance description comes their looks sheet in words
(`companion/world/looks.py`, banks in `world/data/looks.json`): "A tall, athletic woman in her early
thirties with olive skin, an oval face, a defined jawline, a straight nose, almond-shaped hazel eyes,
dark brown hair in a ponytail and freckles." The sheet holds apparent age, height, weight, build, skin,
face shape, jaw and chin, nose, eye colour and shape, hair, facial hair and one noticeable feature. On
the character form (Show details > Looks) each field is optional: what the user sets wins, and an empty
field is drawn from the companion's id, coloured by the heritage their description names and with
weight worked out from height and build inside a plausible body-mass range (`bmi_limits`), so a roll
never pairs 4'10" with 350 lb. A drawn field is left out where the appearance text already speaks of
it, so a picture never gets two hair colours. Weight stays out of the picture (the build word carries
it) but is in their own prompt as "Looks:", so they answer "how tall are you?" the way their pictures
show them. Townsfolk draw height, build, hair, eye colour and their feature from their Matchlight looks
(`companion/world/dating.py`), so a dating card, its photo and a townsperson who becomes the main
character all show one person; becoming the main character copies the whole sheet onto the form.

**Style per backend.** Each backend can have its own **Style** (stored as `style` in its config), since
each model wants its own opening: a photo line for Krea 2, a tag-style line for an anime model, a
plainer one for GPT Image. A request is built with the general style from Settings > Images; when
it starts on a backend, `prompts.restyle` swaps the opening style line (and the camera details that
follow from a plain photo style) for that backend's own, or back to the general one for a backend
without one, so a retry or fallback elsewhere starts from the general style (`general_style` in
the inputs). The job records the prompt as sent. Memes keep their own opening. Profile pictures
use the chosen backend's style too. A backend's style is classified when saved: one that is not
plainly safe is refused on any backend that does not accept NSFW requests, as style LoRAs are.

## Jobs (F3, F4)

A job freezes its inputs: the prompt and negatives, the aspect, a seed, the events and their
revisions, the character version and appearance. It records the classification and its reasons,
the routing reason, the backend, provider, model, workflow, the appearance version and identity
method (the text description, or the adopted LoRA on ComfyUI; see [the LoRA maker](lora.md)), the
seed where the backend takes one, the output size and usage.

- States are `queued`, `running`, `completed`, `failed`, `cancelled` and `interrupted`. A refused
  request is stored as a `failed` job with the reason, so the post shows why.
- The post points at its current job. Queuing a new one makes it current; choosing an earlier
  finished version makes that one current. A result that arrives for a job that is no longer
  current is kept as another version and never replaces the choice.
- Retry repeats the original inputs. Choosing current settings, or a different backend, rebuilds
  them. If an event changed since, retrying the original is refused (M3) and a queued job for it
  is cancelled at dispatch.
- Fallback to the next eligible backend after a failure is off by default.
- After a restart, queued and running jobs become `interrupted`; nothing resumes on its own.
- Automatic images (off by default) need background activity on and no pause. They cover single
  event posts made after the setting was turned on, up to `daily_limit` in any 24 hours, never
  catch-up digests and never older posts. A refusal is not retried.
- At most `queue_limit` jobs wait or run at once.
- Images are saved in `images/` beside the workspace database. Backups hold the job records but
  not the image files. A restored workspace has its image keys cleared and automatic images off.

## Photos, selfies and memes in chat

Asked what they're up to ("what are you up to?", "wyd", "send me a pic"), the companion can answer
with a photo of the moment (`companion/images/photos.py`). "Send me a selfie" gets a selfie of the
same moment, "a pic of the view" a first-person photo with nobody in it (and so no likeness), and
"send me a meme", "make me laugh" or "cheer me up" a meme. The app decides from a fixed list of
phrasings, not the model, and a question about another time ("tomorrow", "tonight", "been up to")
asks for no photo.

- A selfie or view is another version of the moment's picture, on the same post. Each reply keeps
  the version it sent, the feed shows the newest, and asking again for the same kind in the same
  moment shows the one already made.
- A meme is a joke, not an event. Its captions come from templates that fit the companion's day
  (`companion/images/memes.py`: what their routine has them doing, rain, late night or morning), and
  the last few are not repeated. Each caption has a mood, and a few are "this, not that" pairs for
  a two-panel format. The interface draws the captions over the picture; no model is ever asked for
  text. Captions are classified with the rest.
- Memes need no image backend (Hit List #50). The picture under one comes from
  (`companion/images/meme_pictures.py`):
  - the starter pack in `companion/images/meme_data/pack`, public-domain and CC0 pictures shipped
    with the app, each credited in `pack.json`;
  - classic formats (`meme_data/formats.json`), downloaded blank from memegen.link in the background
    the first time memes are sent and kept in the data folder's `meme-formats` folder, never in the
    repository. Only the format's name is sent. Settings > Images > "Download classic meme formats"
    turns it off;
  - the user's own `Meme templates` folder in the data folder (Settings > Images > Open folder, on
    the PC). A picture there may have a JSON file of the same name beside it, in memegen's shape:
    `{"about": "...", "moods": [...], "boxes": [{"x", "y", "w", "h"}, ...]}`, boxes as fractions of
    the picture, top to bottom. Without one the text goes top and bottom and the picture fits any
    mood.
  With an image backend set up, about a third of memes are still made by it: the companion pulling a
  face or a simple fictional scene, square, on a post of its own that never reaches the feed. A
  meme on a template has no image job and no post in the feed either, and the chat keeps the
  template's own shape.
- Reaction GIFs (`companion/images/gifs.py`) are off until the user adds their own GIPHY key in
  Settings > Images, kept in the system's credential store and refused over plain-http Wi-Fi. Only a
  search word from a fixed list, picked by the meme's mood, is sent to GIPHY, never the user's
  words; only the G and PG ratings are asked for and kept, and the chat loads the GIF from GIPHY with
  its "Powered by GIPHY" credit. Searches are kept for six hours. An unasked GIF uses only searches
  already made (a missing one is fetched in the background for next time); asking for a GIF waits
  four seconds at most. Without a key, or with GIPHY not answering, a meme is sent instead.
- Realism > Their days > "Memes and GIFs" sets how often they send memes and GIFs unasked: never,
  now and then, true to life (default) or often. Asking for one always works unless it is Never.
  Memes and GIFs belong to eras with phones (modern and future cities).
- Pictures nobody asked for: now and then a reply comes with a photo or selfie of a moment not yet
  sent in chat (a seeded chance per reply), and a meme is likely when the user sounds bored or down.
  At most three a day, two hours apart, and the reply knows it chose to send it. When the companion
  may text first (Settings > Life), they sometimes text a photo of something they are out doing
  (errands, social, leisure; a seeded chance per moment), at most once a day. That text is a first
  message: the first-message rules decide when it may go out, it counts toward their daily cap, and
  its words are the moment's caption, with no model call. Settings > Images > "Let them send
  pictures without being asked" turns both off.

- The photo shows the companion's current routine slot, composed the way the simulation will
  compose it: the same agenda entry, plan and seed, and the wording prepared ahead for that entry
  when the current life model prepared it. Nothing asks a model to write anything.
- The image is made on a feed post keyed `photo:<event key>`. It has no event yet, so it stays out
  of the feed. When the simulation writes that slot's event, the event joins the photo's post
  instead of getting a post of its own or a place in a digest, so the feed shows the same picture
  and the event is told once. A batch picks photographed slots first, like planned ones.
- The request is classified and routed like any other (F6). With nowhere allowed to send it
  (no backend, only safe-only backends for an NSFW moment, or the prohibited tier) no photo is sent,
  and the reply is not told about one. Sleep, quiet slots, a pause and the setting being off send
  none either.
- A reply that sends a photo gets one context section with the moment, so it can mention the photo.
  Asking again in the same slot shows the same photo without making another.
- `chat_photos` in the image settings turns it off (on by default; it still needs a backend).
- In the chat, each style shows the picture under the reply with a line while it is on its way.
  The Visual novel stage also shows the latest photo (not meme) behind the portrait.

## Profile pictures

Right after a companion is created, when an image backend is enabled, the app offers three
pictures of them (`companion/lora/portraits.py`, page `src/features/appearance/Portraits.tsx`). The
step can be skipped and run again from the Character page (**Profile pictures**).

1. **Profile picture**: waist up, facing the camera, in an everyday outfit, with an expression that
   fits their personality.
2. **Three-quarter view** in a second everyday outfit, made from picture 1.
3. **Face close-up**, also made from picture 1.

- The expression comes from words in their personality, identity and voice (shy, wry, playful,
  warm and so on) and the two outfits are a fixed pick for that companion from a short list. No
  model writes anything; the description and all three shots can be edited before sending.
- Pictures 2 and 3 each send picture 1 along as a reference, so the set shows one person. The whole set goes to the first enabled backend that can take a reference picture:
  **Codex** (attached with `codex exec --image`), a **chat-style API** such as OpenRouter (the
  picture goes in the message), the **OpenAI API** (`/images/edits`), or a **ComfyUI** server with
  its *reference workflow*, the built-in one or the user's own with `{{reference_image}}` as a
  LoadImage node's image (the app uploads the picture through `/upload/image`). Google's OpenAI-compatible endpoint and other `images`-style APIs
  cannot take one.
- When no enabled backend can, nothing is sent and the page says so. The user can choose to make
  all three from the description alone; the page then says they may not look like one person.
- Each picture is classified and routed like any image: NSFW goes only to a backend that accepts it and
  Prohibited is refused. When picture 1 fails or is refused, the other two are not made. **Make
  this one again** remakes that picture with a new seed; remaking picture 1 remakes all three.
- Finished pictures are kept as they are ready (**Keep** shows again only if keeping failed): this adds them to the character's reference pictures (as
  `generated`, for training) and makes picture 1 the companion's picture: in the conversation
  header, the Community style's avatars and the Visual novel stage. Any reference picture can be
  chosen instead in Look and LoRA, and removing it brings back their initial.
- The set runs through the LoRA maker's generation runner (one picture at a time, the shared
  backend limits and the single Codex slot) as a `lora_generations` row of kind `portraits`, which
  the LoRA maker's own list leaves out.
- Every reference path has only been tested against stand-ins (a fake `codex`, mocked HTTP for
  OpenRouter, OpenAI and ComfyUI), not a real backend.
- On Codex, picture 1 is made from the companion's character sheet (below).

## Character sheet (Codex)

Before the first picture of a companion goes to a **Codex** backend, the app asks Codex for a
character reference sheet (`companion/images/sheet.py`): one landscape picture, 1536 x 1024, in three
panels on a grey studio background: a close-up of the face, a front view from the neck down, and a
back view from head to feet. The sheet is saved as the companion's identity reference (in
`images/sheets/`, table `character_sheets`) and never posted. The picture that was asked for is
then made with the sheet attached, so the first picture of someone costs two Codex calls. Every
later Codex picture of them (feed posts, chat photos and selfies, memes of them, profile picture 1
and the LoRA maker's prepared pictures) attaches the same sheet and asks Codex to keep the face,
hair, skin tone and build and to take the outfit, pose and setting from its own description.

- The sheet's prompt is a fixed template (Vanta's production reference-sheet prompt, 2026-10-11),
  filled without a model: their looks sheet and the visible part of their appearance, the profile
  picture's everyday outfit unless the appearance says what they wear, and the backend's picture
  style (`backends.style_for`). It asks for the largest landscape size Codex makes rather than 16K.
- When they already have a profile picture, it is attached and the sheet follows it; otherwise the
  description is the reference.
- Editing their looks or appearance makes a new sheet the next time a Codex picture of them is made.
- The sheet is classified and must be eligible for the backend like any request. When it is not, or
  it fails for a reason other than sign-in, the picture is made from the description alone. A
  sign-in error fails the picture and stops the Codex queue as usual.
- The sheet and the picture run one after the other inside the single Codex slot, so Codex calls
  stay serial. Views (pictures of what they see), memes of something else, other backends and
  Matchlight photos make no sheet.
- Pictures that follow the sheet record "text description and their character sheet" as how they
  drew the character. Sheets go with the character (kept by Start over, removed with the companion)
  and are carried in backups.

## Interface

Settings has an **Images** section: add a ComfyUI server, a Codex backend or an image API, accept
what it receives, order, check, enable or remove each one, and set automatic images, fallback,
the daily limit, the shape and a style line. A blocked Codex backend shows the sign-in step and a
**Signed in again** button. In the Feed, each post shows its image, a line saying what is
happening, and **Make an image**, **New version**, **Cancel image** or **Retry**. **Image details**
lists every request for the post with its backend, model, likeness method, content check,
routing, seed and prompt, lets the user pick between finished versions, and can mark the next
request NSFW so it only goes to a backend that accepts NSFW. The feed refreshes every few seconds while an image is in progress.
Display logic that needs no browser is in `src/features/feed/imageState.ts`.

## API

All writes need the `x-companion-client: workspace` header.

| Method and path | Purpose |
| --- | --- |
| `GET`, `PUT /api/images/settings` | `automatic_images`, `chat_photos`, `daily_limit` (0 to 24), `queue_limit` (1 to 20), `fallback`, `aspect` (`square`, `landscape`, `portrait`), `style` |
| `GET /api/images/backends` | Backends in order, with `local`, `accepts_nsfw`, `allows_nsfw`, `nsfw_switch` (whether the switch is offered), `disclosure`, `blocked_reason`, `has_key`, `model_files` (ComfyUI); never a key |
| `POST /api/images/backends` | `{kind, provider?, label?, base_url?, model?, workflow?, reference_workflow?, unet_name?, clip_name?, clip_type?, vae_name?, cli_path?, api_style?, api_key?, controlled_machine?, allows_nsfw?, concurrency?, enabled?, accept_disclosure?}` |
| `PUT /api/images/backends/{id}` | The same fields; saving a key clears a sign-in block; changing the address or turning `allows_nsfw` on needs the disclosure again |
| `POST /api/images/backends/{id}/move` | `{position}` |
| `DELETE /api/images/backends/{id}` | Remove it; its queued jobs fail at dispatch |
| `POST /api/images/backends/{id}/check` | `{ok, summary, details, install}`; spends no generation quota; `install` lists node packs (`{id, label}`) the app can put into a ComfyUI on this computer |
| `POST /api/images/backends/{id}/install-nodes/{pack}` | Installs a listed node pack into that ComfyUI's custom_nodes (loopback only, PC only); `{installed, folder}` |
| `GET /api/images/backends/{id}/workflows` | ComfyUI's saved `{workflow, reference_workflow}` text (empty when unset) and the built-in ones as `built_in` and `built_in_reference`, for editing on the PC; refused from a paired phone |
| `GET /api/images/backends/{id}/files` | ComfyUI only: `{ok, error, family, defaults, sampler_defaults, options, matching, character_lora}`, the files the server offers each of the family's built-in loaders (`unet_name`, `clip_name`, `clip_type`, `vae_name`, Krea 2's `ref_unet_name`, or `ckpt_name`), its LoRAs (`lora`, without the character's own) and KSampler's `sampler_name` and `scheduler` lists, the family's own first and listed in `matching` |
| `GET /api/images/model-links` | `{links: [{name, role, file, url, licence, family}]}`: download pages for each family's built-in workflow files |
| `POST /api/images/backends/{id}/unblock` | The user signed in to Codex again |
| `POST /api/images/preview` | `{post_id, marked_nsfw?}`: the prompt, classification and route, without queuing |
| `POST /api/images/jobs` | `{post_id, backend_id?, marked_nsfw?}`: queue a manual image |
| `GET /api/images/jobs?post_id=` | Every job for a post, newest first |
| `GET /api/images/jobs/{id}` | One job |
| `POST /api/images/jobs/{id}/cancel` | Cancel a queued or running job |
| `POST /api/images/jobs/{id}/retry` | `{current_settings?, backend_id?}` |
| `POST /api/images/jobs/{id}/select` | Make a finished version the post's image |
| `GET /api/images/jobs/{id}/file` | The image file |
| `GET /api/images/photos/{message_id}` | The picture a reply sent: `{post_id, kind, summary, top_text, bottom_text, status, job_id, ref, error, in_feed}` |

A post's `image` is `{status, job_id, ref, error, updated_at}`: `ref` is the id of the job whose
file is shown, which can differ from `job_id` while a replacement is queued, running or failed.
