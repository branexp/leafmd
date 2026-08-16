"""Typed conversion failures."""

from __future__ import annotations


class LeafmdError(Exception):
    """Base error for leafmd."""


class UsageError(LeafmdError):
    """Invalid CLI usage."""


class FatalConversionError(LeafmdError):
    """Cannot produce a book directory."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class CompletedWithErrors(LeafmdError):
    """Conversion finished but recorded error-severity issues."""
