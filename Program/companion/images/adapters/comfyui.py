"""Headless ComfyUI over its HTTP API (PRD F7).

The app only talks to a ComfyUI server the user configured. It never starts, stops or restarts
one, and cancelling removes or interrupts only the prompt this app queued.

The built-in workflow targets Krea 2 Turbo as described by community setup guides (UNETLoader
with `krea2_turbo_fp8_scaled.safetensors`, CLIPLoader of type `krea2` with the Qwen3-VL 4B
encoder, the Qwen image VAE, 8 steps at CFG 1 with euler/simple). It is unverified: the check
reports any node or model file the server does not have. A custom workflow in ComfyUI's API
format can replace it, using `{{prompt}}`, `{{negative}}`, `{{seed}}`, `{{width}}` and
`{{height}}` where the request's values belong.

Onboarding portraits follow an earlier picture. A ComfyUI server makes those only with a second
custom workflow that also has `{{reference_image}}` (a LoadImage node's image); the app uploads
the picture through `/upload/image` and puts its name there. There is no built-in one.
"""
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx

from companion.errors import DomainError
from companion.images.adapters.base import AdapterError, Check, ImageResult, media_type

TEMPLATE = Path(__file__).parent.parent / 'workflows' / 'krea2-turbo.json'
TEMPLATE_NAME = 'krea2-turbo (unverified)'
NUMERIC = {'{{seed}}', '{{width}}', '{{height}}'}
MODEL_KEYS = ('unet_name', 'ckpt_name')
LORA_NODE = 'prospero-lora'
REFERENCE = '{{reference_image}}'


def parse_workflow(text: str, reference=False) -> dict:
    try:
        workflow = json.loads(text)
    except json.JSONDecodeError as error:
        raise DomainError('The workflow is not valid JSON. Export it with "Save (API format)".', 422) from error
    if not isinstance(workflow, dict) or not workflow or not all(
            isinstance(node, dict) and 'class_type' in node for node in workflow.values()):
        raise DomainError('The workflow must be in ComfyUI API format: nodes with a class_type each.', 422)
    if '{{prompt}}' not in text:
        raise DomainError('Put {{prompt}} in the workflow where the prompt text belongs.', 422)
    if reference and REFERENCE not in text:
        raise DomainError('Put {{reference_image}} in the reference workflow as the image of a LoadImage node.', 422)
    return workflow


def workflow_for(config, reference=False) -> tuple[dict, str]:
    if reference:
        if not config.get('reference_workflow'):
            raise AdapterError('incompatible', 'This ComfyUI server has no workflow for pictures made from a '
                               'reference. Add one in Settings, Images.')
        return parse_workflow(config['reference_workflow'], reference=True), 'custom reference'
    if config.get('workflow'):
        return parse_workflow(config['workflow']), 'custom'
    return json.loads(TEMPLATE.read_text(encoding='utf-8')), TEMPLATE_NAME


