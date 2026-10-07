"""Request bodies for image generation (PRD F3–F9)."""
from typing import Literal

from pydantic import Field

from companion.models import Input

Kind = Literal['comfyui', 'codex', 'hosted']
Provider = Literal['comfyui', 'codex', 'openrouter', 'google', 'openai', 'other']
Aspect = Literal['square', 'landscape', 'portrait']
FILE_NAME = r'^[^\x00-\x1f\x7f]*$'


class StyleLora(Input):
    """A LoRA from ComfyUI's loras folder applied after the character's own, with its trigger words."""
    name: str = Field(min_length=1, max_length=300, pattern=FILE_NAME)
    strength: float = Field(default=0.7, ge=-2, le=2)
    trigger: str = Field(default='', max_length=200, pattern=FILE_NAME)


class BackendFields(Input):
    label: str | None = Field(default=None, max_length=80)
    enabled: bool | None = None
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, max_length=200)
    # ComfyUI workflow in API format with {{prompt}}, {{negative}}, {{seed}}, {{width}} and {{height}}.
    workflow: str | None = Field(default=None, max_length=200000)
    # A second ComfyUI workflow for pictures that follow an earlier one, with {{reference_image}} too.
    reference_workflow: str | None = Field(default=None, max_length=200000)
    # Files from the ComfyUI server for the built-in workflow's loaders; empty means its default.
    unet_name: str | None = Field(default=None, max_length=300, pattern=FILE_NAME)
    clip_name: str | None = Field(default=None, max_length=300, pattern=FILE_NAME)
    clip_type: str | None = Field(default=None, max_length=60, pattern=FILE_NAME)
    vae_name: str | None = Field(default=None, max_length=300, pattern=FILE_NAME)
    # The built-in workflow's sampler; a value equal to the workflow's own is stored as unset.
    steps: int | None = Field(default=None, ge=1, le=100)
    cfg: float | None = Field(default=None, ge=0, le=30)
    sampler_name: str | None = Field(default=None, max_length=60, pattern=FILE_NAME)
    scheduler: str | None = Field(default=None, max_length=60, pattern=FILE_NAME)
    # Style LoRAs for ComfyUI, in order; an empty list removes them.
    style_loras: list[StyleLora] | None = Field(default=None, max_length=3)
    cli_path: str | None = Field(default=None, max_length=1000)
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
    chat_photos: bool | None = None
    unprompted_photos: bool | None = None
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
