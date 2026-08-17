"""Small, conservative text cleanups used by the Markdown renderer."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_DROP_CAP_MARKDOWN = re.compile(r"(?<![\w*])(?:\*{1,3}|_{1,3})([A-Za-z])(?:\*{1,3}|_{1,3})(?=[A-Za-z])")
_DROP_CAP_HTML = re.compile(
    r"<(?P<tag>span|b|strong)\b(?P<attrs>[^>]*)>(?P<char>[A-Za-z])</(?P=tag)>(?=[A-Za-z])",
    re.IGNORECASE,
)
_HYPHENATED_LINE = re.compile(r"\b([A-Za-z]{2,})-\s+([a-z]\w*)\b")
_HEADING = re.compile(r"(?m)^#{1,3}\s")
_LEADING_BOLD_TITLE = re.compile(r"\A\s*\*\*(?P<title>[^*\n]+?)\*\*\s*(?:\n|\Z)")
_INLINE_WHITESPACE = re.compile(r"[ \t\r\n\f\v]+")
_MOJIBAKE_STARTS = frozenset("ÃÂâð")


def normalize_text(text: str) -> str:
    """Apply conservative text repairs without rewriting spelling.

    Only recognizable UTF-8-after-single-byte-decoding sequences are repaired;
    legitimate characters such as ``â`` in a name or ``▪`` are preserved.
    """

    return join_line_hyphens(drop_caps(repair_mojibake(text)))


def collapse_inline_whitespace(text: str) -> str:
    """Turn source line wrapping inside prose into ordinary spaces."""

    return _INLINE_WHITESPACE.sub(" ", text)


def repair_mojibake(text: str) -> str:
    """Repair only byte sequences that unambiguously round-trip as UTF-8.

    A broad replacement of suspicious-looking Unicode would corrupt legitimate
    prose. This bounded heuristic handles common accidental UTF-8 → Windows
    single-byte → Unicode conversions (for example ``Ã©`` and ``Â ``) while
    leaving incomplete or ordinary words untouched.
    """

    for _ in range(2):
        repaired = _repair_mojibake_pass(text)
        if repaired == text:
            break
        text = repaired
    return text


def _repair_mojibake_pass(text: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(text):
        if text[index] not in _MOJIBAKE_STARTS:
            parts.append(text[index])
            index += 1
            continue
        replacement: str | None = None
        consumed = 0
        for width in range(min(4, len(text) - index), 1, -1):
            candidate = text[index : index + width]
            try:
                decoded = candidate.encode("cp1252").decode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue
            if decoded != candidate:
                replacement = decoded
                consumed = width
                break
        if replacement is None:
            parts.append(text[index])
            index += 1
        else:
            parts.append(replacement)
            index += consumed
    return "".join(parts)


def drop_caps(text: str) -> str:
    """Turn a glued, single-letter emphasis drop cap into an ordinary letter."""

    text = _DROP_CAP_MARKDOWN.sub(r"\1", text)

    def html_replacement(match: re.Match[str]) -> str:
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        if tag == "span" and not re.search(r'class\s*=\s*["\'][^"\']*\bdropcap\b', attrs, re.I):
            return match.group(0)
        return match.group("char")

    return _DROP_CAP_HTML.sub(html_replacement, text)


def join_line_hyphens(text: str) -> str:
    """Join end-of-line word hyphens, excluding title-like false positives."""

    def replacement(match: re.Match[str]) -> str:
        prefix, suffix = match.groups()
        # All-caps tokens are commonly Roman-numeral/title labels, not wraps.
        if prefix.isupper() or prefix == "Zodiac":
            return match.group(0)
        return prefix + suffix

    return _HYPHENATED_LINE.sub(replacement, text)


def promote_leading_bold_title(markdown: str) -> str:
    """Promote an initial bold-only paragraph when no ATX heading exists."""

    if _HEADING.search(markdown):
        return markdown
    match = _LEADING_BOLD_TITLE.match(markdown)
    if match is None:
        return markdown
    title = match.group("title").strip()
    rest = markdown[match.end() :].lstrip("\n")
    return f"# {title}\n\n{rest}" if rest else f"# {title}\n"


class _DescriptionParser(HTMLParser):
    """Render the small HTML subset allowed in OPF descriptions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._emphasis: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "br":
            self.parts.append("\n")
        elif tag == "p":
            self.parts.append("\n\n")
        elif tag in {"i", "em"}:
            self.parts.append("*")
            self._emphasis.append("*")
        elif tag in {"b", "strong"}:
            self.parts.append("**")
            self._emphasis.append("**")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"i", "em", "b", "strong"} and self._emphasis:
            self.parts.append(self._emphasis.pop())

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def description_to_markdown(description: str | None) -> str:
    """Convert simple OPF description HTML to compact Markdown."""

    if not description:
        return ""
    parser = _DescriptionParser()
    parser.feed(description)
    parser.close()
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
