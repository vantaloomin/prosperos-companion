"""Krea 2 on a card too small for its built-in fp8 file: the app picks a file that fits (Vanta, 2026-10-28), and a
.gguf file runs through the ComfyUI-GGUF loader."""
import httpx
import pytest
from fastapi.testclient import TestClient

from companion import hardware
from companion.database import decode
from companion.hardware import Hardware
from companion.identity import CLIENT_HEADER
from companion.images import backends
from companion.images.adapters.comfyui import ComfyAdapter, built_in, model_file
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_images import ComfyStandIn, FakeAdapter, local_comfy, ok


def card(name, memory):
    return {'index': 0, 'name': name, 'memory_gb': memory, 'usable_gb': memory, 'used_gb': None, 'shared': False}


def computer(*gpus):
    return {'system': 'Windows', 'cores': 16, 'memory_gb': 64.0, 'gpus': list(gpus), 'gpu_note': None}


RTX_5070 = card('NVIDIA GeForce RTX 5070', 11.9)


def test_sizes_come_from_krea_2s_real_files():
    # Comfy-Org/Krea-2: fp8 13.1 GB, NVFP4 7.7 GB, bf16 26.3 GB, plus working room.
    assert 13 < hardware.image_size_gb('krea2_turbo_fp8_scaled.safetensors') < 15
    assert 8 < hardware.image_size_gb('krea2_turbo_nvfp4.safetensors') < 10
    assert hardware.image_size_gb('krea2_turbo_bf16.safetensors') > 25
    assert hardware.image_size_gb('krea2_turbo-Q4_K_M.gguf') < hardware.image_size_gb('krea2_turbo-Q6_K.gguf')


@pytest.mark.parametrize(('gpu', 'pick'), [
    (RTX_5070, 'krea2_turbo_nvfp4.safetensors'),
    # NVFP4 only runs natively on RTX 50-series cards, so others get a GGUF that fits.
    (card('NVIDIA GeForce RTX 3080', 10.0), 'krea2_turbo-Q4_K_M.gguf'),
    (card('NVIDIA GeForce RTX 4060', 8.0), 'krea2_turbo-Q3_K_M.gguf'),
    # The built-in fp8 file fits, so it stays; nothing fits, so it stays and the warning says so.
    (card('NVIDIA GeForce RTX 4070 Ti SUPER', 16.0), None),
    (card('NVIDIA GeForce GTX 1650', 4.0), None),
    (None, None)])
def test_picks_the_krea_2_file_the_card_holds(gpu, pick):
    assert hardware.krea_pick(gpu) == pick


def test_prefers_a_fitting_file_comfyui_already_has():
    have = ['Krea 2\\Krea-2-Turbo-Q4_K_M.gguf', 'krea2_turbo_fp8_scaled.safetensors', 'krea2_raw_fp8_scaled.safetensors',
            'Krea2 Edit Q4_K_M.gguf']
    assert hardware.krea_pick(card('NVIDIA GeForce RTX 3080', 10.0), have) == 'Krea 2\\Krea-2-Turbo-Q4_K_M.gguf'
    assert hardware.krea_pick(RTX_5070, [*have, 'Muse Krea2 NVFP4.safetensors']) == 'Muse Krea2 NVFP4.safetensors'
    # Nothing it has fits: the one to download.
    assert hardware.krea_pick(RTX_5070, ['krea2_turbo_bf16.safetensors']) == 'krea2_turbo_nvfp4.safetensors'


def test_a_too_big_file_names_the_one_that_fits():
    image = {'label': 'Local ComfyUI', 'base_url': 'http://127.0.0.1:8188', 'unet': 'krea2_turbo_fp8_scaled.safetensors',
             'size_gb': hardware.image_size_gb('krea2_turbo_fp8_scaled.safetensors'), 'krea2': True}
    text = hardware.check(computer(RTX_5070), [], [image], {})[0]['text']
    assert 'krea2_turbo_nvfp4.safetensors (about 9.1 GB) fits' in text and 'NVFP4)' not in text
    lines = hardware.can_run(computer(RTX_5070))
    assert 'krea2_turbo_nvfp4.safetensors' in lines[1]


