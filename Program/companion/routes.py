"""Local HTTP API for the Companion backbone."""
import json

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse

from companion import (
    auto_backup,
    backup,
    cast,
    character_helper,
    characters,
    chats,
    conversation,
    data_folder,
    drafting,
    events,
    logs,
    message_edits,
    notifications,
    pictures,
    prompt_library,
    recap,
    restore,
    self_facts,
    sidecar,
    start_over,
    text_models,
    timelines,
    workspace,
)
from companion.identity import APP_ID, VERSION
from companion.imports import cards
from companion.memory import consolidation, formation, pairs, records
from companion.models import (
    CastDraftRequest,
    CastFocus,
    CastSwitch,
    CharacterCardFile,
    CharacterDefinition,
    CharacterDraftRequest,
    CharacterRevision,
    CharacterSplitRequest,
    ChatRead,
    ConnectionUpdate,
    EventCorrection,
    EventProposal,
    FieldDraftRequest,
    MemoryCorrection,
    MemoryCreate,
    MemoryDelete,
    MessageCreate,
    MessageEdit,
    NotificationCheck,
    NotificationSettingsUpdate,
    PerceptionRequest,
    PromptUpdate,
    RecapRead,
    SettingsUpdate,
    SidecarRequest,
    StartOverConfirm,
    TimelineFork,
    TimelineUpdate,
    TownSeed,
)
from companion.world import looks, perception

router = APIRouter(prefix='/api')


def db(request: Request):
    return request.app.state.database


@router.get('/health')
def health():
    return {'app_id': APP_ID, 'version': VERSION}


@router.post('/logs/open-folder')
def open_log_folder():
    """Show the folder holding the log on the PC, for "Open the log folder" under an error."""
    folder = logs.file_path().parent
    logs.open_folder(folder)
    return {'folder': str(folder)}


@router.get('/settings')
def read_settings(request: Request):
    return workspace.read(db(request)) | features(request)


@router.put('/settings')
def update_settings(request: Request, body: SettingsUpdate):
    return workspace.update(db(request), body) | features(request)


def features(request: Request) -> dict:
    """Switches the interface reads with the settings; they are set on the PC, not saved here."""
    return {'lora_maker': request.app.state.lora_maker}


@router.post('/pause')
def pause(request: Request):
    return workspace.pause(db(request))


@router.post('/resume')
def resume(request: Request):
    return workspace.resume(db(request))


@router.get('/connection')
def read_connection(request: Request):
    """The conversation's model profile, in the shape of the single connection before profiles."""
    with db(request).connect() as connection:
        return {'connection': text_models.connection_summary(connection)}


@router.put('/connection')
def save_connection(request: Request, body: ConnectionUpdate):
    """Quick setup: point the conversation at an OpenAI-compatible or local server. Saving never contacts it."""
    return text_models.quick_save(db(request), request.app.state.vault, body)


@router.get('/companion')
def read_companion(request: Request):
    with db(request).connect() as connection:
        return {'companion': characters.current(connection)}


@router.post('/companion')
def create_companion(request: Request, body: CharacterDefinition):
    return characters.create(db(request), body)


@router.post('/companion/draft')
async def draft_companion(request: Request, body: CharacterDraftRequest):
    """A drafted definition for the form to review; nothing is saved."""
    return await drafting.draft(request.app.state, body)


@router.post('/companion/draft/field')
async def draft_field(request: Request, body: FieldDraftRequest):
    return await drafting.redo_field(request.app.state, body)


@router.post('/companion/draft/split')
async def split_character(request: Request, body: CharacterSplitRequest):
    """A whole pasted character split into the form's fields for review; nothing is saved."""
    return await character_helper.split(request.app.state, body)


@router.post('/companion/perception')
def perception_suggestions(request: Request, body: PerceptionRequest):
    """Bank picks for "How others see them" and "How they see themselves" that fit the form's words, and, for a
    saved companion, what an empty field uses. No model is involved."""
    with request.app.state.database.connect() as connection:
        companion = characters.current(connection)
    found = perception.suggestions(body.definition, companion['id'] if companion else 'new')
    return found if companion else {**found, 'automatic': None}


@router.post('/companion/looks')
def looks_suggestions(request: Request, body: PerceptionRequest):
    """What each empty looks field uses for a saved companion (drawn from their id, leaving out what the appearance
    already says), and suggestions for the word fields. No model is involved."""
    with request.app.state.database.connect() as connection:
        companion = characters.current(connection)
    automatic = looks.automatic(body.definition, companion['id']) if companion else None
    return {'automatic': automatic, 'options': looks.options()}


