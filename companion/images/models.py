"""Request bodies for image generation (PRD F3–F9)."""
from typing import Literal

from pydantic import Field

from companion.models import Input

Kind = Literal['comfyui', 'codex', 'hosted']
Provider = Literal['comfyui', 'codex', 'openrouter', 'google', 'openai', 'other']
Aspect = Literal['square', 'landscape', 'portrait']


class BackendFields(Input):
    label: str | None = Field(default=None, max_length=80)
    enabled: bool | None = None
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    # ComfyUI workflow in API format with {{prompt}}, {{negative}}, {{seed}}, {{width}} and {{height}}.
    workflow: str | None = Field(default=None, max_length=200000)
    cli_path: str | None = Field(default=None, max_length=1000)
    # Codex only: `native` runs `codex exec`; `imagegen_cli` runs the optional chatgpt-imagegen CLI.
    method: Literal['native', 'imagegen_cli'] | None = None
    api_style: Literal['images', 'chat'] | None = None
    api_key: str | None = Field(default=None, max_length=4000)
    controlled_machine: bool | None = None
    concurrency: int | None = Field(default=None, ge=1, le=4)
    accept_disclosure: bool | None = None


class BackendCreate(BackendFields):
    kind: Kind
    provider: Provider | None = None


class BackendMove(Input):
    position: int = Field(ge=0, le=50)


class ImageSettingsUpdate(Input):
    automatic_images: bool | None = None
    daily_limit: int | None = Field(default=None, ge=0, le=24)
    queue_limit: int | None = Field(default=None, ge=1, le=20)
    fallback: bool | None = None
    aspect: Aspect | None = None
    style: str | None = Field(default=None, max_length=500)


class JobCreate(Input):
    post_id: str
    backend_id: str | None = None
    marked_nsfw: bool = False


class JobRetry(Input):
    # Retry keeps the original inputs unless the user explicitly chooses current settings (F4).
    current_settings: bool = False
    backend_id: str | None = None


class Preview(Input):
    post_id: str
    marked_nsfw: bool = False
