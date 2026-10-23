"""High-level operations: discover, load, validate, convert, transaction."""

import logging
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from configuration_file_manager.exceptions import (
    ConfigAccessError,
    ConfigNotFoundError,
    ConfigValidationError,
    UnsupportedFormatError,
)
from configuration_file_manager.handlers import (
    CsvHandler,
    FormatHandler,
    JsonHandler,
    XmlHandler,
)
from configuration_file_manager.schema import ConfigEntry

logger = logging.getLogger(__name__)

HANDLERS: dict[str, FormatHandler] = {
    ".json": JsonHandler(),
    ".csv": CsvHandler(),
    ".xml": XmlHandler(),
}


def get_handler(path: Path) -> FormatHandler:
    """Pick the handler from the file extension."""
    try:
        return HANDLERS[path.suffix.lower()]
    except KeyError:
        raise UnsupportedFormatError(
            f"Unsupported format '{path.suffix}'. Supported: {', '.join(HANDLERS)}"
        ) from None


def discover(directory: Path, recursive: bool = True) -> list[Path]:
    """Find every supported config file in a folder."""
    if not directory.is_dir():
        raise ConfigNotFoundError(f"Folder not found: {directory}")
    pattern = directory.rglob("*") if recursive else directory.glob("*")
    return sorted(p for p in pattern if p.is_file() and p.suffix.lower() in HANDLERS)


def iter_config(path: Path) -> Iterator[ConfigEntry]:
    """Stream entries from a file one at a time (generator)."""
    if not path.exists():
        raise ConfigNotFoundError(f"File not found: {path}")
    try:
        yield from get_handler(path).iter_entries(path)
    except (PermissionError, IsADirectoryError) as err:
        raise ConfigAccessError(f"Cannot read {path}") from err


def load_config(path: Path) -> list[ConfigEntry]:
    """Load all entries into memory."""
    return list(iter_config(path))


def validate_config(path: Path) -> int:
    """Check the whole file against the schema and return the entry count.

    Also rejects duplicate (section, key) pairs.
    """
    seen: set[tuple[str, str]] = set()
    count = 0
    for entry in iter_config(path):
        pair = (entry["section"], entry["key"])
        if pair in seen:
            raise ConfigValidationError(f"Duplicate key {pair[0]}.{pair[1]} in {path}")
        seen.add(pair)
        count += 1
    return count


@contextmanager
def config_transaction(target: Path) -> Iterator[Path]:
    """Write to a temporary file; replace the target only if the block succeeds.

    If an error happens, the original file is left untouched.
    """
    temp = target.with_name(target.name + ".tmp")
    try:
        yield temp
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def backup_version(path: Path) -> Path | None:
    """Copy an existing file to `<name>.<timestamp>.bak` and return the copy."""
    if not path.exists():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    backup = path.with_name(f"{path.name}.{stamp}.bak")
    shutil.copy2(path, backup)
    return backup


def _normalize(entry: ConfigEntry) -> ConfigEntry:
    return ConfigEntry(
        section=entry["section"].lower(), key=entry["key"].lower(), value=entry["value"]
    )


def convert(source: Path, destination: Path) -> int:
    """Convert a config file to another format; return the number of entries.

    Functional pipeline: stream -> filter(non-empty value) -> map(normalize).
    An existing destination is backed up first, and the write is transactional.
    """
    handler_out = get_handler(destination)
    entries = map(_normalize, filter(lambda e: e["value"] != "", iter_config(source)))
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup_version(destination)
        with config_transaction(destination) as temp:
            written = list(entries)
            handler_out.write(written, temp)
    except PermissionError as err:
        raise ConfigAccessError(f"Cannot write {destination}") from err
    logger.info("Converted %s -> %s (%d entries)", source, destination, len(written))
    return len(written)