@router.post('/companion/draft/card')
def read_character_card(body: CharacterCardFile):
    """A character card file's text, for the paste box to show before anything is sent to a model."""
    return cards.read_card(body.filename, body.data)


@router.post('/sidecar')
async def sidecar_message(request: Request, body: SidecarRequest):
    """One message to the sidecar: a reply and proposed changes. Nothing is stored or applied."""
    return await sidecar.chat(request.app.state, body)


@router.post('/conversation/messages/{message_id}/edit')
def edit_message(request: Request, message_id: str, body: MessageEdit):
    """New wording for one of the companion's replies, keeping the old wording for Undo."""
    return message_edits.edit(db(request), message_id, body.text, body.expected_text)


@router.get('/companion/cast')
def companion_cast(request: Request):
    """Every companion in the workspace: the main character and those who stepped back."""
    return {'members': cast.members(db(request))}


@router.get('/companion/cast/draft')
def cast_draft(request: Request, key: str):
    """A profile for a townsperson the main character has met, from their sheet; nothing is saved."""
    return cast.draft(db(request), key)


@router.post('/companion/cast/draft')
async def cast_fleshed(request: Request, body: CastDraftRequest):
    """The same profile written out by the text model; nothing is saved."""
    return await cast.fleshed(request.app.state, body.key)


@router.post('/companion/cast/switch')
def cast_switch(request: Request, body: CastSwitch):
    """The townsperson becomes the main character; the current one steps back with their history."""
    return cast.switch(db(request), body.key, body.definition, body.ties)


@router.get('/companion/ties')
def companion_ties(request: Request):
    """How close the current companion and the other companions they know feel to each other, both ways
    (companion/memory/pairs.py). Read-only: only what happens between them moves it."""
    database = db(request)
    with database.connect() as connection:
        return {'ties': pairs.ties(connection, characters.require_current(connection), database.clock.now())}


@router.post('/companion/town')
def companion_town(request: Request, body: TownSeed):
    """New townsfolk of the companion's own, or the city's shared ones again."""
    return cast.reseed_town(db(request), body.fresh)


@router.post('/companion/cast/focus')
def cast_focus(request: Request, body: CastFocus):
    """Switch back to a companion who stepped back."""
    return cast.focus_on(db(request), body.companion_id)


@router.get('/chats')
def list_chats(request: Request):
    """Every chat with its latest message and unread count, the most recent first."""
    return chats.listed(db(request))


@router.post('/chats/read')
def read_chat(request: Request, body: ChatRead):
    """The user has seen a chat up to a message (its latest when no seq is given)."""
    return chats.read(db(request), body.thread_id, body.seq)


@router.get('/prompts')
def read_prompts(request: Request):
    return prompt_library.views(db(request))


@router.put('/prompts/{name}')
def save_prompt(request: Request, name: str, body: PromptUpdate):
    return prompt_library.save(db(request), name, body.text)


@router.delete('/prompts/{name}')
def reset_prompt(request: Request, name: str):
    return prompt_library.reset(db(request), name)


@router.post('/companion/versions')
def revise_companion(request: Request, body: CharacterRevision):
    return characters.revise(db(request), body)


@router.get('/companion/versions')
def companion_versions(request: Request):
    return characters.versions(db(request))


@router.get('/companion/start-over')
def start_over_preview(request: Request):
    """What starting over or deleting would remove, for the confirmation."""
    return start_over.preview(db(request))


@router.post('/companion/start-over')
def start_companion_over(request: Request, body: StartOverConfirm):
    """Same character, fresh history, after a verified backup."""
    return stopped(request, start_over.start_over(db(request), body.name))


@router.post('/companion/delete')
def delete_companion(request: Request, body: StartOverConfirm):
    """The companion and everything about them, after a verified backup."""
    return stopped(request, start_over.delete(db(request), body.name))


def stopped(request: Request, result: dict) -> dict:
    for attempt_id in result['stopped_reply_ids']:
        request.app.state.conversation.stop(attempt_id)
    return result


@router.get('/timelines')
def list_timelines(request: Request):
    return timelines.listing(db(request))


@router.post('/timelines')
def fork_timeline(request: Request, body: TimelineFork):
    """Branch from here, or Edit from here on your own message: a new inactive timeline; the live one is
    untouched until the user switches."""
    return timelines.fork(db(request), body)


@router.patch('/timelines/{timeline_id}')
def update_timeline(request: Request, timeline_id: str, body: TimelineUpdate):
    return timelines.update(db(request), timeline_id, body)