def test_the_pick_is_used_until_the_user_chooses_a_model():
    config = {'base_url': 'http://127.0.0.1:8188', 'unet_fit': 'krea2_turbo_nvfp4.safetensors'}
    assert model_file(config) == 'krea2_turbo_nvfp4.safetensors'
    assert all(node['inputs']['unet_name'] == 'krea2_turbo_nvfp4.safetensors'
               for node in built_in(config, reference=True).values() if node['class_type'] == 'UNETLoader')
    assert model_file({**config, 'unet_name': 'mine.safetensors'}) == 'mine.safetensors'


def test_a_gguf_model_loads_through_the_gguf_loader():
    config = {'base_url': 'http://127.0.0.1:8188', 'unet_name': 'Krea 2\\krea2_turbo-Q5_K_M.gguf'}
    for workflow in (built_in(config), built_in(config, reference=True)):
        loaders = [node for node in workflow.values() if 'unet_name' in node['inputs']]
        assert loaders and all(node == {'class_type': 'UnetLoaderGGUF', 'inputs': {'unet_name': 'Krea 2\\krea2_turbo-Q5_K_M.gguf'}}
                               for node in loaders)
    # A reference model of its own keeps the plain loader when it is a .safetensors file.
    mixed = built_in({**config, 'ref_unet_name': 'krea2_edit.safetensors'}, reference=True)
    assert {node['class_type'] for node in mixed.values() if 'unet_name' in node['inputs']} == {'UNETLoader'}


GGUF_FILES = {'UnetLoaderGGUF': {'input': {'required': {'unet_name': [['Krea 2\\krea2_turbo-Q4_K_S.gguf'], {}]}}}}


class GgufStandIn(ComfyStandIn):
    """A server with the ComfyUI-GGUF nodes and one Krea 2 GGUF file, and no UnetLoaderGGUF in the check's list."""

    def object_info(self, request: httpx.Request):
        if request.url.path == '/object_info/UnetLoaderGGUF':
            return httpx.Response(200, json=GGUF_FILES)
        return super().object_info(request)


@pytest.fixture
def small_card(tmp_path, clock, provider):
    adapters = {'comfyui': ComfyAdapter(httpx.MockTransport(GgufStandIn())), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}
    app = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(), provider=provider,
                     life_tasks=False, image_adapters=adapters,
                     hardware=Hardware(scanner=lambda: computer(card('NVIDIA GeForce RTX 3080', 10.0)), device=lambda url: None))
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def saved_config(client, backend_id):
    with client.app.state.database.connect() as connection:
        return decode(backends.get(connection, backend_id)['config'])


def test_a_new_krea_2_server_starts_on_a_file_its_card_holds(small_card):
    backend = local_comfy(small_card)
    assert backend['model_fit'] == 'krea2_turbo-Q4_K_M.gguf'
    assert saved_config(small_card, backend['id'])['unet_fit'] == 'krea2_turbo-Q4_K_M.gguf'
    report = ok(small_card.get('/api/hardware'))
    assert report['local_images'][0]['unet'] == 'krea2_turbo-Q4_K_M.gguf' and report['warnings'] == []
    # Once the server lists its files, a fitting one it has wins, and is what the picker shows as the default.
    listed = ok(small_card.get(f"/api/images/backends/{backend['id']}/files"))
    assert 'Krea 2\\krea2_turbo-Q4_K_S.gguf' in listed['options']['unet_name']
    assert listed['defaults']['unet_name'] == 'Krea 2\\krea2_turbo-Q4_K_S.gguf'
    # Asking the card again keeps that pick.
    ok(small_card.get('/api/hardware?fresh=true'))
    assert saved_config(small_card, backend['id'])['unet_fit'] == 'Krea 2\\krea2_turbo-Q4_K_S.gguf'
    check = ok(small_card.post(f"/api/images/backends/{backend['id']}/check"))
    assert any('Missing node: UnetLoaderGGUF (from the ComfyUI-GGUF nodes' in line for line in check['details'])
    # Another family drops the pick.
    ok(small_card.put(f"/api/images/backends/{backend['id']}", json={'family': 'zimage'}))
    assert 'unet_fit' not in saved_config(small_card, backend['id'])
