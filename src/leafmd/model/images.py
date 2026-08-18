"""Provider-neutral image analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ImageDecision(StrEnum):
    """Whether a source raster can be replaced by semantic content."""

    PRESERVE = "preserve"
    REPLACE = "replace"


class ImageBlockKind(StrEnum):
    """Markdown-representable block types recovered from an image."""

    TEXT = "text"
    TABLE = "table"
    FORMULA = "formula"


@dataclass(frozen=True)
class ImageBlock:
    """One recovered semantic block in image reading order."""

    kind: ImageBlockKind
    content: str
    label: str


@dataclass(frozen=True)
class ImageAnalysis:
    """Normalized result from an external image analyzer."""

    source_href: str
    decision: ImageDecision
    blocks: tuple[ImageBlock, ...]
    labels: tuple[str, ...]
    reason: str
    backend: str
