"""Hosted image APIs with the user's own key (PRD F9).

Two request shapes cover the tested providers:

- `images`: OpenAI-style `POST /images/generations`, used by the OpenAI API and Google's
  OpenAI-compatible endpoint for its image models.
- `chat`: `POST /chat/completions` with `modalities: ["image", "text"]`, used by OpenRouter's
  image models, which return the picture as a data URL in `message.images`.

A request carries only the prompt (X2), except an onboarding portrait, which also carries the
picture it follows: in the chat message, or as the image of an OpenAI `/images/edits` request. Provider-reported usage is recorded as given; unknown
cost stays unknown. A provider's content refusal is reported as `refused`, which reclassifies the
request as NSFW so it is never offered to another hosted provider (F6).
"""
import base64
from urllib.parse import urlsplit

import httpx

from companion.images.adapters.base import AdapterError, Check, ImageResult, media_type

REFUSAL_SIGNS = ('content_policy', 'content policy', 'safety', 'moderation', 'prohibited', 'blocked', 'nsfw')
TIMEOUT_SECONDS = 180
# Request paths people paste with the base URL from a provider's docs; the adapter adds them itself.
ENDPOINT_SUFFIXES = ('/images/generations', '/images/edits', '/images/edit', '/chat/completions', '/models', '/images')


def api_base(value: str) -> str:
    """The API base without a trailing request path, so a URL copied from an endpoint's docs (say
    `https://nano-gpt.com/api/v1/images/generations`) still works. Applied when saving and again
    when calling, for backends saved before this."""
    value = value.strip().rstrip('/')
    for suffix in ENDPOINT_SUFFIXES:
        if value.endswith(suffix) and urlsplit(value).path != suffix:
            return value.removesuffix(suffix).rstrip('/')
    return value


def refused(text: str) -> bool:
    lowered = text.casefold()
    return any(sign in lowered for sign in REFUSAL_SIGNS)


def decode_data_url(url: str) -> bytes:
    header, _, payload = url.partition(',')
    if not header.startswith('data:image/') or ';base64' not in header:
        raise AdapterError('invalid_output', 'The provider returned an image in an unexpected form.')
    return base64.b64decode(payload, validate=False)


def models_url(config, provider) -> str:
    """Where the provider lists its image models. NanoGPT's `/models` lists text models only, so a
    NanoGPT address (chosen by name or entered as another API) uses its image list."""
    host = urlsplit(config['base_url']).hostname or ''
    if provider == 'nanogpt' or host == 'nano-gpt.com' or host.endswith('.nano-gpt.com'):
        return config['base_url'] + '/images/models'
    return config['base_url'] + '/models'


def takes_reference(config, provider) -> bool:
    """Chat-style image models read a picture in the message; of the `images` style, only the
    OpenAI API's `/images/edits` is a tested shape for one."""
    return config.get('api_style') == 'chat' or provider == 'openai'


def chat_content(prompt: str, reference: bytes | None):
    if reference is None:
        return prompt
    _extension, kind = media_type(reference)
    url = f"data:{kind};base64,{base64.b64encode(reference).decode('ascii')}"
    return [{'type': 'text', 'text': prompt}, {'type': 'image_url', 'image_url': {'url': url}}]


