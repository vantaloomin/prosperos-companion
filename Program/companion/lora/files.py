"""Files for the LoRA maker, kept in `lora/` beside the workspace database.

Adapters are checked as safetensors before they count: the header must be readable JSON and the
tensor data must end exactly where the file does. A truncated or partly written checkpoint fails
that check, so it is never offered for resume or adoption.
"""
import hashlib
import json
import shutil
import struct
from pathlib import Path

from companion.errors import DomainError

MAX_HEADER = 100 * 1024 * 1024
CHUNK = 1024 * 1024


def root(database) -> Path:
    path = database.path.parent / 'lora'
    path.mkdir(parents=True, exist_ok=True)
    return path


def folder(database, name: str) -> Path:
    path = root(database) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def inside(base: Path, name: str) -> Path:
    """A stored file name resolved inside its folder; anything that escapes it is refused."""
    resolved_base = base.resolve()
    path = (resolved_base / name).resolve()
    if resolved_base not in path.parents or not path.is_file():
        raise FileNotFoundError(name)
    return path


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


class InvalidAdapter(ValueError):
    pass


def read_header(path: Path) -> tuple[dict, int]:
    size = path.stat().st_size
    with path.open('rb') as handle:
        prefix = handle.read(8)
        if len(prefix) < 8:
            raise InvalidAdapter('the file is too short to be safetensors')
        length = struct.unpack('<Q', prefix)[0]
        if length <= 1 or length > MAX_HEADER or 8 + length > size:
            raise InvalidAdapter('the safetensors header length is not plausible')
        try:
            header = json.loads(handle.read(length))
        except (UnicodeDecodeError, ValueError) as error:
            raise InvalidAdapter('the safetensors header is not readable JSON') from error
    if not isinstance(header, dict):
        raise InvalidAdapter('the safetensors header is not an object')
    return header, size - 8 - length


def adapter_format(names: list[str]) -> str:
    if any('lokr_w1' in name or 'lokr_w2' in name for name in names):
        return 'lokr'
    if any(marker in name for name in names for marker in ('lora_A', 'lora_B', 'lora_down', 'lora_up')):
        return 'lora'
    return 'unknown'


def inspect_adapter(path: Path) -> dict:
    """Validate a safetensors adapter without loading its tensors."""
    header, data_bytes = read_header(path)
    metadata = header.pop('__metadata__', {}) or {}
    end = 0
    for name, tensor in header.items():
        offsets = tensor.get('data_offsets') if isinstance(tensor, dict) else None
        if not (isinstance(offsets, list) and len(offsets) == 2 and 0 <= offsets[0] <= offsets[1]):
            raise InvalidAdapter(f'tensor {name} has no valid data offsets')
        end = max(end, offsets[1])
    if not header:
        raise InvalidAdapter('the file holds no tensors')
    if end != data_bytes:
        raise InvalidAdapter('the tensor data does not end where the file does (incomplete or damaged)')
    names = list(header)
    return {'format': adapter_format(names), 'tensors': len(names), 'bytes': path.stat().st_size,
            'metadata': {key: str(value)[:2000] for key, value in metadata.items()} if isinstance(metadata, dict)
            else {}}


def require_adapter(path: Path) -> dict:
    try:
        return inspect_adapter(path)
    except (InvalidAdapter, OSError) as error:
        raise DomainError(f'This is not a usable safetensors adapter: {error}.', 422, 'invalid_adapter') from error


async def receive(stream, target: Path, limit: int) -> tuple[int, str]:
    """Write a request body to `target` through a partial file, returning its size and digest."""
    digest = hashlib.sha256()
    size = 0
    partial = target.with_name(target.name + '.partial')
    try:
        with partial.open('wb') as handle:
            async for chunk in stream:
                size += len(chunk)
                if size > limit:
                    raise DomainError(f'This file is larger than the {limit // (1024 * 1024)} MB limit.', 413)
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise DomainError('The file was empty.', 422)
        partial.replace(target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return size, digest.hexdigest()


def copy_verified(source: Path, target: Path) -> None:
    partial = target.with_name(target.name + '.partial')
    shutil.copyfile(source, partial)
    partial.replace(target)
