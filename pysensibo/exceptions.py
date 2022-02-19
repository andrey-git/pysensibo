"""Exceptions for Sensibo."""

from typing import Any


class SensiboError(Exception):
    """Error from Sensibo api."""

    def __init__(self, *args: Any) -> None:
        """Initialize the exception."""
        Exception.__init__(self, *args)


class AuthenticationError(Exception):
    """Authentication issue from Sensibo api."""

    def __init__(self, *args: Any) -> None:
        """Initialize the exception."""
        Exception.__init__(self, *args)
