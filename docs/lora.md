# Character LoRA maker

[Back to the README](../README.md)

A LoRA is a small adapter that teaches an image model what one character looks like. The
Companion guides the whole job (PRD "Character LoRA maker requirements"): gather reference
pictures, review them, train with AI Toolkit, evaluate, then deliberately adopt the result for future images. An
adapter trained elsewhere can be imported instead, and a character can always stay on its text
description. The code is in `companion/lora/`; files live in `lora/` beside the workspace database.

## Prepare and review

- The user adds each picture; the app never reads folders on its own. Only PNG and JPEG are
  accepted, because AI Toolkit reads those two formats. An exact copy of a picture already in the
  set is refused (SHA-256). The interface sends a 64-bit difference hash with each picture, and
  pictures within 6 bits of each other are flagged as near duplicates.
- Each picture records where it came from (`own_work`, `commissioned`, `licensed`, `generated`
  or `unknown`) and a source note. Training refuses any training picture whose source is still
  `unknown`.
- Each picture is a **training** picture, a held-out **evaluation** reference, or **excluded**
  with a reason. A near duplicate split across training and evaluation blocks training, so an
  evaluation reference is never a copy of a training picture.
- The original file is never changed. A crop is drawn in the interface and stored as a separate
  copy beside the original.
- Suggested captions are `[trigger], <appearance description>`; AI Toolkit replaces `[trigger]`
  with the trigger word. Suggestions are only a starting point and never overwrite a caption the
  user wrote. Nothing looks at the picture to caption it.

## Adapters and appearance versions

- An imported adapter must be a valid `.safetensors` file: the header is read and the tensor data
  must end exactly where the file does. Its format (`lora`, `lokr` or `unknown`) comes from the
  tensor names. The user states its base model and trigger word. Krea 2 adapters carry the
  license note: redistributed derivatives need the Krea 2 Community License and a name starting
  with "Krea".
- An **appearance version** is how images draw the character from the moment it is adopted:
  `text` (the appearance description) or `lora` (an adapter at a strength). Adopting creates a
  new numbered version; nothing is adopted automatically, and a failed training run never changes
  it.
- Image jobs freeze `appearance_version_id`, `appearance_version` and the adapter details with
  their other inputs, so older posts keep the look they were made with and a retry repeats it.
- Only ComfyUI applies the adapter. The ComfyUI adapter inserts a `LoraLoaderModelOnly` node after
  the workflow's first model loader (`unet_name` or `ckpt_name`) and puts the trigger word at the
  start of the prompt. Codex and hosted APIs draw from the text description, and the job records
  `text description only; this backend cannot apply the adopted LoRA`.
- ComfyUI loads adapters from its own `models/loras` folder. When the user names that folder in
  the LoRA settings, adopting copies the adapter there as
  `prospero-<name>-<first 8 of sha256>.safetensors`; otherwise the app says which name to copy it
  to. The ComfyUI check in Settings reports when the adopted adapter is missing.
- Removing an adapter deletes its file but keeps its record, because images may name it. The
  adopted adapter cannot be removed.

## Configure and train

