"""Model families for a ComfyUI backend (Vanta, 2026-10-13): Krea 2, Qwen Image 2.1, Anima and Booru
models, each with a built-in workflow of its own."""
import asyncio
import json

import httpx
import pytest

from companion.images import backends
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
    assert all(marker in text for marker in ('{{prompt}}', '{{seed}}', '{{width}}', '{{height}}'))
    # The CFG 1 families run with an empty negative, as Vanta's workflows do.
    assert ('{{negative}}' in text) == (family in ('anima', 'booru'))
    assert '{{reference_image}}' in json.dumps(built_in({'family': family}, reference=True))


def test_an_unknown_or_missing_family_is_krea_2():
    assert built_in({}) == built_in({'family': 'krea2'}) == built_in({'family': 'gone'})


def test_qwen_image_2_1_runs_its_full_file_and_follows_a_reference_with_comfyuis_own_node():
    server = ComfyWithUpload()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    config = {**LOCAL, 'family': 'qwen21'}
    result = asyncio.run(adapter.generate(request_for('comfyui', config)))
    nodes = by_class(server.prompts[0])
    assert nodes['CLIPTextEncode']['text'] == 'A café' and nodes['CLIPLoader']['type'] == 'qwen_image'
    assert nodes['KSampler']['negative'] == ['5', 0] and nodes['KSampler']['steps'] == 25
    assert result.workflow == 'qwen-image-2.1' and result.model == 'qwen_image_2.1_int8_convrot.safetensors'
    followed = asyncio.run(adapter.generate(request_for('comfyui', config, reference=b'\x89PNG')))
    nodes = by_class(server.prompts[1])
    assert nodes['TextEncodeQwenImage21']['images.image_1'] == ['5', 0]
    assert nodes['TextEncodeQwenImage21']['prompt'] == 'Use <image1> as the reference for the person. A café'
    assert nodes['LoadImage']['image'] == 'prospero-job1.png' and followed.workflow == 'qwen-image-2.1 reference'


def test_anima_and_booru_models_draw_with_their_quality_tags():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'anima'})))
    texts = [node['inputs']['text'] for node in server.prompts[0].values() if 'text' in node['inputs']]
    # No rating tag, so an NSFW backend's pictures are not steered back to "safe".
    assert texts[0] == 'masterpiece, best quality, score_7, newest, A café' and texts[1].startswith('text, worst quality')
    assert by_class(server.prompts[0])['KSampler']['sampler_name'] == 'er_sde'
    asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'booru', 'ckpt_name': 'pony.safetensors'})))
    nodes = by_class(server.prompts[1])
    assert nodes['CheckpointLoaderSimple']['ckpt_name'] == 'pony.safetensors'
    assert nodes['CLIPSetLastLayer']['stop_at_clip_layer'] == -2 and nodes['VAEDecode']['vae'] == ['1', 2]


def test_anima_booru_and_z_image_follow_a_reference_with_vantas_workflows():
    server = ComfyWithUpload()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    for family in ('anima', 'booru', 'zimage'):
        asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': family}, reference=b'\x89PNG')))
    anima, booru, zimage = (by_class(graph) for graph in server.prompts)
    assert anima['LoraLoaderModelOnly']['lora_name'] == 'AnimeEditV2.safetensors'
    assert anima['ApplyCosmosReferenceLatent']['ref_latents.ref_latent_1'] == ['6', 0]
    assert booru['IPAdapterAdvanced']['end_at'] == 0.5 and booru['KSampler']['model'] == ['14', 0]
    assert zimage['KSampler']['denoise'] == 0.7 and zimage['KSampler']['latent_image'] == ['6', 0]


def test_krea_2_reference_takes_its_own_model_and_an_edit_model_needs_no_lora():
    shared = built_in({'family': 'krea2', 'unet_name': 'mine.safetensors'}, reference=True)
    assert by_class(shared)['UNETLoader']['unet_name'] == 'mine.safetensors' and 'LoraLoaderModelOnly' in by_class(shared)
    edit = built_in({'family': 'krea2', 'unet_name': 'mine.safetensors',
                     'ref_unet_name': 'Krea 2\\krea2_turbo_EDIT.safetensors'}, reference=True)
    nodes = by_class(edit)
    assert nodes['UNETLoader']['unet_name'] == 'Krea 2\\krea2_turbo_EDIT.safetensors'
    assert 'LoraLoaderModelOnly' not in nodes and nodes['Krea2EditModelPatch']['model'] == ['1', 0]
    assert nodes['Krea2EditModelPatch']['ref_boost'] == 2.5
    text = built_in({'family': 'krea2', 'unet_name': 'mine.safetensors', 'ref_unet_name': 'x_edit.safetensors'})
    assert by_class(text)['UNETLoader']['unet_name'] == 'mine.safetensors'
    assert default_files('krea2')['ref_unet_name'] == ''


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
    options = ['krea2_turbo.safetensors', 'anima-base-v1.0.safetensors', 'Illustrious-XL-v2.0.safetensors']
    assert family_first('unet_name', options, 'anima') == (
        ['anima-base-v1.0.safetensors', 'krea2_turbo.safetensors', 'Illustrious-XL-v2.0.safetensors'],
        ['anima-base-v1.0.safetensors'])
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
    assert anima['takes_reference'] is True
    workflows = ok(comfy_client.get(f"/api/images/backends/{backend['id']}/workflows"))
    assert 'anima-base-v1.0.safetensors' in workflows['built_in'] and 'AnimeEditV2' in workflows['built_in_reference']
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


def test_z_image_turbo_runs_comfyuis_own_template_shape():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    result = asyncio.run(adapter.generate(request_for('comfyui', {**LOCAL, 'family': 'zimage'})))
    nodes = by_class(server.prompts[0])
    assert nodes['CLIPLoader'] == {'clip_name': 'qwen_3_4b.safetensors', 'type': 'lumina2'}
    assert nodes['ModelSamplingAuraFlow']['shift'] == 3 and nodes['KSampler']['model'] == ['10', 0]
    assert nodes['KSampler']['steps'] == 9
    assert nodes['KSampler']['sampler_name'] == 'res_multistep' and nodes['ConditioningZeroOut']['conditioning'] == ['4', 0]
    assert result.workflow == 'z-image-turbo' and result.model == 'z_image_turbo_bf16.safetensors'
    assert family_first('vae_name', ['flux\\ae.safetensors', 'qwen_image_vae.safetensors'], 'zimage')[1] == ['flux\\ae.safetensors']
