"""Request bodies for the LoRA maker."""
from typing import Literal

from pydantic import Field

from companion.models import Input

Rights = Literal['own_work', 'commissioned', 'licensed', 'generated', 'unknown']
Role = Literal['train', 'evaluation', 'excluded']


class LoraSettingsUpdate(Input):
    python_path: str | None = Field(default=None, max_length=1000)
    trainer_dir: str | None = Field(default=None, max_length=1000)
    base_model: str | None = Field(default=None, min_length=1, max_length=1000)
    comfy_lora_dir: str | None = Field(default=None, max_length=1000)


class ReferenceUpdate(Input):
    rights: Rights | None = None
    source_note: str | None = Field(default=None, max_length=1000)
    role: Role | None = None
    exclusion_reason: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=2000)


class Adopt(Input):
    method: Literal['text', 'lora']
    adapter_id: str | None = None
    strength: float = Field(default=1.0, ge=0.0, le=2.0)
    note: str = Field(default='', max_length=500)