**The target trainer is [AI Toolkit](https://github.com/ostris/ai-toolkit) at commit `ecee894`
(2026-09-27), training Krea 2 through its built-in `krea2` architecture. This is not verified on
hardware**: it was written from that commit's source and has only run against the stand-in
trainer in `tests/stand_in_trainer/`. The app never installs AI Toolkit or downloads weights.

- The user names AI Toolkit's own Python interpreter, its checkout folder and the base model
  (default `krea/Krea-2-Raw`: train on Raw, generate on Turbo). The check only looks for the files
  (`run.py`, `extensions_built_in/diffusion_models/krea2`); it runs nothing.
- Before training, the user accepts a disclosure: training is local and pictures never leave the
  computer, but AI Toolkit downloads whatever the config names that is not in its Hugging Face
  cache (Krea 2 Raw is gated, so it needs the license accepted and `HF_TOKEN` in AI Toolkit's
  `.env`; also the Qwen3-VL 4B text encoder and the Qwen image VAE). A local folder as the base
  model avoids the base model download. The user also confirms the pictures show a fictional
  adult character.
- The page states the community-reported requirements, marked unverified: a 16 to 24 GB NVIDIA
  GPU, about 40 to 45 minutes on an RTX 3090, up to most of a day on 12 GB, tens of gigabytes of
  disk, and disputed step counts (3,000 or more reported to overfit).
- Training refuses a dataset the review blocks, and classifies the appearance and every caption
  with the image classifier: NSFW may train locally, Prohibited never trains.
- A run freezes its dataset (each picture's digest, caption with the trigger word in place,
  rights and source), its options and the exact config. Captions are written with the trigger
  word substituted, because AI Toolkit does not add it when text embeddings are cached.

The generated config (`lora/runs/<run>/config.json`, JSON, which AI Toolkit accepts):

| Key | Value |
| --- | --- |
| `job`, `process[0].type` | `extension`, `sd_trainer` |
| `model` | `name_or_path` from settings, `arch: krea2`, `quantize` and `quantize_te` on, `low_vram` optional |
| `network` | LoKr by default (`lokr_full_rank: true`, `lokr_factor: -1`), or LoRA with `linear` = `linear_alpha` = rank |
| `train` | batch 1, 1,500 steps, `adamw8bit` at 1e-4, bf16, flowmatch, gradient checkpointing, cached text embeddings, sampling off (evaluation happens in ComfyUI) |
| `datasets[0]` | the run's `dataset/` folder, `.txt` captions, latents cached, resolution `[512, 1024]` (or `[512]`) |
| `save` | float16 every 250 steps, keeping 4 |

Running: `<python> run.py <config.json>` in the AI Toolkit folder, as a child process in its own
process group. One run trains at a time, a run does not start while ComfyUI is making an image,
and local ComfyUI images wait while a trainer runs. Chat continues, but shares the GPU if the chat
model is local.

- **Progress** is the step count AI Toolkit's progress bar printed (`120/1500 [`), shown only when
  it has printed one. There is no time estimate. The last 60 lines of output are kept with the
  run; the full log is in `lora/runs/<run>/trainer.log`.
- **Cancel** sends Ctrl+C (Ctrl+Break on Windows), waits 20 seconds, then ends the process. On
  Windows only the trainer process is ended; worker processes it started may need closing by
  hand. Training cannot pause.
- **Checkpoints** are AI Toolkit's `<name>_<step>.safetensors` files. Each is checked as
  safetensors and hashed when the trainer exits. A verified checkpoint can be kept as its own
  adapter.
- **Resume** reruns the same config after a failure, cancellation or interruption, only when a
  verified checkpoint exists. AI Toolkit continues from the newest file in its folder, so any file
  that failed the check is moved to `set-aside/` first. **Restart** begins again from step 0 and
  moves the earlier checkpoints to `discarded-attempt-<n>/`; nothing is deleted.
- A run that exits cleanly with a verified final file becomes an adapter. It is not adopted;
  the user evaluates and chooses. Any other ending is `failed` with the exit code and last line.
- After the app restarts, a run that was training becomes `interrupted`. If its process is still
  alive, its pid is kept and no new run starts until it is gone. Closing the app normally ends the
  trainer.

## Evaluate

An evaluation renders a fixed set (version 1) on the first enabled ComfyUI server on this
computer, because only ComfyUI applies the adapter. Each prompt has a fixed seed and is rendered
twice: with the adapter (`<trigger>, <name>`) and, for comparison, from the text description alone.
Images render one at a time, and the next one waits while a chat reply is being written, the
same priority local ComfyUI image jobs follow.

| Key | Prompt (after "Natural photograph.") | Seed | Shape |
| --- | --- | --- | --- |
| `portrait` | head and shoulders portrait, plain background, soft even light | 1101 | portrait |
| `full_body` | full-body photo standing in a plain studio, whole outfit visible | 1102 | portrait |
| `cafe` | reading at a small café table, candid photograph | 1103 | landscape |
| `street` | walking along a city street in the afternoon | 1104 | landscape |
| `golden_hour` | outdoors at golden hour, warm backlight | 1105 | square |
| `night_lamp` | indoors at night lit by a single table lamp | 1106 | square |
| `expression` | laughing, close-up of the face | 1107 | square |
| `traits` | close-up showing the appearance description | 1108 | portrait |

- Every request is classified like any image request; a Prohibited one is recorded as refused and
  never sent. NSFW is allowed because only a local server is used.
- Every output, its prompt, seed, size, workflow, model and strength, and every failure are kept
  and listed. The user can mark an image good or weak; nothing is hidden or ranked away.
- Held-out evaluation references are listed with the evaluation for side-by-side comparison. They
  are never sent to ComfyUI or used as inputs.
- Evaluation does not start while training runs, and training does not start while an evaluation
  renders. After a restart, unfinished images are marked interrupted.

## Recover and export

- Backups carry every adapter that has not been removed (`lora/adapters/` in the archive, stored
  uncompressed and listed with its SHA-256 in the manifest). Restore checks each digest. Reference
  pictures, training folders and images are not in backups; a restored workspace lists missing
  pictures and refuses to train until they are added again.
- **Export** gives a zip with the adapter, `adapter.json` (format, base model, trigger word,
  digest, origin, the run's options and a dataset summary of counts, rights and picture digests)
  and `LICENSE-NOTICE.txt`. It never includes pictures, captions or local paths. A Krea 2 adapter
  is named `Krea-<name>.safetensors`, as the Krea 2 Community License asks of redistributed
  derivatives.

## Interface

Character has a **Look and LoRA** button that opens a guided page with six steps: **Prepare**
(add pictures; source, rights and use for each), **Review** (blocking problems and advice,
captions, crops drawn with sliders and saved as copies), **Configure** (the target trainer marked
"Not verified on hardware", its requirements and what cancelling stops, the trainer settings, run
options, the download disclosure and the fictional-adult confirmation), **Train** (state,
reported progress, checkpoints with their check, the trainer's output, cancel, resume and
restart), **Evaluate** (the fixed set with and without the adapter side by side, held-out
references, every failure, good and weak marks) and **Adopt** (the current appearance, every
adapter with adopt, export and remove, importing an adapter, and the version history). The
browser computes each picture's difference hash and draws crops; logic that needs no browser is in
`src/features/appearance/loraState.ts`.

## API

All writes need the `x-companion-client: workspace` header. Uploads send the file itself as the
request body.

| Method and path | Purpose |
| --- | --- |
| `GET`, `PUT /api/lora/settings` | `python_path`, `trainer_dir`, `base_model`, `comfy_lora_dir` |
| `GET /api/lora/references` | Pictures with `similar_to`, and `review`: counts, `blocking`, `advice`, `ready` |
| `POST /api/lora/references?name=&dhash=` | Add a picture (body: PNG or JPEG, up to 30 MB) |
| `PUT /api/lora/references/{id}` | `{rights?, source_note?, role?, exclusion_reason?, caption?}` |
| `POST /api/lora/references/{id}/crop?x=&y=&width=&height=` | Store a cropped copy (body: the copy) |
| `DELETE /api/lora/references/{id}/crop` | Drop the cropped copy |
| `DELETE /api/lora/references/{id}` | Remove the picture and its files |
| `GET /api/lora/references/{id}/file?cropped=` | The original, or the cropped copy |
| `POST /api/lora/references/captions` | Suggest captions for pictures without the user's own |
| `GET /api/lora/adapters` | Adapters, newest first |
| `POST /api/lora/adapters/import?name=&base_model=&trigger=&note=` | Import (body: `.safetensors`, up to 4 GB) |
| `DELETE /api/lora/adapters/{id}` | Remove the file, keep the record |
| `GET /api/lora/appearance` | `current` and every adopted version |
| `POST /api/lora/appearance` | `{method, adapter_id?, strength?, note?}`; returns `install` for a LoRA |
| `GET /api/lora/trainer` | The target trainer, `verified: false`, disclosure, requirements, defaults and the file check |
| `GET /api/lora/runs` | Runs, newest first |
| `POST /api/lora/runs` | `{name, trigger, network?, rank?, steps?, learning_rate?, save_every?, resolution?, low_vram?, attest_fictional_adult, accept_disclosure}` |
| `GET /api/lora/runs/{id}` | State, reported progress, checkpoints, log tail, frozen dataset and config |
| `GET /api/lora/runs/{id}/log` | The trainer's console output |
| `POST /api/lora/runs/{id}/cancel`, `/resume`, `/restart` | Stop, continue from a verified checkpoint, or begin again |
| `POST /api/lora/runs/{id}/keep` | `{step}`: make a verified checkpoint an adapter |
| `GET /api/lora/evaluations?adapter_id=` | Evaluations with every image, plus the prompt set |
| `POST /api/lora/evaluations` | `{adapter_id, strength?, include_baseline?}` |
| `GET /api/lora/evaluations/{id}` | One evaluation |
| `POST /api/lora/evaluations/{id}/cancel` | Stop rendering; finished images stay |
| `PUT /api/lora/evaluation-images/{id}/rating` | `{rating: '' \| 'good' \| 'weak'}` |
| `GET /api/lora/evaluation-images/{id}/file` | The rendered image |
| `GET /api/lora/adapters/{id}/export` | The export zip |
