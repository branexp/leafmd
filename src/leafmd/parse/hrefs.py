"""POSIX package-relative href joining. No filesystem traversal."""

from __future__ import annotations

from urllib.parse import unquote, urlparse


def split_fragment(href: str) -> tuple[str, str | None]:
    if "#" not in href:
        return href, None
    path, fragment = href.split("#", 1)
    return path, fragment or None


def posix_join(base: str, rel: str) -> str:
    """Join a package-relative base file with a relative href, preserving fragments."""
    parsed = urlparse(rel)
    if parsed.scheme or parsed.netloc:
        return rel
    rel_path, fragment = split_fragment(rel)
    rel_path = unquote(rel_path)
    if not rel_path:
        joined = posix_norm(base)
    elif rel_path.startswith("/"):
        joined = posix_norm(rel_path.lstrip("/"))
    else:
        base_dir = base.rsplit("/", 1)[0] if "/" in base else ""
        parts = [part for part in base_dir.split("/") if part] if base_dir else []
        for part in rel_path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        joined = "/".join(parts)
    if fragment:
        return f"{joined}#{fragment}"
    return joined


def posix_norm(path: str) -> str:
    parts: list[str] = []
    for part in path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)
