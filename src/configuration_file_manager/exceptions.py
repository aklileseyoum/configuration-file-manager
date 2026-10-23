"""Custom exceptions. Every expected failure derives from ConfigError."""


class ConfigError(Exception):
    """Base class for all errors raised by this package."""


class ConfigNotFoundError(ConfigError):
    """The config file or folder does not exist."""


class ConfigAccessError(ConfigError):
    """The file exists but cannot be read or written."""


class UnsupportedFormatError(ConfigError):
    """The file extension has no registered handler."""


class ConfigParseError(ConfigError):
    """The file content is not valid for its format."""


class ConfigValidationError(ConfigError):
    """The entries do not match the schema."""
