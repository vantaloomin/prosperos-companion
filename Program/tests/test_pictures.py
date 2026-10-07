"""Pictures the user sends: described once by the Seeing pictures model, then part of the conversation."""
import struct
import zlib
from datetime import timedelta

from conftest import send

from companion import pictures
from companion.providers.chat import Chunk
from companion.providers.requests import anthropic_request, chat_request, google_request, openai_request

DESCRIPTION = 'A brown dog asleep on a red sofa in afternoon light.'
CONFIG = {'model': 'm', 'max_output_tokens': 300, 'provider': 'local'}
PARTS = [{'type': 'text', 'text': 'Look'}, {'type': 'image', 'media_type': 'image/png', 'data': 'QUJD'}]


def png(width=4, height=3) -> bytes:
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    rows = b''.join(b'\x00' + b'\x80' * width * 3 for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


def sees(provider, description=DESCRIPTION):
    def respond(system, messages):
        if system == pictures.DESCRIBE:
            return [Chunk(description), Chunk('', 'stop')]
        return [Chunk('What a sleepy dog.'), Chunk('', 'stop')]
    provider.respond = respond


def upload(client, data=None):
    response = client.post('/api/pictures', content=data or png(),
                           headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 201, response.text
    return response.json()


def send_picture(client, text='Look at him', client_id='picture-0001'):
    picture = upload(client)
    response = client.post('/api/conversation/messages',
                           json={'text': text, 'client_id': client_id, 'picture_ids': [picture['id']]})
    assert response.status_code == 200, response.text
    return picture, response.json()


def reply_request(provider):
    return next(request for request in provider.requests if request['system'] != pictures.DESCRIBE)


def test_a_picture_is_described_once_and_the_reply_reads_the_description(client, connected, provider):
    sees(provider)
    picture, result = send_picture(client)
    describe = provider.requests[0]
    assert describe['system'] == pictures.DESCRIBE
    [part_text, part_image] = describe['messages'][0]['content']
    assert 'Look at him' in part_text['text'] and part_image['media_type'] == 'image/png'
    assert f'[Photo: {DESCRIPTION}]' in reply_request(provider)['messages'][-1]['content']
    assert result['message']['pictures'] == [{'id': picture['id'], 'width': 4, 'height': 3, 'status': 'seen',
                                              'reason': None}]
    alternative = client.post(f"/api/conversation/messages/{result['message']['id']}/alternatives")
    assert alternative.status_code == 200
    assert sum(request['system'] == pictures.DESCRIBE for request in provider.requests) == 1
    assert client.get(f"/api/pictures/{picture['id']}").content == png()


def test_a_picture_alone_can_be_sent(client, connected, provider):
    sees(provider)
    _picture, result = send_picture(client, text='')
    assert result['message']['text'] == ''
    assert reply_request(provider)['messages'][-1]['content'] == f'[Photo: {DESCRIPTION}]'
    empty = client.post('/api/conversation/messages', json={'text': ' ', 'client_id': 'picture-0002'})
    assert empty.status_code == 422


def test_a_model_that_cannot_see_leaves_the_picture_unseen_with_a_reason(client, connected, provider):
    profile = client.post('/api/models/profiles', json={'name': 'Kobold', 'config': {
        'provider': 'kobold', 'model': 'kobold', 'base_url': 'http://127.0.0.1:5001/api/v1'}}).json()
    assert client.put('/api/models/routes', json={'job': 'vision', 'profile_id': profile['id']}).status_code == 200
    _picture, result = send_picture(client)
    [shown] = result['message']['pictures']
    assert shown['status'] == 'unseen' and 'cannot look at pictures' in shown['reason']
    system = provider.requests[-1]['system']
    assert 'photo that would not open for you' in system
    assert pictures.UNSEEN in provider.requests[-1]['messages'][-1]['content']


def test_other_files_are_refused(client, connected):
    response = client.post('/api/pictures', content=b'GIF89a not allowed',
                           headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 415


def test_deleting_the_message_deletes_the_picture_and_its_description(client, app, connected, provider):
    sees(provider)
    picture, result = send_picture(client)
    memory = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Dog', 'value': 'Brown',
                                                'source_message_ids': [result['message']['id']]}).json()
    client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': True})
    assert client.get(f"/api/pictures/{picture['id']}").status_code == 404
    assert not list((app.state.database.path.parent / 'pictures').iterdir())


def test_a_forked_timeline_keeps_the_picture(client, app, connected, provider, clock):
    sees(provider)
    _picture, result = send_picture(client)
    clock.advance(timedelta(minutes=5))
    later = send(client, 'Anyway', 'picture-0003')['message']
    created = client.post('/api/timelines', json={'message_id': later['id'], 'text': 'Actually, never mind'}).json()
    client.post(f"/api/timelines/{created['id']}/activate")
    copy = client.get('/api/conversation').json()['messages'][0]
    assert copy['id'] != result['message']['id'] and copy['pictures'][0]['status'] == 'seen'
    assert client.get(f"/api/pictures/{copy['pictures'][0]['id']}").status_code == 200


def test_starting_over_removes_pictures(client, app, connected, provider, companion):
    sees(provider)
    send_picture(client)
    response = client.post('/api/companion/start-over', json={'name': 'Mira'})
    assert response.status_code == 200, response.text
    assert not list((app.state.database.path.parent / 'pictures').iterdir())


def test_each_api_gets_pictures_in_its_own_form():
    messages = [{'role': 'user', 'content': PARTS}]
    assert openai_request(CONFIG, 's', messages)[1]['input'][0]['content'][1] == {
        'type': 'input_image', 'image_url': 'data:image/png;base64,QUJD'}
    assert chat_request(CONFIG, 's', messages)[1]['messages'][1]['content'][1] == {
        'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,QUJD'}}
    assert anthropic_request(CONFIG, 's', messages)[1]['messages'][0]['content'][1]['source'] == {
        'type': 'base64', 'media_type': 'image/png', 'data': 'QUJD'}
    assert google_request(CONFIG, 's', messages)[1]['contents'][0]['parts'][1] == {
        'inline_data': {'mime_type': 'image/png', 'data': 'QUJD'}}