@router.post('/timelines/{timeline_id}/activate')
def activate_timeline(request: Request, timeline_id: str):
    result = timelines.activate(db(request), timeline_id)
    for attempt_id in result['stopped_reply_ids']:
        request.app.state.conversation.stop(attempt_id)
    return result


@router.get('/conversation')
def read_conversation(request: Request, before_seq: int | None = None, limit: int = 100):
    return conversation.history(db(request), before_seq, min(max(limit, 1), 500))


@router.get('/conversation/recap')
def read_recap(request: Request):
    """While you were away: a catch-up after a few days without a message, or null (companion/recap.py)."""
    return recap.read(db(request))


@router.post('/conversation/recap/read')
def dismiss_recap(request: Request, body: RecapRead):
    return recap.dismiss(db(request), body.since)


@router.get('/conversation/search')
def search_conversation(request: Request, q: str = ''):
    return conversation.search(db(request), q)


@router.post('/conversation/messages')
async def send_message(request: Request, body: MessageCreate, wait: bool = True):
    return await request.app.state.conversation.send(body, wait)


@router.post('/pictures', status_code=201)
async def upload_picture(request: Request):
    """The body is the picture, already shrunk by the interface (companion/pictures.py)."""
    data = await request.body()
    return pictures.save(db(request), data)


@router.get('/pictures/{picture_id}')
def read_picture(request: Request, picture_id: str):
    path, media_type = pictures.path_of(db(request), picture_id)
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'private, max-age=31536000, immutable'})


@router.post('/conversation/messages/{message_id}/alternatives')
async def alternative(request: Request, message_id: str, wait: bool = True):
    return await request.app.state.conversation.alternative(message_id, wait)


