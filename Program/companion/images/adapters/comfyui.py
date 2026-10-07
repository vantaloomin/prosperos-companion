"""Headless ComfyUI over its HTTP API (PRD F7).

The app only talks to a ComfyUI server the user configured. It never starts, stops or restarts
one, and cancelling removes or interrupts only the prompt this app queued.

The built-in workflow targets Krea 2 Turbo with the files ComfyUI's own Krea 2 template uses
(UNETLoader with `krea2_turbo_fp8_scaled.safetensors`, CLIPLoader of type `krea2` with
`qwen3vl_4b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors`, 8 steps at CFG 1 with
euler/simple). It ran on an RTX 5090 with ComfyUI 0.39.0, with other files chosen for the three
loaders. The check reports any node or model file the server does not have. A custom workflow in
ComfyUI's API format can replace it, using `{{prompt}}`, `{{negative}}`, `{{seed}}`, `{{width}}`
and `{{height}}` where the request's values belong.

With the built-in workflow the user can pick other files from their server for its three loaders
(`unet_name`, `clip_name` with its `type`, and `vae_name` in the backend's config); `files` asks the
server which ones it has. Names are kept exactly as the server lists them, subfolder and all
(`Krea 2\\model.safetensors` on Windows). A custom workflow is used exactly as given.

Onboarding portraits follow an earlier picture. A ComfyUI server makes those only with a second
custom workflow that also has `{{reference_image}}` (a LoadImage node's image); the app uploads
the picture through `/upload/image` and puts its name there. There is no built-in one.
"""
import asyncio
import json
import re
from pathlib import Path
from uuid import uuid4

import httpx

from companion.errors import DomainError
from companion.images.adapters.base import AdapterError, Check, ImageResult, media_type

TEMPLATE = Path(__file__).parent.parent / 'workflows' / 'krea2-turbo.json'
TEMPLATE_NAME = 'krea2-turbo'
NUMERIC = {'{{seed}}', '{{width}}', '{{height}}'}
MODEL_KEYS = ('unet_name', 'ckpt_name')
LORA_NODE = 'prospero-lora'
REFERENCE = '{{reference_image}}'
# The built-in workflow's loader inputs the user can choose files for: config key -> (node, input).
FILE_INPUTS = {'unet_name': ('UNETLoader', 'unet_name'), 'clip_name': ('CLIPLoader', 'clip_name'),
               'clip_type': ('CLIPLoader', 'type'), 'vae_name': ('VAELoader', 'vae_name')}
LORA_INPUT = ('LoraLoaderModelOnly', 'lora_name')
# The built-in workflow's KSampler settings the user can change for their model; unset means the
# workflow's own (8 steps, CFG 1, euler, simple: Krea 2 Turbo's).
SAMPLER_INPUTS = ('steps', 'cfg', 'sampler_name', 'scheduler')
SAMPLER_LISTS = ('sampler_name', 'scheduler')
# Which listed files are Krea 2's, matched on the whole path so a "Krea 2" folder counts. ComfyUI
# cannot say a file's model family, so these only sort a list; nothing is hidden for not matching.
KREA_FILES = {'unet_name': re.compile(r'krea|kr2|kera', re.IGNORECASE),
              'clip_name': re.compile(r'qwen[-_ ]?3[-_ ]?vl[-_ ]?4b', re.IGNORECASE),
              'vae_name': re.compile(r'qwen.*vae|krea', re.IGNORECASE),
              'lora': re.compile(r'krea|kr2|kera', re.IGNORECASE)}


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
    return built_in(config), TEMPLATE_NAME


def built_in(config) -> dict:
    """The built-in workflow with the user's chosen loader files in place of its defaults."""
    workflow = json.loads(TEMPLATE.read_text(encoding='utf-8'))
    chosen = [(class_type, name, config[key]) for key, (class_type, name) in FILE_INPUTS.items() if config.get(key)]
    chosen += [('KSampler', key, config[key]) for key in SAMPLER_INPUTS if config.get(key) not in (None, '')]
    for class_type, name, value in chosen:
        for node in workflow.values():
            if node['class_type'] == class_type:
                node['inputs'][name] = value
    return workflow


def default_sampler() -> dict:
    sampler = next(node for node in built_in({}).values() if node['class_type'] == 'KSampler')
    return {key: sampler['inputs'][key] for key in SAMPLER_INPUTS}


def default_files() -> dict:
    workflow = built_in({})
    return {key: next(node['inputs'][name] for node in workflow.values() if node['class_type'] == class_type)
            for key, (class_type, name) in FILE_INPUTS.items()}


def options_of(spec) -> list | None:
    """The choices of a combo input in /object_info: `[[...], {...}]`, or `["COMBO", {"options": [...]}]`
    in newer ComfyUI versions. None for any other kind of input."""
    if not isinstance(spec, list) or not spec:
        return None
    if isinstance(spec[0], list):
        return spec[0]
    if spec[0] == 'COMBO' and len(spec) > 1 and isinstance(spec[1], dict) and isinstance(spec[1].get('options'), list):
        return spec[1]['options']
    return None


def input_options(info, class_type, name) -> list[str]:
    inputs = (info.get(class_type) or {}).get('input') or {}
    spec = {**(inputs.get('optional') or {}), **(inputs.get('required') or {})}.get(name)
    return [option for option in options_of(spec) or [] if isinstance(option, str)]


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


