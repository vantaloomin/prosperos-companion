"""Model families for a ComfyUI backend (Vanta, 2026-10-13): Krea 2, Qwen Image 2.1, Anima and Booru
models, each with a built-in workflow of its own."""
import asyncio
import json

import httpx
import pytest

from companion.images import backends
from companion.images.adapters.base import AdapterError
from companion.images.adapters.comfyui import FAMILIES, ComfyAdapter, built_in, default_files, family_first
from companion.images.runner import character_lora
from tests.test_images import ComfyStandIn, comfy_client, local_comfy, ok, request_for  # noqa: F401
from tests.test_portraits import ComfyWithUpload

LOCAL = {'base_url': 'http://127.0.0.1:8188'}


def by_class(graph) -> dict:
    return {node['class_type']: node['inputs'] for node in graph.values()}


@pytest.mark.parametrize('family', list(FAMILIES))
def test_every_family_has_a_built_in_workflow_with_the_request_markers(family):
    text = json.dumps(built_in({'family': family}))
    assert all(marker in text for marker in ('{{prompt}}', '{{negative}}', '{{seed}}', '{{width}}', '{{height}}'))
    reference = built_in({'family': family}, reference=True)
    assert (reference is not None) == (FAMILIES[family].reference is not None)
    if reference:
        assert '{{reference_image}}' in json.dumps(reference)


def test_an_unknown_or_missing_family_is_krea_2():
    assert built_in({}) == built_in({'family': 'krea2'}) == built_in({'family': 'gone'})


def test_qwen_image_2_1_runs_its_turbo_file_and_follows_a_reference_with_comfyuis_own_node():
    server = ComfyWithUpload()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    config = {**LOCAL, 'family': 'qwen21'}
    result = asyncio.run(adapter.generate(request_for('comfyui', config)))
    nodes = by_class(server.prompts[0])
    assert nodes['TextEncodeQwenImage21']['prompt'] == 'A café' and nodes['CLIPLoader']['type'] == 'qwen_image'
    assert nodes['KSampler']['negative'] == ['4', 1] and nodes['KSampler']['steps'] == 8
    assert result.workflow == 'qwen-image-2.1-turbo' and result.model == 'qwen_image_2.1_turbo_int8_convrot.safetensors'
    followed = asyncio.run(adapter.generate(request_for('comfyui', config, reference=b'\x89PNG')))
    nodes = by_class(server.prompts[1])
    assert nodes['TextEncodeQwenImage21']['images.image_1'] == ['5', 0]
    assert nodes['LoadImage']['image'] == 'prospero-job1.png' and followed.workflow == 'qwen-image-2.1-turbo reference'


def test_anima_and_booru_models_draw_with_their_quality_tags_and_have_no_built_in_reference():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'anima'})))
    texts = [node['inputs']['text'] for node in server.prompts[0].values() if 'text' in node['inputs']]
    assert texts[0] == 'masterpiece, best quality, A café' and texts[1].startswith('text, worst quality')
    asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'booru', 'ckpt_name': 'pony.safetensors'})))
    nodes = by_class(server.prompts[1])
    assert nodes['CheckpointLoaderSimple']['ckpt_name'] == 'pony.safetensors'
    assert nodes['CLIPSetLastLayer']['stop_at_clip_layer'] == -2 and nodes['VAEDecode']['vae'] == ['1', 2]
    with pytest.raises(AdapterError) as refused:
        asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'anima'}, reference=b'\x89PNG')))
    assert 'Anima' in refused.value.message and len(server.prompts) == 2


def test_style_loras_attach_after_a_booru_checkpoint_and_leave_its_clip_and_vae_alone():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    config = {**LOCAL, 'family': 'booru', 'style_loras': [{'name': 'ink.safetensors', 'strength': 0.6, 'trigger': ''}]}
    asyncio.run(adapter.generate(request_for('comfyui', config)))
    graph = server.prompts[0]
    assert graph['prospero-style-lora-1']['inputs']['model'] == ['1', 0]
    assert graph['7']['inputs']['model'] == ['prospero-style-lora-1', 0] and graph['2']['inputs']['clip'] == ['1', 1]


def test_only_krea_2_applies_the_adopted_character_lora():
    lora = {'lora': {'name': 'x', 'comfy_name': 'prospero-x.safetensors', 'strength': 0.8}}
    krea = {'kind': 'comfyui', 'config': json.dumps(LOCAL)}
    qwen = {'kind': 'comfyui', 'config': json.dumps({**LOCAL, 'family': 'qwen21'})}
    assert character_lora(krea, lora) == lora['lora'] and character_lora(qwen, lora) is None


def test_matching_files_sort_first_for_the_family():
    options = ['krea2_turbo.safetensors', 'anima-turbo-v1.1.safetensors', 'Illustrious-XL-v2.0.safetensors']
    assert family_first('unet_name', options, 'anima') == (
        ['anima-turbo-v1.1.safetensors', 'krea2_turbo.safetensors', 'Illustrious-XL-v2.0.safetensors'],
        ['anima-turbo-v1.1.safetensors'])
    assert family_first('ckpt_name', options, 'booru')[1] == ['Illustrious-XL-v2.0.safetensors']
    assert family_first('clip_name', ['qwen3vl_8b_int8_convrot.safetensors', 'qwen3vl_4b.safetensors'], 'qwen21')[1] \
        == ['qwen3vl_8b_int8_convrot.safetensors']


def test_choosing_a_family_starts_it_on_its_own_files_and_sampling(comfy_client):  # noqa: F811
    backend = local_comfy(comfy_client)
    assert backend['family'] == 'krea2' and backend['takes_reference'] is True
    tuned = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'unet_name': 'mine.safetensors', 'steps': 12}))
    assert tuned['model_files']['unet_name'] == 'mine.safetensors' and tuned['sampler']['steps'] == 12
    anima = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'family': 'anima'}))
    assert anima['family'] == 'anima' and anima['model_files']['unet_name'] == '' and anima['sampler']['steps'] is None
    assert anima['takes_reference'] is False
    workflows = ok(comfy_client.get(f"/api/images/backends/{backend['id']}/workflows"))
    assert 'anima-turbo-v1.1.safetensors' in workflows['built_in'] and workflows['built_in_reference'] == ''
    booru = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'family': 'booru'}))
    assert booru['model_files'] == {'ckpt_name': ''}
    listed = ok(comfy_client.get(f"/api/images/backends/{backend['id']}/files"))
    assert listed['family'] == 'booru' and listed['defaults'] == default_files('booru')
    assert listed['sampler_defaults']['sampler_name'] == 'euler_ancestral' and 'unet_name' not in listed['options']
    back = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'family': 'krea2'}))
    assert back['family'] == 'krea2' and back['takes_reference'] is True
    assert comfy_client.put(f"/api/images/backends/{backend['id']}", json={'family': 'sd15'}).status_code == 422


def test_an_anime_family_starts_its_prompts_as_an_illustration_unless_the_backend_has_a_style():
    anima = {'kind': 'comfyui', 'config': json.dumps({**LOCAL, 'family': 'anima'})}
    assert backends.style_for(anima, 'Candid, natural-light photograph') == 'Anime illustration'
    own = {'kind': 'comfyui', 'config': json.dumps({**LOCAL, 'family': 'anima', 'style': 'Watercolour'})}
    assert backends.style_for(own, 'Candid photo') == 'Watercolour'
    krea = {'kind': 'comfyui', 'config': json.dumps(LOCAL)}
    assert backends.style_for(krea, 'Candid photo') == 'Candid photo'
