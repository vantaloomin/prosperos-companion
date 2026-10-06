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


class RunCreate(Input):
    name: str = Field(min_length=1, max_length=80)
    # The word captions and prompts use to call up the character.
    trigger: str = Field(min_length=2, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    network: Literal['lokr', 'lora'] = 'lokr'
    rank: int = Field(default=16, ge=4, le=128)
    steps: int = Field(default=1500, ge=10, le=6000)
    learning_rate: float = Field(default=1e-4, gt=0, le=1e-2)
    save_every: int = Field(default=250, ge=5, le=2000)
    resolution: Literal[512, 1024] = 1024
    low_vram: bool = False
    attest_fictional_adult: bool = False
    accept_disclosure: bool = False

    def options(self) -> dict:
        return self.model_dump(include={'network', 'rank', 'steps', 'learning_rate', 'save_every', 'resolution',
                                        'low_vram'})


class KeepCheckpoint(Input):
    step: int = Field(ge=0)


class EvaluationCreate(Input):
    adapter_id: str
    strength: float = Field(default=1.0, ge=0.0, le=2.0)
    # Also render each prompt from the text description alone, for comparison.
    include_baseline: bool = True


class Rating(Input):
    rating: Literal['', 'good', 'weak']


class Shot(Input):
    key: str = Field(default='', max_length=40)
    label: str = Field(min_length=1, max_length=80)
    # What this picture shows; it follows the shared base description in the prompt.
    shot: str = Field(min_length=1, max_length=500)
    aspect: Literal['square', 'landscape', 'portrait'] = 'portrait'


class GenerationPlan(Input):
    # The description every shot starts from, so the set stays consistent.
    base: str = Field(min_length=1, max_length=1500)
    shots: list[Shot] = Field(min_length=1, max_length=40)
    marked_nsfw: bool = False
    # None follows the user's backend order; a backend the request is not eligible for is refused.
    backend_id: str | None = None
    seed: int | None = Field(default=None, ge=1, lt=2**31)


class GenerationCreate(GenerationPlan):
    seed: int = Field(ge=1, lt=2**31)


class PortraitPlan(Input):
    base: str = Field(min_length=1, max_length=1500)
    shots: list[Shot] = Field(min_length=1, max_length=3)
    backend_id: str | None = None
    # Make every picture from the description alone, for backends that cannot take a reference.
    without_reference: bool = False
    seed: int | None = Field(default=None, ge=1, lt=2**31)


class PortraitCreate(PortraitPlan):
    seed: int = Field(ge=1, lt=2**31)


class Portrait(Input):
    reference_id: str | None = None
