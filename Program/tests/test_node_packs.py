"""One-press install of a listed ComfyUI node pack (images/node_packs.py), against stand-ins only."""
import asyncio
import hashlib

import httpx
import pytest

from companion.errors import DomainError
from companion.images import node_packs

PACK = {'label': 'Test Pack', 'folder': 'comfyui-test', 'source': 'https://example.test/pin/',
        'nodes': ('TestNode',), 'files': {'__init__.py': hashlib.sha256(b'NODES = 1\n').hexdigest(),
                                          'LICENSE': hashlib.sha256(b'Apache\n').hexdigest()}}
FILES = {'/pin/__init__.py': b'NODES = 1\n', '/pin/LICENSE': b'Apache\n'}


@pytest.fixture
def pack(monkeypatch):
    monkeypatch.setitem(node_packs.PACKS, 'test', PACK)
    return PACK


def serve(files):
    return httpx.MockTransport(lambda request: httpx.Response(200, content=files[request.url.path])
                               if request.url.path in files else httpx.Response(404))


def test_installs_a_pinned_pack_as_a_new_folder(pack, tmp_path):
    target = asyncio.run(node_packs.install('test', {'custom_nodes': [str(tmp_path)]}, serve(FILES)))
    assert target == tmp_path / 'comfyui-test'
    assert (target / '__init__.py').read_bytes() == b'NODES = 1\n' and (target / 'LICENSE').exists()
    assert [path.name for path in tmp_path.iterdir()] == ['comfyui-test']


def test_a_changed_file_installs_nothing(pack, tmp_path):
    with pytest.raises(DomainError) as error:
        asyncio.run(node_packs.install('test', {'custom_nodes': [str(tmp_path)]},
                                       serve({**FILES, '/pin/LICENSE': b'something else\n'})))
    assert "didn't match" in error.value.message and list(tmp_path.iterdir()) == []


def test_an_existing_folder_is_never_replaced(pack, tmp_path):
    (tmp_path / 'comfyui-test').mkdir()
    (tmp_path / 'comfyui-test' / 'mine.py').write_text('kept')
    with pytest.raises(DomainError) as error:
        asyncio.run(node_packs.install('test', {'custom_nodes': [str(tmp_path)]}, serve(FILES)))
    assert 'already' in error.value.message
    assert [path.name for path in (tmp_path / 'comfyui-test').iterdir()] == ['mine.py']


def test_needs_a_custom_nodes_folder_on_this_computer(pack, tmp_path):
    for folders in ({}, {'custom_nodes': [str(tmp_path / 'not-here')]}, []):
        with pytest.raises(DomainError):
            asyncio.run(node_packs.install('test', folders, serve(FILES)))
    with pytest.raises(DomainError):
        asyncio.run(node_packs.install('unknown', {'custom_nodes': [str(tmp_path)]}, serve(FILES)))


def test_the_listed_pack_covers_the_reference_workflows_nodes():
    assert node_packs.providing(['Krea2EditModelPatch', 'KSampler']) == [{'id': 'krea2edit', 'label': 'Krea 2 Identity Edit'}]
    assert node_packs.providing(['KSampler']) == []
    pack = node_packs.PACKS['krea2edit']
    assert '/86f886dac23013d88996e3a2e99093ba44d322fb/' in pack['source'] and '__init__.py' in pack['files']


def test_only_a_comfyui_on_this_computer(client, companion):
    remote = client.post('/api/images/backends', json={'kind': 'comfyui', 'base_url': 'http://192.168.1.20:8188',
                                                        'controlled_machine': True}).json()
    refused = client.post(f"/api/images/backends/{remote['id']}/install-nodes/krea2edit")
    assert refused.status_code == 409 and 'this computer' in refused.json()['detail']
