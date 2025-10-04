"""Custom exceptions for r2x-core package."""


class R2XCoreError(Exception):
    """Base exception for all r2x-core errors."""

    pass


class ParserError(R2XCoreError):
    """Exception raised for parser-related errors.

    This exception is raised when there are issues during the parsing
    and system building process, such as invalid data, missing required
    files, or configuration errors.

    Parameters
    ----------
    message : str
        Description of the error.

    Examples
    --------
    >>> raise ParserError("Required file 'buses.csv' not found in data store")
    """

    pass


class ValidationError(R2XCoreError):
    """Exception raised for validation errors.

    This exception is raised when data or configuration validation fails,
    such as invalid years, missing required fields, or constraint violations.

    Parameters
    ----------
    message : str
        Description of the validation error.

    Examples
    --------
    >>> raise ValidationError("Model year 2019 not found in available years: [2020, 2025, 2030]")
    """

    pass


class ComponentCreationError(R2XCoreError):
    """Exception raised when component creation fails.

    This exception is raised when there are issues creating component instances,
    such as invalid field values or type mismatches.

    Parameters
    ----------
    message : str
        Description of the component creation error.

    Examples
    --------
    >>> raise ComponentCreationError("Failed to create Bus: missing required field 'voltage'")
    """

    pass