def with_lora(graph: dict, lora: dict, node=LORA_NODE, source=None) -> dict:
    """Insert a LoraLoaderModelOnly after the workflow's model loader (or after `source`, an
    earlier LoRA) and point everything that used that model at it instead. LoKr files load
    through the same node."""
    source = source or next((node_id for node_id, item in graph.items()
                             if any(key in item.get('inputs', {}) for key in MODEL_KEYS)), None)
    if source is None:
        raise AdapterError('incompatible', 'The workflow has no model loader to attach the LoRA to.')
    rewired = {node_id: {**item, 'inputs': {key: [node, 0] if value == [source, 0] else value
                                            for key, value in item.get('inputs', {}).items()}}
               for node_id, item in graph.items()}
    rewired[node] = {'class_type': 'LoraLoaderModelOnly', 'inputs': {
        'model': [source, 0], 'lora_name': lora['comfy_name'], 'strength_model': lora['strength']}}
    return rewired


def with_loras(graph: dict, character: dict | None, styles: list[dict]) -> dict:
    """The character's LoRA first, so its likeness always applies, then each style LoRA after it."""
    source = None
    if character:
        graph, source = with_lora(graph, character), LORA_NODE
    for index, style in enumerate(styles, start=1):
        node = f'prospero-style-lora-{index}'
        graph = with_lora(graph, {'comfy_name': style['name'], 'strength': style['strength']}, node, source)
        source = node
    return graph


def style_loras(config, character: dict | None) -> list[dict]:
    """The backend's style LoRAs, leaving out the character's own file so it is never applied twice."""
    skip = character and character.get('comfy_name')
    return [lora for lora in config.get('style_loras') or [] if lora.get('name') and lora['name'] != skip]


def triggered(prompt: str, character: dict | None, styles: list[dict]) -> str:
    words = [character['trigger']] if character and character.get('trigger') else []
    words += [style['trigger'] for style in styles if style.get('trigger')]
    return ', '.join([*words, prompt])


def krea_first(key: str, options: list[str]) -> tuple[list[str], list[str]]:
    """The list with Krea 2's files first, and which those are."""
    pattern = KREA_FILES.get(key)
    found = [option for option in options if pattern and pattern.search(option)]
    return found + [option for option in options if option not in found], found


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
        if name == TEMPLATE_NAME and any(request.config.get(key) not in (None, '') for key in SAMPLER_INPUTS):
            used = {**default_sampler(), **{key: request.config[key] for key in SAMPLER_INPUTS
                                             if request.config.get(key) not in (None, '')}}
            name = f"{name} ({used['steps']} steps, CFG {used['cfg']:g}, {used['sampler_name']}/{used['scheduler']})"
        styles = style_loras(request.config, request.lora)
        prompt = triggered(request.prompt, request.lora, styles)
        values = {'{{prompt}}': prompt, '{{negative}}': request.negative, '{{seed}}': request.seed,
                  '{{width}}': request.width, '{{height}}': request.height, REFERENCE: ''}
        async with self.client(request.config['base_url']) as client:
            if request.reference is not None:
                values[REFERENCE] = await self.upload(client, request)
            graph = fill(workflow, values)
            if request.lora or styles:
                graph = with_loras(graph, request.lora, styles)
            if request.lora:
                name = f"{name} + LoRA {request.lora['comfy_name']}"
            for style in styles:
                name = f"{name} + style LoRA {style['name']} at {style['strength']:g}"
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
    def lora_problems(info, lora_name, styles=()) -> list[str]:
        """The adopted LoRA and each style LoRA must be in ComfyUI's loras folder under the name
        images will ask for."""
        wanted = [(f'The adopted LoRA {lora_name}', lora_name)] if lora_name else []
        wanted += [(f"The style LoRA {style['name']}", style['name']) for style in styles]
        if not wanted:
            return []
        spec = info.get('LoraLoaderModelOnly')
        if spec is None:
            return ['Missing node: LoraLoaderModelOnly, which applies LoRAs.']
        options = options_of((spec.get('input', {}).get('required') or {}).get('lora_name'))
        return [f"{label} is not in ComfyUI's loras folder." for label, name in wanted
                if options is not None and name not in options]

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
                options = options_of(required.get(key_name))
                # A placeholder such as {{reference_image}} is filled in per request.
                if isinstance(value, str) and '{{' not in value and options is not None and value not in options:
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
        missing += self.lora_problems(info, config.get('lora_name'),
                                      style_loras(config, {'comfy_name': config.get('lora_name')}))
        if missing:
            return Check(False, f'ComfyUI is reachable, but the {name} workflow cannot run yet.', missing)
        return Check(True, f'ComfyUI is reachable and has every node and model the {name} workflow uses.')

    async def files(self, config) -> dict:
        """The files the server offers the built-in workflow's loaders, asked of the configured
        address with the same client as the check. Nothing is queued or downloaded."""
        found = {}
        async with self.client(config['base_url']) as client:
            for class_type in dict.fromkeys([*(class_type for class_type, _ in FILE_INPUTS.values()), LORA_INPUT[0],
                                             'KSampler']):
                response = await self.call(client, 'GET', f'/object_info/{class_type}')
                try:
                    found[class_type] = response.json() if response.is_success else {}
                except ValueError as error:
                    raise AdapterError('failed', 'ComfyUI returned an unreadable node list.') from error
                if not isinstance(found[class_type], dict):
                    raise AdapterError('failed', 'ComfyUI returned an unreadable node list.')
        lists = {**FILE_INPUTS, 'lora': LORA_INPUT, **{key: ('KSampler', key) for key in SAMPLER_LISTS}}
        return {key: input_options(found[class_type], class_type, name) for key, (class_type, name) in lists.items()}
