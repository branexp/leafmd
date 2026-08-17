"""Small, conservative text cleanups used by the Markdown renderer."""

from __future__ import annotations

import re
from html.parser import HTMLParser

_DROP_CAP_MARKDOWN = re.compile(r"(?<![\w*])(?:\*\*|__)([A-Za-z])(?:\*\*|__)(?=[A-Za-z])")
_DROP_CAP_HTML = re.compile(
    r"<(?P<tag>span|b|strong)\b(?P<attrs>[^>]*)>(?P<char>[A-Za-z])</(?P=tag)>(?=[A-Za-z])",
    re.IGNORECASE,
)
_HYPHENATED_LINE = re.compile(r"\b([A-Za-z]{2,})-\s+([a-z]\w*)\b")
_HEADING = re.compile(r"(?m)^#{1,3}\s")
_LEADING_BOLD_TITLE = re.compile(r"\A\s*\*\*(?P<title>[^*\n]+?)\*\*\s*(?:\n|\Z)")


def normalize_text(text: str) -> str:
    """Apply only unambiguous typography repairs; never rewrite spelling."""

    return join_line_hyphens(drop_caps(text))


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
