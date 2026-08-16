from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BookMetadata:
    title: str
    language: str | None = None
    authors: tuple[str, ...] = ()
    subtitle: str | None = None
    identifiers: tuple[str, ...] = ()
    publisher: str | None = None
    date: str | None = None
    rights: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Resource:
    id: str
    href: str
    media_type: str
    properties: frozenset[str] = field(default_factory=frozenset)
    content: bytes | None = None


@dataclass(frozen=True)
class SpineEntry:
    idref: str
    linear: bool
    href: str


@dataclass(frozen=True)
class NavNode:
    title: str
    href: str | None
    kind: str
    semantic_type: str | None = None
    children: tuple[NavNode, ...] = ()


@dataclass
class NormalizedPublication:
    schema_version: int
    metadata: BookMetadata
    epub_version: str
    package_path: str
    source_filename: str
    resources: dict[str, Resource]
    spine: list[SpineEntry]
    nav_toc: list[NavNode]
    ncx_toc: list[NavNode]
    landmarks: list[NavNode]
    guide: list[NavNode]
    cover_id: str | None = None
