"""Request bodies for each provider's own API.

Adapted from prosperos-study server/providers/requests.py at bbcbde4. Changes: requests carry the
Companion's conversation (a system text and alternating messages) instead of one prompt and one
input, and the LM Studio native protocol is not offered.
"""
from urllib.parse import quote

from companion.errors import require
from companion.providers.capabilities import SAMPLING, request_reasoning
from companion.providers.config import NEEDS_KEY

# Anthropic and Gemini require the conversation to open with the user's turn.
OPENING = '(The conversation so far.)'


def headers_for(config: dict, key: str | None) -> dict:
    headers = {'Content-Type': 'application/json'}
    if config['provider'] == 'anthropic':
        headers.update({'x-api-key': key or '', 'anthropic-version': '2023-06-01'})
    elif config['provider'] == 'google':
        headers['x-goog-api-key'] = key or ''
    elif key:
        headers['Authorization'] = f'Bearer {key}'
    return headers


def data_url(part: dict) -> str:
    return f"data:{part['media_type']};base64,{part['data']}"


# A message's content is text, or a list of text and image parts (companion/pictures.py) in each API's form.
PARTS = {
    'openai': lambda part: {'type': 'input_text', 'text': part['text']} if part['type'] == 'text'
    else {'type': 'input_image', 'image_url': data_url(part)},
    'anthropic': lambda part: {'type': 'text', 'text': part['text']} if part['type'] == 'text'
    else {'type': 'image', 'source': {'type': 'base64', 'media_type': part['media_type'], 'data': part['data']}},
    'chat': lambda part: {'type': 'text', 'text': part['text']} if part['type'] == 'text'
    else {'type': 'image_url', 'image_url': {'url': data_url(part)}},
    'google': lambda part: {'text': part['text']} if part['type'] == 'text'
    else {'inline_data': {'mime_type': part['media_type'], 'data': part['data']}},
}


def content_for(api: str, content):
    return content if isinstance(content, str) else [PARTS[api](part) for part in content]


def sampling(config: dict) -> dict:
    return {key: config[key] for key in SAMPLING[config['provider']] if config.get(key) is not None}


def alternating(messages: list[dict]) -> list[dict]:
    """Merge consecutive turns by the same speaker and open with the user's turn."""
    result = []
    for message in messages:
        if result and result[-1]['role'] == message['role'] and isinstance(message['content'], str) \
                and isinstance(result[-1]['content'], str):
            result[-1] = {'role': message['role'], 'content': result[-1]['content'] + '\n\n' + message['content']}
        else:
            result.append({'role': message['role'], 'content': message['content']})
    if not result or result[0]['role'] != 'user':
        result.insert(0, {'role': 'user', 'content': OPENING})
    return result


def transcript(system: str, messages: list[dict]) -> str:
    """One prompt for adapters without a message format (Kobold, Codex CLI)."""
    turns = [f"{'User' if message['role'] == 'user' else 'Assistant'}: {message['content']}" for message in messages]
    return '\n\n'.join([system, *turns, 'Assistant:'])


def openai_request(config: dict, system: str, messages: list[dict]) -> tuple[str, dict]:
    body = {'model': config['model'], 'instructions': system,
            'input': [{'role': message['role'], 'content': content_for('openai', message['content'])}
                      for message in messages],
            'max_output_tokens': config['max_output_tokens'], 'store': False, 'stream': True, **sampling(config)}
    if config.get('reasoning_effort'):
        body['reasoning'] = {'effort': config['reasoning_effort']}
    if config.get('response_verbosity'):
        body['text'] = {'verbosity': config['response_verbosity']}
    return '/responses', body


def anthropic_request(config: dict, system: str, messages: list[dict]) -> tuple[str, dict]:
    turns = [{**turn, 'content': content_for('anthropic', turn['content'])} for turn in alternating(messages)]
    body = {'model': config['model'], 'system': system, 'messages': turns,
            'max_tokens': config['max_output_tokens'], 'stream': True, **sampling(config)}
    mode = config.get('thinking_mode')
    if mode:
        body['thinking'] = {'type': {'off': 'disabled', 'budget': 'enabled', 'adaptive': 'adaptive'}[mode]}
        if mode == 'budget':
            body['thinking']['budget_tokens'] = config['thinking_budget_tokens']
    if config.get('reasoning_effort'):
        body['output_config'] = {'effort': config['reasoning_effort']}
    return '/messages', body


def chat_request(config: dict, system: str, messages: list[dict]) -> tuple[str, dict]:
    turns = [{**message, 'content': content_for('chat', message['content'])} for message in messages]
    body = {'model': config['model'], 'messages': [{'role': 'system', 'content': system}, *turns],
            config.get('output_token_parameter', 'max_tokens'): config['max_output_tokens'],
            'stream': True, **sampling(config)}
    if config['provider'] == 'openrouter':
        body['provider'] = {'allow_fallbacks': False, 'require_parameters': True}
        if reasoning := request_reasoning(config):
            body['reasoning'] = reasoning
    elif config.get('reasoning_effort'):
        body['reasoning_effort'] = config['reasoning_effort']
    if config.get('compatible_thinking') is not None:
        body['chat_template_kwargs'] = {'enable_thinking': config['compatible_thinking']}
    if config['provider'] in {'openrouter', 'nanogpt', 'local', 'compatible'}:
        body['stream_options'] = {'include_usage': True}
    return '/chat/completions', body


def kobold_request(config: dict, system: str, messages: list[dict]) -> tuple[str, dict]:
    options = sampling(config)
    if 'repetition_penalty' in options:
        options['rep_pen'] = options.pop('repetition_penalty')
    return '/generate', {'prompt': transcript(system, messages), 'max_length': config['max_output_tokens'],
                         'max_context_length': config['context_tokens'], **options}


def google_request(config: dict, system: str, messages: list[dict]) -> tuple[str, dict]:
    model = quote(config['model'].removeprefix('models/'), safe='')
    options = {'maxOutputTokens': config['max_output_tokens'], **sampling(config)}
    for source, target in [('top_p', 'topP'), ('top_k', 'topK')]:
        if source in options:
            options[target] = options.pop(source)
    if config.get('thinking_mode'):
        options['thinkingConfig'] = {'thinkingBudget': 0 if config['thinking_mode'] == 'off'
                                     else config['thinking_budget_tokens']}
    elif config.get('reasoning_effort'):
        options['thinkingConfig'] = {'thinkingLevel': config['reasoning_effort']}
    contents = [{'role': 'user' if message['role'] == 'user' else 'model',
                 'parts': [{'text': message['content']}] if isinstance(message['content'], str)
                 else content_for('google', message['content'])} for message in alternating(messages)]
    return f'/models/{model}:streamGenerateContent?alt=sse', {
        'systemInstruction': {'parts': [{'text': system}]}, 'contents': contents, 'generationConfig': options}


REQUESTS = {'openai': openai_request, 'anthropic': anthropic_request, 'openrouter': chat_request,
            'nanogpt': chat_request, 'local': chat_request, 'compatible': chat_request,
            'kobold': kobold_request, 'google': google_request}


def validate_key(provider: str, key: str | None):
    if provider in NEEDS_KEY:
        require(bool(key), 'This model profile needs an API key. Add it in Settings > Models or set the '
                'provider environment variable.', 409)
