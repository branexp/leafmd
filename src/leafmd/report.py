"""Shared report helpers."""

from __future__ import annotations

from leafmd import __version__
from leafmd.model.report import ConversionReport


def new_report() -> ConversionReport:
    return ConversionReport(status="ok", tool_version=__version__)
