"""Record model calls (companion/model_calls.py): every model request and response, in full, only when turned on."""
import io
import json
import zipfile
from datetime import timedelta

from conftest import send

from companion import model_calls


def recorded(client) -> list[dict]:
    folder = model_calls.folder(client.app.state.database)
    return [json.loads(line) for path in sorted(folder.glob('*.jsonl')) for line in path.read_text().splitlines()]


def record(client, on=True) -> dict:
    response = client.put('/api/model-calls', json={'recording': on})
    assert response.status_code == 200, response.text
    return response.json()


def test_nothing_is_written_unless_turned_on(client, connected):
    send(client, 'Hi there', 'calls-01')
    assert client.get('/api/model-calls').json()['recording'] is False
    assert not model_calls.folder(client.app.state.database).exists()


def test_a_reply_is_written_down_in_full_without_the_key(client, connected, provider):
    assert record(client)['recording'] is True
    send(client, 'Hi there', 'calls-02')
    [call] = recorded(client)
    assert call['caller'] == 'companion.conversation'
    assert (call['provider'], call['model'], call['base_url']) == ('local', 'local-model', 'http://127.0.0.1:1234/v1')
    assert call['request']['system'] == provider.requests[-1]['system']
    assert call['request']['messages'][-1]['content'].endswith('Hi there')
    assert call['request']['body']['model'] == 'local-model' and call['request']['body']['messages']
    assert call['response']['text'] == 'Hello again.' and 'error' not in call
    files = model_calls.folder(client.app.state.database).glob('*.jsonl')
    assert all('secret-key' not in path.read_text() for path in files)

    record(client, on=False)
    send(client, 'Still there?', 'calls-03')
    assert len(recorded(client)) == 1


def test_a_failed_call_records_the_error(client, connected, provider):
    record(client)
    provider.error = RuntimeError('the model fell over')
    client.post('/api/conversation/messages', json={'text': 'Hi there', 'client_id': 'calls-04'})
    assert 'the model fell over' in recorded(client)[-1]['error']


def test_old_days_are_deleted_and_the_rest_can_be_saved_or_cleared(client, connected, clock):
    record(client)
    folder = model_calls.folder(client.app.state.database)
    folder.mkdir(parents=True)
    old = folder / f'{(clock.now() - timedelta(days=model_calls.KEEP_DAYS)).date().isoformat()}.jsonl'
    old.write_text('{}\n')
    send(client, 'Hi there', 'calls-05')
    assert not old.exists() and client.get('/api/model-calls').json()['files'] == 1

    download = client.get('/api/model-calls/download')
    assert download.headers['content-type'] == 'application/zip'
    names = zipfile.ZipFile(io.BytesIO(download.content)).namelist()
    assert names == [f'{clock.now().date().isoformat()}.jsonl']
    assert client.delete('/api/model-calls').json()['files'] == 0


def test_the_address_loses_its_query_string():
    assert model_calls.address('https://example.test/v1beta?key=abc') == 'https://example.test/v1beta'
