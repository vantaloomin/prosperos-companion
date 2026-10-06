# Acceptance status

[Back to the README](../../README.md)

Where the build stands against the [acceptance matrix](product-requirements.md#acceptance-and-measurement),
from an end-to-end pass on 2026-10-05. This is not the release evidence the matrix asks for: it ran
in a Linux cloud container, not on the declared Windows reference machine, against stand-in model,
image and MCP servers, with no model weights. Use it to see which rows have been exercised where
features meet, what broke and what is still open.

**Result key.** *Pass*: driven end to end here and behaved as the row requires. *Fail, then fixed*:
broke, fixed in the linked pull request with a regression test, then passed. *Covered by tests*: not
re-driven here; automated tests exercise it. *Not testable here*: needs hardware, weights, Windows,
a person or a real service.

## How it was run

- `scripts/acceptance/standins.py` serves an OpenAI-compatible chat and embeddings API (port 1234)
  that logs every request body, and a ComfyUI API (port 8188) that returns a small PNG after a
  delay. `POST /control` changes the per-word and image delays.
- `scripts/acceptance/serve.py` runs the real app with a clock the driver can move forward or back
  (`POST /acceptance/clock`); the host clock is never changed.
- `scripts/acceptance/journeys.py` drives the cross-feature journeys over HTTP and inspects what
  reached the model; the interface was driven in Chromium with Playwright for the feed, the
  responsiveness timings and the accessibility journeys.

```sh
python scripts/acceptance/standins.py --log requests.jsonl
COMPANION_DATA_DIR=<empty dir> COMPANION_API_KEY=k python scripts/acceptance/serve.py
python scripts/acceptance/journeys.py --log requests.jsonl      # 13 checks
```

## Rows

| Acceptance area | Result | What was checked |
| --- | --- | --- |
| Chat and feed coherence | Fail, then fixed ([#71](https://github.com/vantaloomin/prosperos-companion/pull/71), [#77](https://github.com/vantaloomin/prosperos-companion/pull/77)) | One event through return batch, review, post, image, a chat about the post and a correction. Chat, feed and recall shared the corrected revision and kept the earlier one as history, but the corrected event kept the old place in its details, so a new image prompt said "at Artifact Coffee … at The Charmery", and the finished picture of the old version was labelled with the corrected summary. Forking a timeline then dropped every post whose event had been corrected. |
| Immediate correction | Pass | A memory corrected while a slow reply streamed: the reply was kept as `withheld` with its reason shown, and the next reply used only the new value. Consolidation commits nothing when the memory revision changes (`tests/test_consolidation.py`). A correction is one transaction, so there is no partial state to recover. |
| Memory isolation | Fail, then fixed ([#74](https://github.com/vantaloomin/prosperos-companion/pull/74)) | Every model request body was logged and searched. Excluded and deleted facts stayed out of the system prompt, but the companion's replies to their source messages were still sent as conversation, repeating them. A forked, activated timeline and a second workspace leaked nothing after the fix. |
| Forgetting and restoration | Fail, then fixed ([#74](https://github.com/vantaloomin/prosperos-companion/pull/74), [#81](https://github.com/vantaloomin/prosperos-companion/pull/81)) | Same leak as above. After the fix: no excluded or deleted words in chat, embeddings, phrasing, suggestions or consolidation requests; restoring a backup taken earlier kept a later deletion deleted and left the workspace paused with automatic memory off. Conversation search then still found the companion's reply to a deleted message; it now leaves that reply out too ([#81](https://github.com/vantaloomin/prosperos-companion/pull/81)). |
| Time reconciliation | Pass | Clock moved back 30 hours (`clock_behind`, nothing replayed), forward 14 days (3 slots, all idempotency keys unique), a restart in between (agenda and events unchanged), and repeat reconciles (`not_due`). DST, timezone change and filled-in versus always-running agenda are covered by `tests/test_life.py` and `tests/test_circle.py`. |
| Shared compute | Fail, then fixed ([#74](https://github.com/vantaloomin/prosperos-companion/pull/74)) | Chat during a running ComfyUI job and during prepared wording (T9). The reply's first words arrived after one stand-in token in both cases, but accepting the message waited for the query embedding, which queued behind background phrasing: 213–246 ms against an idle 72–94 ms. After the fix it was 21–56 ms. Training and evaluation priority are covered by `tests/test_lora_*.py`; the reference GPU is not available here. |
| Responsiveness | Fail, then fixed ([#74](https://github.com/vantaloomin/prosperos-companion/pull/74), [#81](https://github.com/vantaloomin/prosperos-companion/pull/81)) | `scripts/acceptance/responsiveness.py` seeds 10,000 messages, 1,225 events and 1,000 posts, then times the interface in Chromium (30 samples, P95). Before: a sent message took 535 ms to appear because the reply's context was built before the request returned and on the server's main loop, which also held every other request for 280–350 ms; Stop took 192 ms to show with 3,160 messages loaded; jumping to a search result took up to 4.8 s. After: own message shown 70 ms, Stop shown 119 ms (71 ms with 3,160 loaded), opening Chat 72 ms, Feed 167–182 ms, Today 147 ms, Memories 107 ms, earlier messages 145 ms, search results 66 ms, jump to a result 1,097 ms, older posts 230 ms. Linux container, not the reference machine; model first-token and image times excluded. The context preview takes 413 ms at this size; it is not a control and loads in the background. |
| Accessibility | Fail, then fixed ([#81](https://github.com/vantaloomin/prosperos-companion/pull/81)) | Keyboard-only journeys in Chromium through setup, chat (send, stop, another reply, versions, search), memory correction, feed, cancelling an image job and a training run, backups and a restored workspace, logging where focus went after each key. Focus fell to the page body after a dozen common actions; a stopped reply was announced as "The reply ended: Stopped.."; at 320 px Memories scrolled sideways and the bottom navigation hid Settings; one heading-order violation. After the fixes every journey passes, and axe reports 0 violations in both colour schemes at 1280 and 400 CSS px at 200% and with reduced motion. Not tested: a real Windows screen reader. Questions for that run: notices that appear already holding their text may not be announced; the Memories notice may be announced twice; a finished reply announces "Mira replied." without its text (a design choice to confirm with users); training "Step N of M" updates may be chatty. The app is dark-only, so the light scheme looks the same. |
| Recovery and privacy | Pass | Backup with images, then a restore into the same workspace (`python -m companion.launch --restore`, and Settings > Backups > Restore on next start): history, events, the image file and memory statuses came back; keys were not restored. Interrupted saves, commits and jobs are covered by `tests/test_conversation.py`, `tests/test_life.py`, `tests/test_images.py` and `tests/test_lora_training.py`. |
| Standalone delivery | Not testable here | Needs a clean Windows machine. CI's `windows-install` and `clean-launch` jobs install, upgrade, restore, uninstall and launch on Windows runners. On Linux, relaunching or restoring within about a minute of closing the app can report "Close Prospero Companion" because the port is still in TIME_WAIT. |
| Current-context tools | Covered by tests | `tests/test_context_tools.py` and the MCP SDK interop job; lookups were not configured in this run. |
| Absence and permission behaviour | Covered by tests | `tests/test_traits.py` (neutral without traits, intensity, removal, reset, pause is not absence, neutral controls) and `tests/test_notifications.py` (quiet hours, the daily cap, digests; traits never raise frequency). Desktop notifications were not driven here: the container has no notification surface. |
| Memory formation and authority | Fail, then fixed ([#81](https://github.com/vantaloomin/prosperos-companion/pull/81)) | `tests/test_memory_formation.py`, `tests/test_memory_acceptance.py`. In this run "my sister Jo is visiting next Saturday" produced no memory. It now forms the person (Sister: Jo) and a dated plan (Visit from Jo, next Saturday, marked uncertain because "next Saturday" can mean either of two days), and "my visit got cancelled" updates that plan. |
| Relationship continuity, Personal memory over time, Retrieval usefulness, Model behaviour | Not testable here | Need real text models and annotated review; the stand-in model only echoes. The annotated fixtures in `tests/test_memory_acceptance.py` cover current-versus-historical values. |
| Image identity, Codex path resilience, Image content routing, LoRA workflow | Not testable here / covered by tests | Need Krea 2 weights, a GPU, a Codex login or a hosted key. Routing, Codex failure handling and the LoRA state machine are covered by `tests/test_images.py` and `tests/test_lora*.py`. |
