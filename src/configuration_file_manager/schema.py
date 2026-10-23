"""Config schema: a flat list of entries grouped by section."""

from typing import TypedDict

from configuration_file_manager.exceptions import ConfigValidationError


class ConfigEntry(TypedDict):
    """One setting. Example: section="database", key="port", value="5432"."""

    section: str
    key: str
    value: str


REQUIRED_FIELDS: tuple[str, ...] = ("section", "key", "value")


def validate_entry(raw: object) -> ConfigEntry:
    """Return a clean ConfigEntry or raise ConfigValidationError."""
    if not isinstance(raw, dict):
        raise ConfigValidationError(
            f"Entry must be an object, got {type(raw).__name__}"
        )
    missing = [f for f in REQUIRED_FIELDS if f not in raw]
    if missing:
        raise ConfigValidationError(f"Entry is missing fields: {', '.join(missing)}")
    section, key, value = (str(raw[f]).strip() for f in REQUIRED_FIELDS)
    if not section or not key:
        raise ConfigValidationError("'section' and 'key' must not be empty")
    return ConfigEntry(section=section, key=key, value=value)
