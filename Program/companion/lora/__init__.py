"""Character LoRA maker: references, adapters, training, evaluation and appearance versions."""
import os

# The LoRA creator is hidden unless this is set (1, true, yes or on); see docs/lora.md.
MAKER_ENV = 'COMPANION_LORA_MAKER'


def maker_enabled() -> bool:
    return os.environ.get(MAKER_ENV, '').strip().lower() in {'1', 'true', 'yes', 'on'}
