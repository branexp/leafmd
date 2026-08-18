"""Optional image-to-semantic-content analysis boundary."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from leafmd.model.images import ImageAnalysis


class ImageAnalyzer(Protocol):
    """Batch image analyzer. Implementations may live outside leafmd's environment."""

    backend: str

    def analyze_batch(self, images: Mapping[str, Path]) -> dict[str, ImageAnalysis]: ...


class ImageAnalyzerError(RuntimeError):
    """An optional image analyzer failed after it was successfully configured."""


__all__ = ["ImageAnalyzer", "ImageAnalyzerError"]
