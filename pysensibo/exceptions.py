"""Exceptions for Sensibo."""

from __future__ import annotations

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


class StreamUnavailableError(SensiboError):
    """The event stream is not available now.

    retry_after: seconds to wait before the next attempt, if the API gave them.
    """

    def __init__(self, *args: Any, retry_after: float | None = None) -> None:
        """Initialize the exception."""
        SensiboError.__init__(self, *args)
        self.retry_after = retry_after
