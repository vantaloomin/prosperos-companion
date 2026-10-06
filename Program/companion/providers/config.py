"""Provider presets and model profile settings.

Adapted from prosperos-study server/providers/config.py at bbcbde4. Changes: the LM Studio native
protocol and its reasoning control are not offered (local servers use the OpenAI-compatible API),
environment fallbacks use Companion names for local and compatible services, and Codex text
generation runs through the same CLI login the image backend uses.
"""
from typing import ClassVar, Literal
from urllib.parse import urlsplit

from pydantic import Field, ValidationInfo, model_validator

from companion.errors import DomainError
from companion.models import Input
from companion.providers.capabilities import validate_options
from companion.providers.urls import is_loopback, validate_compatible_url

Provider = Literal['openai', 'anthropic', 'openrouter', 'google', 'compatible', 'local', 'kobold', 'codex']
PROVIDER_NAMES = {'openai': 'OpenAI', 'anthropic': 'Anthropic', 'openrouter': 'OpenRouter',
                  'google': 'Google / Gemini', 'compatible': 'OpenAI-compatible API', 'local': 'Local / LM Studio',
                  'kobold': 'Kobold', 'codex': 'Codex / ChatGPT'}
DEFAULT_URLS = {
    'openai': 'https://api.openai.com/v1',
    'anthropic': 'https://api.anthropic.com/v1',
    'openrouter': 'https://openrouter.ai/api/v1',
    'google': 'https://generativelanguage.googleapis.com/v1beta',
    'compatible': '',
    'local': 'http://127.0.0.1:1234/v1',
    'kobold': 'http://127.0.0.1:5001/api/v1',
    'codex': '',
}
# Standard variable names for hosted services; the Companion's own name for anything else.
ENV_KEYS = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'openrouter': 'OPENROUTER_API_KEY',
            'google': 'GEMINI_API_KEY', 'compatible': 'COMPANION_API_KEY', 'local': 'COMPANION_API_KEY'}
# Providers whose official API needs a key; local servers and compatible services may not.
NEEDS_KEY = {'openai', 'anthropic', 'openrouter', 'google'}
EMBEDDING_PROVIDERS = {'openai', 'compatible', 'local'}


def validate_local_url(url: str):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not is_loopback(parts.hostname):
        raise ValueError('Local services must use a localhost or loopback HTTP(S) address.')
    if any((parts.username, parts.password, parts.query, parts.fragment)):
        raise ValueError('Put credentials in the API key field, not in the server address.')


def validate_profile_url(provider, url, allow_incomplete=False):
    if provider in {'local', 'kobold'}:
        validate_local_url(url)
    elif provider == 'compatible':
        if url or not allow_incomplete:
            try:
                validate_compatible_url(url)
            except DomainError as error:
                raise ValueError(error.message) from error
    elif url != DEFAULT_URLS[provider]:
        raise ValueError('This provider uses its official API address.')


def profile_ready(config) -> bool:
    return bool(config.get('model', '').strip()) and (config['provider'] == 'codex' or bool(config.get('base_url')))


class ReportedCapabilities(Input):
    model_id: str
    context_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    supported_parameters: list[str] | None = Field(default=None, max_length=100)
    supported_efforts: list[str] | None = Field(default=None, max_length=20)


class ProfileConfig(Input):
    allow_incomplete: ClassVar[bool] = False
    provider: Provider
    model: str = Field(min_length=1, max_length=200)
    base_url: str = ''
    max_output_tokens: int = Field(default=800, ge=64, le=128000)
    context_tokens: int = Field(default=16000, ge=1024, le=2000000)
    timeout_seconds: int = Field(default=180, ge=10, le=1800)
    temperature: float | None = Field(default=None, ge=0, le=2)
    reasoning_effort: Literal['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'] | None = None
    top_p: float | None = Field(default=None, ge=0, le=1)
    top_k: int | None = Field(default=None, ge=0, le=1000)
    min_p: float | None = Field(default=None, ge=0, le=1)
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2)
    presence_penalty: float | None = Field(default=None, ge=-2, le=2)
    repetition_penalty: float | None = Field(default=None, gt=0, le=3)
    seed: int | None = Field(default=None, ge=0, le=2147483647)
    thinking_mode: Literal['off', 'budget', 'adaptive'] | None = None
    thinking_budget_tokens: int | None = Field(default=None, ge=-1, le=128000)
    response_reserve_tokens: int = Field(default=256, ge=64, le=128000)
    response_verbosity: Literal['low', 'medium', 'high'] | None = None
    compatible_thinking: bool | None = None
    output_token_parameter: Literal['max_tokens', 'max_completion_tokens'] = 'max_tokens'
    reported_capabilities: ReportedCapabilities | None = None
    resource_group: str = Field(default='', max_length=80, pattern=r'^[a-zA-Z0-9 _.-]*$')
    # Optional; semantic recall uses this model through the same service's /embeddings.
    embedding_model: str = Field(default='', max_length=200)

    @model_validator(mode='after')
    def validate_capabilities(self, info: ValidationInfo):
        self.base_url = (self.base_url or DEFAULT_URLS[self.provider]).rstrip('/')
        validate_profile_url(self.provider, self.base_url, self.allow_incomplete)
        if self.provider == 'codex' and self.temperature is not None:
            raise ValueError('Codex CLI does not support a temperature setting here.')
        if self.provider == 'anthropic' and self.temperature is not None and self.temperature > 1:
            raise ValueError('Anthropic temperature must be between 0 and 1.')
        if self.embedding_model.strip() and self.provider not in EMBEDDING_PROVIDERS:
            raise ValueError('Embeddings need an OpenAI, local or OpenAI-compatible connection.')
        validate_options(self)
        return self


class DiscoveryConfig(ProfileConfig):
    model: str = Field(default='', max_length=200)


class SavedProfileConfig(ProfileConfig):
    """A profile can be saved before a model is chosen, so a key is never lost to an unfinished form."""
    allow_incomplete: ClassVar[bool] = True
    model: str = Field(default='', max_length=200)


class ConnectionProbe(Input):
    config: DiscoveryConfig
    api_key: str | None = Field(default=None, max_length=4000)
    profile_id: str | None = None


class ProfileCreate(Input):
    name: str = Field(default='', max_length=120)
    config: SavedProfileConfig
    api_key: str | None = Field(default=None, max_length=4000)


class ProfileUpdate(ProfileCreate):
    expected_revision: int


class RouteUpdate(Input):
    job: str = Field(min_length=1, max_length=40)
    profile_id: str | None = None
