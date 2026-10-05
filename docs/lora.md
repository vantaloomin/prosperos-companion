# Character LoRA maker

[Back to the README](../README.md)

A LoRA is a small adapter that teaches an image model what one character looks like. The
Companion guides the whole job (PRD "Character LoRA maker requirements"): gather reference
pictures, review them, train, evaluate, then deliberately adopt the result for future images. An
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