class HostedAdapter:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, timeout_seconds=TIMEOUT_SECONDS):
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def client(self):
        return httpx.AsyncClient(transport=self.transport, timeout=self.timeout_seconds, trust_env=False,
                                 follow_redirects=False)

    async def generate(self, request) -> ImageResult:
        if not request.key:
            raise AdapterError('auth', 'Add an API key for this provider in Settings.')
        config, provider = {**request.config, 'base_url': api_base(request.config['base_url'])}, request.backend['provider']
        prompt = f'{request.prompt}\nAvoid: {request.negative}' if request.negative else request.prompt
        headers = {'Authorization': f'Bearer {request.key}'}
        if request.reference is not None and not takes_reference(config, provider):
            raise AdapterError('incompatible', 'This image API cannot make a picture from a reference picture.')
        async with self.client() as client:
            if config.get('api_style') == 'chat':
                body = {'model': config['model'], 'modalities': ['image', 'text'],
                        'messages': [{'role': 'user', 'content': chat_content(prompt, request.reference)}]}
                data = await self.post(client, config['base_url'] + '/chat/completions', headers, body)
                image = self.chat_image(data)
            elif request.reference is not None:
                data = await self.edit(client, config, headers, prompt, request)
                image = await self.images_image(client, data)
            else:
                body = {'model': config['model'], 'prompt': prompt, 'n': 1, 'size': f'{request.width}x{request.height}'}
                if provider != 'openai':
                    body['response_format'] = 'b64_json'
                data = await self.post(client, config['base_url'] + '/images/generations', headers, body)
                image = await self.images_image(client, data)
        return ImageResult(image, model=config['model'], workflow=f"{provider} {config.get('api_style')}",
                           usage=data.get('usage') if isinstance(data.get('usage'), dict) else None,
                           remote_id=data.get('id') if isinstance(data.get('id'), str) else None)

    async def edit(self, client, config, headers, prompt, request) -> dict:
        """OpenAI's `/images/edits`: the reference goes up as a file beside the prompt."""
        extension, kind = media_type(request.reference)
        fields = {'model': config['model'], 'prompt': prompt, 'n': '1', 'size': f'{request.width}x{request.height}'}
        files = {'image': (f'reference.{extension}', request.reference, kind)}
        return await self.post(client, config['base_url'] + '/images/edits', headers, None, data=fields, files=files)

    async def post(self, client, url, headers, body, **form) -> dict:
        try:
            response = await client.post(url, headers=headers, **form) if form else \
                await client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as error:
            raise AdapterError('timeout', 'The provider did not answer within the time limit.') from error
        except httpx.RequestError as error:
            raise AdapterError('unavailable', 'Cannot reach the provider. Check the address and your network.') \
                from error
        text = response.text[:2000]
        if response.status_code in (401, 403):
            raise AdapterError('auth', 'The provider rejected the API key. Update it in Settings.')
        if response.status_code == 429:
            raise AdapterError('rate_limited', 'The provider reached a rate or usage limit. Try again later.')
        if response.status_code >= 400 and refused(text):
            raise AdapterError('refused', 'The provider refused this image under its content rules.')
        if not response.is_success:
            raise AdapterError('failed', f'The provider rejected the request (HTTP {response.status_code}).')
        try:
            data = response.json()
        except ValueError as error:
            raise AdapterError('invalid_output', 'The provider returned an unreadable response.') from error
        if not isinstance(data, dict):
            raise AdapterError('invalid_output', 'The provider returned an unreadable response.')
        return data

    @staticmethod
    def chat_image(data) -> bytes:
        choice = (data.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        for image in message.get('images') or []:
            url = (image.get('image_url') or {}).get('url') if isinstance(image, dict) else None
            if isinstance(url, str):
                return decode_data_url(url)
        if choice.get('finish_reason') == 'content_filter' or refused(str(message.get('refusal') or '')):
            raise AdapterError('refused', 'The provider refused this image under its content rules.')
        raise AdapterError('invalid_output', 'The model answered without an image. Check that it is an image model.')

    async def images_image(self, client, data) -> bytes:
        item = (data.get('data') or [{}])[0]
        if isinstance(item.get('b64_json'), str):
            return base64.b64decode(item['b64_json'])
        url = item.get('url')
        if isinstance(url, str) and url.startswith('https://'):
            try:
                response = await client.get(url)
            except httpx.RequestError as error:
                raise AdapterError('unavailable', 'Could not download the finished image.') from error
            if response.is_success:
                return response.content
        raise AdapterError('invalid_output', 'The provider answered without an image.')

    async def check(self, backend, config, key=None) -> Check:
        """Lists the provider's models with the key; sends no prompt and spends no image quota."""
        if not key:
            return Check(False, 'Add an API key for this provider.')
        config = {**config, 'base_url': api_base(config['base_url'])}
        try:
            async with self.client() as client:
                url = models_url(config, backend.get('provider'))
                response = await client.get(url, headers={'Authorization': f'Bearer {key}'})
        except httpx.RequestError:
            return Check(False, 'Cannot reach the provider at this address.')
        if response.status_code in (401, 403):
            return Check(False, 'The provider rejected the API key.')
        if response.status_code in (404, 405):
            return Check(False, f'Nothing answered at {url}, so the key and model could not be checked.', [
                'Check the API base URL: it should end at the API version (like /v1), without '
                '/images/generations on the end.',
                'Some services have no model list. Making an image is the real test, and Check never blocks it.'])
        if not response.is_success:
            return Check(False, f'The provider answered HTTP {response.status_code} when listing models.')
        try:
            ids = [str(model.get('id', '')).removeprefix('models/') for model in response.json().get('data', [])]
        except (ValueError, AttributeError):
            ids = []
        if config.get('model') and ids and config['model'] not in ids:
            return Check(False, f"The key works, but the provider does not list the model {config['model']}.")
        return Check(True, 'The key works and the provider lists this model. Image output itself is not tested '
                     'until you make an image.')
