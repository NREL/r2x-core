"""Custom exceptions for r2x-core package."""


class R2XCoreError(Exception):
    """Base exception for all r2x-core errors."""


class ParserError(R2XCoreError):
    """Exception raised for parser-related errors."""


class ValidationError(R2XCoreError):
    """Exception raised for validation errors."""


class ComponentCreationError(R2XCoreError):
    """Exception raised when component creation fails."""


class ExporterError(R2XCoreError):
    """Exception raised for exporter-related errors."""


class UpgradeError(R2XCoreError):
    """Exception raised for upgrader-related errors."""


class ReaderError(R2XCoreError):
    """Exception raised for data reading related errors."""


class CLIError(R2XCoreError):
    """Error raised during CLI plugin execution."""
