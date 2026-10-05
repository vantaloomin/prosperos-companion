"""Local HTTP API for the Companion backbone."""
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from companion import (
    backup,
    characters,
    conversation,
    drafting,
    events,
    notifications,
    restore,
    text_models,
    timelines,
    workspace,
)
from companion.identity import APP_ID, VERSION
from companion.memory import consolidation, formation, records
from companion.models import (
    CharacterDefinition,
    CharacterDraftRequest,
    CharacterRevision,
    ConnectionUpdate,
    EventCorrection,
    EventProposal,
    FieldDraftRequest,
    MemoryCorrection,
    MemoryCreate,
    MemoryDelete,
    MessageCreate,
    NotificationCheck,
    NotificationSettingsUpdate,
    PromptUpdate,
    SettingsUpdate,
    TimelineFork,
    TimelineUpdate,
)

router = APIRouter(prefix='/api')


def db(request: Request):
    return request.app.state.database


@router.get('/health')
def health():
    return {'app_id': APP_ID, 'version': VERSION}


@router.get('/settings')
def read_settings(request: Request):
    return workspace.read(db(request))


@router.put('/settings')
def update_settings(request: Request, body: SettingsUpdate):
    return workspace.update(db(request), body)


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


@router.get('/prompts')
def read_prompts(request: Request):
    return drafting.prompts(db(request))


@router.put('/prompts/{name}')
def save_prompt(request: Request, name: str, body: PromptUpdate):
    return drafting.save_prompt(db(request), name, body.text)


@router.delete('/prompts/{name}')
def reset_prompt(request: Request, name: str):
    return drafting.reset_prompt(db(request), name)


@router.post('/companion/versions')
def revise_companion(request: Request, body: CharacterRevision):
    return characters.revise(db(request), body)


@router.get('/companion/versions')
def companion_versions(request: Request):
    return characters.versions(db(request))


@router.get('/timelines')
def list_timelines(request: Request):
    return timelines.listing(db(request))


@router.post('/timelines')
def fork_timeline(request: Request, body: TimelineFork):
    """Edit from here: a new inactive timeline; the live one is untouched until the user switches."""
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


@router.get('/conversation/search')
def search_conversation(request: Request, q: str = ''):
    return conversation.search(db(request), q)


@router.post('/conversation/messages')
async def send_message(request: Request, body: MessageCreate, wait: bool = True):
    return await request.app.state.conversation.send(body, wait)


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
    return restore.listing(db(request).path.parent)


@router.post('/backups/{name}/restore')
def schedule_restore(request: Request, name: str):
    """The restore runs the next time the Companion starts; the running app keeps its workspace."""
    return restore.schedule(db(request).path.parent, name, db(request).now())


@router.delete('/backups/restore')
def cancel_restore(request: Request):
    return restore.cancel(db(request).path.parent)


@router.get('/notifications/settings')
def read_notification_settings(request: Request):
    return notifications.read(db(request))


@router.put('/notifications/settings')
def update_notification_settings(request: Request, body: NotificationSettingsUpdate):
    return notifications.update(db(request), body)


@router.post('/notifications/next')
def next_notification(request: Request, body: NotificationCheck | None = None):
    """The open interface asks for what to show; the answer respects quiet hours and the cap."""
    return notifications.deliver(db(request), (body or NotificationCheck()).focused)