def fill(value, values: dict):
    if isinstance(value, dict):
        return {key: fill(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [fill(item, values) for item in value]
    if isinstance(value, str):
        if value in NUMERIC:
            return values[value]
        for marker in ('{{prompt}}', '{{negative}}', REFERENCE):
            value = value.replace(marker, values[marker])
    return value


def with_lora(graph: dict, lora: dict) -> dict:
    """Insert a LoraLoaderModelOnly after the workflow's model loader and point everything that
    used the loader's model at it instead. LoKr files load through the same node."""
    source = next((node_id for node_id, node in graph.items()
                   if any(key in node.get('inputs', {}) for key in MODEL_KEYS)), None)
    if source is None:
        raise AdapterError('incompatible', 'The workflow has no model loader to attach the adopted LoRA to.')
    rewired = {node_id: {**node, 'inputs': {key: [LORA_NODE, 0] if value == [source, 0] else value
                                            for key, value in node.get('inputs', {}).items()}}
               for node_id, node in graph.items()}
    rewired[LORA_NODE] = {'class_type': 'LoraLoaderModelOnly', 'inputs': {
        'model': [source, 0], 'lora_name': lora['comfy_name'], 'strength_model': lora['strength']}}
    return rewired


def output_images(entry) -> list[dict]:
    images = []
    for output in (entry.get('outputs') or {}).values():
        images += [image for image in output.get('images', []) if image.get('type', 'output') == 'output']
    return images


def failure_text(entry) -> str:
    for message in (entry.get('status') or {}).get('messages', []):
        if isinstance(message, list) and message and message[0] == 'execution_error':
            detail = message[1] if len(message) > 1 and isinstance(message[1], dict) else {}
            return f"ComfyUI could not run the workflow: {detail.get('exception_message', 'unknown error')}".strip()
    return 'ComfyUI reported an error running the workflow.'


class ComfyAdapter:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, poll_seconds=1.0, timeout_seconds=900):
        self.transport = transport
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def client(self, base_url):
        return httpx.AsyncClient(base_url=base_url, transport=self.transport, timeout=30, trust_env=False,
                                 follow_redirects=False)

    async def generate(self, request) -> ImageResult:
        workflow, name = workflow_for(request.config, reference=request.reference is not None)
        prompt = request.prompt
        if request.lora and request.lora.get('trigger'):
            prompt = f"{request.lora['trigger']}, {prompt}"
        values = {'{{prompt}}': prompt, '{{negative}}': request.negative, '{{seed}}': request.seed,
                  '{{width}}': request.width, '{{height}}': request.height, REFERENCE: ''}
        async with self.client(request.config['base_url']) as client:
            if request.reference is not None:
                values[REFERENCE] = await self.upload(client, request)
            graph = fill(workflow, values)
            if request.lora:
                graph = with_lora(graph, request.lora)
                name = f"{name} + LoRA {request.lora['comfy_name']}"
            prompt_id = await self.submit(client, graph)
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    entry = await self.wait(client, prompt_id)
            except TimeoutError as error:
                await self.withdraw(client, prompt_id)
                raise AdapterError('timeout', 'ComfyUI did not finish within the time limit; the request was '
                                   'withdrawn.', prompt_id) from error
            except asyncio.CancelledError:
                await self.withdraw(client, prompt_id)
                raise
            images = output_images(entry)
            if not images:
                raise AdapterError('invalid_output', 'The workflow finished without saving an image. It needs a '
                                   'SaveImage node.', prompt_id)
            image = images[0]
            response = await self.call(client, 'GET', '/view', params={
                'filename': image['filename'], 'subfolder': image.get('subfolder', ''), 'type': 'output'})
        return ImageResult(response.content, model=self.model_name(workflow), workflow=name, seed=request.seed,
                           remote_id=prompt_id)

    @staticmethod
    def model_name(workflow) -> str | None:
        for node in workflow.values():
            for key in MODEL_KEYS:
                if isinstance(node.get('inputs', {}).get(key), str):
                    return node['inputs'][key]
        return None

    async def call(self, client, method, path, **kwargs) -> httpx.Response:
        try:
            response = await client.request(method, path, **kwargs)
        except httpx.RequestError as error:
            raise AdapterError('unavailable', 'Cannot reach the ComfyUI server. Check that it is running at the '
                               'configured address.') from error
        if response.status_code >= 500:
            raise AdapterError('failed', f'ComfyUI returned HTTP {response.status_code}.')
        return response

    async def upload(self, client, request) -> str:
        """Put the reference picture in ComfyUI's input folder under this job's own name."""
        extension, kind = media_type(request.reference)
        response = await self.call(client, 'POST', '/upload/image', data={'overwrite': 'true'},
                                   files={'image': (f'prospero-{request.job_id}.{extension}', request.reference, kind)})
        body = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        if not response.is_success or not isinstance(body.get('name'), str):
            raise AdapterError('failed', f'ComfyUI did not accept the reference picture (HTTP {response.status_code}).')
        return f"{body['subfolder']}/{body['name']}" if body.get('subfolder') else body['name']

    async def submit(self, client, graph) -> str:
        response = await self.call(client, 'POST', '/prompt', json={'prompt': graph, 'client_id': uuid4().hex})
        body = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
        if response.status_code == 400 or body.get('node_errors'):
            error = (body.get('error') or {}).get('message') if isinstance(body.get('error'), dict) else None
            raise AdapterError('incompatible', f"ComfyUI rejected the workflow: {error or 'invalid workflow'}. "
                               'Run the compatibility check in Settings.')
        if not response.is_success or 'prompt_id' not in body:
            raise AdapterError('failed', f'ComfyUI did not accept the request (HTTP {response.status_code}).')
        return body['prompt_id']

    async def wait(self, client, prompt_id) -> dict:
        while True:
            response = await self.call(client, 'GET', f'/history/{prompt_id}')
            entry = response.json().get(prompt_id) if response.is_success else None
            status = (entry or {}).get('status') or {}
            if status.get('status_str') == 'error':
                raise AdapterError('failed', failure_text(entry), prompt_id)
            if entry and (status.get('completed') or output_images(entry)):
                return entry
            await asyncio.sleep(self.poll_seconds)

    async def withdraw(self, client, prompt_id):
        """Remove our prompt if it is still pending, or interrupt it if it is the one running.
        Someone else's prompt is never touched."""
        try:
            queue = (await client.get('/queue')).json()
            if any(len(item) > 1 and item[1] == prompt_id for item in queue.get('queue_pending', [])):
                await client.post('/queue', json={'delete': [prompt_id]})
            elif any(len(item) > 1 and item[1] == prompt_id for item in queue.get('queue_running', [])):
                await client.post('/interrupt', json={'prompt_id': prompt_id})
        except (httpx.HTTPError, ValueError):
            pass

    @staticmethod
    def lora_problems(info, lora_name) -> list[str]:
        """The adopted LoRA must be in ComfyUI's loras folder under the name images will ask for."""
        if not lora_name:
            return []
        spec = info.get('LoraLoaderModelOnly')
        if spec is None:
            return ['Missing node: LoraLoaderModelOnly, which applies the adopted LoRA.']
        options = (spec.get('input', {}).get('required') or {}).get('lora_name', [None])[0]
        if isinstance(options, list) and lora_name not in options:
            return [f'The adopted LoRA {lora_name} is not in ComfyUI\'s loras folder.']
        return []

    @staticmethod
    def node_problems(info, workflow) -> list[str]:
        missing = []
        for node in workflow.values():
            spec = info.get(node['class_type'])
            if spec is None:
                missing.append(f"Missing node: {node['class_type']} (install the custom node that provides it).")
                continue
            required = {**(spec.get('input', {}).get('required') or {}), **(spec.get('input', {}).get('optional') or {})}
            for key_name, value in node.get('inputs', {}).items():
                options = required.get(key_name, [None])[0]
                # A placeholder such as {{reference_image}} is filled in per request.
                if isinstance(value, str) and '{{' not in value and isinstance(options, list) and value not in options:
                    missing.append(f'Missing file or option for {node["class_type"]}.{key_name}: {value}.')
        return missing

    async def check(self, backend, config, key=None) -> Check:
        """Ask the server which nodes and model files it has; nothing is queued or downloaded."""
        try:
            workflow, name = workflow_for(config)
            reference = workflow_for(config, reference=True)[0] if config.get('reference_workflow') else None
        except DomainError as error:
            return Check(False, error.message)
        try:
            async with self.client(config['base_url']) as client:
                response = await self.call(client, 'GET', '/object_info')
                info = response.json()
        except (AdapterError, ValueError) as error:
            return Check(False, getattr(error, 'message', 'ComfyUI returned an unreadable node list.'))
        missing = self.node_problems(info, workflow)
        if reference is not None:
            missing += [f'Reference workflow: {problem}' for problem in self.node_problems(info, reference)]
        missing += self.lora_problems(info, config.get('lora_name'))
        if missing:
            return Check(False, f'ComfyUI is reachable, but the {name} workflow cannot run yet.', missing)
        return Check(True, f'ComfyUI is reachable and has every node and model the {name} workflow uses.')