@router.get('/conversation/replies/{attempt_id}/events')
async def reply_events(request: Request, attempt_id: str):
    """Server-sent events for one reply. Closing the stream does not stop the reply."""
    conversation = request.app.state.conversation
    conversation.reply(attempt_id)

    async def body():
        async for name, data in conversation.events(attempt_id):
            yield f'event: {name}\ndata: {json.dumps(data)}\n\n'

    return StreamingResponse(body(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@router.post('/conversation/replies/{attempt_id}/stop')
def stop_reply(request: Request, attempt_id: str):
    return {'stopped': request.app.state.conversation.stop(attempt_id)}


@router.post('/conversation/messages/{message_id}/decline-memory')
def decline_memory(request: Request, message_id: str):
    return formation.forget_message(db(request), message_id)


@router.post('/conversation/messages/{message_id}/remember')
def remember_message(request: Request, message_id: str):
    return formation.remember_message(db(request), message_id)


@router.get('/memory/status')
def memory_status(request: Request):
    return formation.status(db(request))


@router.post('/memory/run')
def run_memory(request: Request):
    """Process queued extraction now (the app also does this after each reply)."""
    return formation.run_pending(db(request))


@router.get('/memory/suggestions')
def memory_suggestions(request: Request):
    return formation.suggestions(db(request))


@router.post('/memory/suggestions/{candidate_id}/accept')
def accept_suggestion(request: Request, candidate_id: str):
    return formation.accept(db(request), candidate_id)


@router.post('/memory/suggestions/{candidate_id}/decline')
def decline_suggestion(request: Request, candidate_id: str):
    return formation.decline(db(request), candidate_id)


@router.post('/memory/consolidate')
def consolidate_memory(request: Request):
    """Run bounded consolidation now (the app also runs it in the background while automatic memory is on)."""
    return consolidation.run(db(request))


@router.get('/memory/proposals')
def memory_proposals(request: Request):
    return consolidation.proposals(db(request))


@router.post('/memory/proposals/{proposal_id}/accept')
def accept_proposal(request: Request, proposal_id: str):
    return consolidation.resolve(db(request), proposal_id, True)


@router.post('/memory/proposals/{proposal_id}/decline')
def decline_proposal(request: Request, proposal_id: str):
    return consolidation.resolve(db(request), proposal_id, False)


@router.get('/memory/activity')
def memory_activity(request: Request, limit: int = 100):
    return formation.activity(db(request), min(max(limit, 1), 500))


@router.get('/context/preview')
def context_preview(request: Request):
    return conversation.context_preview(db(request))


@router.get('/self-facts')
def list_self_facts(request: Request):
    """What the companion has said about themselves, with conflicts waiting for a decision."""
    return self_facts.listing(request.app.state.database)


@router.post('/self-facts/{fact_id}/keep')
def keep_self_fact(request: Request, fact_id: str):
    return self_facts.decide(request.app.state.database, fact_id, True)


@router.post('/self-facts/{fact_id}/remove')
def remove_self_fact(request: Request, fact_id: str):
    return self_facts.decide(request.app.state.database, fact_id, False)


@router.get('/memories')
def list_memories(request: Request, history: bool = False):
    return records.listing(db(request), history)


@router.post('/memories')
def remember(request: Request, body: MemoryCreate):
    return records.remember(db(request), body)


@router.post('/memories/{memory_id}/correct')
def correct_memory(request: Request, memory_id: str, body: MemoryCorrection):
    return records.correct(db(request), memory_id, body)


@router.post('/memories/{memory_id}/confirm')
def confirm_memory(request: Request, memory_id: str):
    return records.confirm(db(request), memory_id)


@router.post('/memories/{memory_id}/exclude')
def exclude_memory(request: Request, memory_id: str):
    return records.set_flag(db(request), memory_id, status='excluded')


@router.post('/memories/{memory_id}/include')
def include_memory(request: Request, memory_id: str):
    return records.set_flag(db(request), memory_id, status='active')


@router.post('/memories/{memory_id}/pin')
def pin_memory(request: Request, memory_id: str, pinned: bool = True):
    return records.set_flag(db(request), memory_id, pinned=pinned)


@router.get('/memories/{memory_id}/delete-preview')
def delete_preview(request: Request, memory_id: str):
    return records.delete_preview(db(request), memory_id)


@router.post('/memories/{memory_id}/delete')
def delete_memory(request: Request, memory_id: str, body: MemoryDelete):
    return records.delete(db(request), memory_id, body.delete_sources)


@router.get('/events')
def list_events(request: Request, history: bool = False):
    return events.listing(db(request), history)


@router.post('/events')
def propose_event(request: Request, body: EventProposal):
    return events.propose(db(request), body)


@router.post('/events/{event_id}/commit')
def commit_event(request: Request, event_id: str):
    return events.commit(db(request), event_id)


@router.post('/events/{event_id}/reject')
def reject_event(request: Request, event_id: str):
    return events.reject(db(request), event_id)


@router.post('/events/{event_id}/correct')
def correct_event(request: Request, event_id: str, body: EventCorrection):
    return events.correct(db(request), event_id, body)


@router.post('/backups')
def create_backup(request: Request, include_datasets: bool = False):
    """Training reference pictures are included only with ?include_datasets=true (PRD persistence)."""
    return backup.create(db(request), db(request).path.parent / 'backups', include_datasets)


@router.get('/backups')
def list_backups(request: Request):
    return restore.listing(db(request).path.parent) | auto_backup.status(db(request))


@router.post('/backups/{name}/restore')
def schedule_restore(request: Request, name: str):
    """The restore runs the next time the Companion starts; the running app keeps its workspace."""
    return restore.schedule(db(request).path.parent, name, db(request).now())


@router.delete('/backups/restore')
def cancel_restore(request: Request):
    return restore.cancel(db(request).path.parent)


# Under /api/backups so a phone never sees or changes it (companion/phone/access.py PC_ONLY).
@router.get('/backups/data-folder')
def read_data_folder(request: Request):
    return data_folder.status(db(request).root)


@router.post('/backups/data-folder/move')
def schedule_data_move(request: Request):
    """The move runs the next time the Companion starts; the open workspace cannot be copied safely."""
    return data_folder.schedule(db(request).root, db(request).now())


@router.delete('/backups/data-folder/move')
def cancel_data_move(request: Request):
    return data_folder.cancel(db(request).root)


@router.post('/backups/data-folder/open')
def open_data_folder(request: Request):
    return data_folder.open_folder(db(request).root)


@router.get('/notifications/settings')
def read_notification_settings(request: Request):
    return notifications.read(db(request))


@router.put('/notifications/settings')
def update_notification_settings(request: Request, body: NotificationSettingsUpdate):
    return notifications.update(db(request), body)


@router.post('/notifications/next')
def next_notification(request: Request, background: BackgroundTasks, body: NotificationCheck | None = None):
    """The open interface asks for what to show; the answer respects quiet hours and the cap. Whatever it
    shows also goes to phones subscribed to notifications (companion/phone/push.py)."""
    focused = (body or NotificationCheck()).focused
    pusher = request.app.state.push
    if request.state.device is None:
        pusher.pc_checked(focused)
    result = notifications.deliver(db(request), focused)
    if result['notification']:
        background.add_task(pusher.send, result['notification'])
    return result
