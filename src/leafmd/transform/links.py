"""Build and apply the source-href → output path/anchor map."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from leafmd.model.issues import IssueSeverity
from leafmd.model.publication import NormalizedPublication
from leafmd.model.report import ConversionReport
from leafmd.model.section import OutputTarget, SectionPlan
from leafmd.parse.hrefs import posix_join, split_fragment
from leafmd.parse.xmlutil import attr, local_name
from leafmd.transform.slug import slugify

ALLOWED_SCHEMES = {"http", "https", "mailto"}


@dataclass
class TargetMap:
    by_href: dict[tuple[str, str | None], OutputTarget]

    def resolve(self, source_href: str, href: str) -> OutputTarget | None:
        if href.startswith("#"):
            path, _ = split_fragment(source_href)
            return self.by_href.get((path, href[1:] or None))
        joined = posix_join(source_href, href)
        path, fragment = split_fragment(joined)
        if fragment:
            return self.by_href.get((path, fragment)) or self.by_href.get((path, None))
        return self.by_href.get((path, None))

    def resolve_abs(self, href: str) -> OutputTarget | None:
        path, fragment = split_fragment(href)
        if fragment:
            return self.by_href.get((path, fragment)) or self.by_href.get((path, None))
        return self.by_href.get((path, None))


def build_target_map(
    publication: NormalizedPublication,
    plans: list[SectionPlan],
) -> TargetMap:
    mapping: dict[tuple[str, str | None], OutputTarget] = {}
    used_anchors: set[str] = set()
    for plan in plans:
        if plan.role != "file" or not plan.output_path:
            continue
        for source in plan.sources:
            path, fragment = split_fragment(source.href)
            mapping[(path, None)] = OutputTarget(path=plan.output_path, anchor=None)
            if fragment:
                mapping[(path, fragment)] = OutputTarget(path=plan.output_path, anchor=None)
            resource = next(
                (item for item in publication.resources.values() if item.href == path),
                None,
            )
            if resource is None or resource.content is None:
                continue
            from leafmd.parse.html import parse_document

            try:
                root = parse_document(resource.content)
            except Exception:  # noqa: BLE001
                continue
            stem = slugify(path.rsplit("/", 1)[-1].rsplit(".", 1)[0], fallback="doc")
            for node in root.iter():
                node_id = attr(node, "id")
                if not node_id:
                    continue
                anchor = _unique_anchor(f"src-{stem}-{slugify(node_id, fallback='id')}", used_anchors)
                mapping[(path, node_id)] = OutputTarget(path=plan.output_path, anchor=anchor)
    return TargetMap(by_href=mapping)


def _unique_anchor(base: str, used: set[str]) -> str:
    candidate = base
    n = 2
    while candidate in used:
        candidate = f"{base}-{n}"
        n += 1
    used.add(candidate)
    return candidate


def rewrite_tree(
    root: etree._Element,
    source_href: str,
    targets: TargetMap,
    asset_map: dict[str, str],
    report: ConversionReport,
    section_path: str,
) -> None:
    for node in list(root.iter()):
        tag = local_name(getattr(node, "tag", ""))
        if tag in {"script", "iframe", "object", "embed", "form"}:
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            continue
        _strip_event_handlers(node)
        if tag == "a":
            href = attr(node, "href")
            if href is None:
                continue
            rewritten = _rewrite_href(href, source_href, targets, report, section_path)
            if rewritten is None:
                node.attrib.pop("href", None)
            else:
                node.set("href", rewritten)
        if tag == "img":
            src = attr(node, "src")
            if src is None:
                continue
            new_src = _rewrite_asset(src, source_href, asset_map, report)
            if new_src is None:
                node.attrib.pop("src", None)
            else:
                node.set("src", new_src)


def _strip_event_handlers(node: etree._Element) -> None:
    for key in list(node.attrib):
        if key.lower().startswith("on"):
            del node.attrib[key]


def _rewrite_href(
    href: str,
    source_href: str,
    targets: TargetMap,
    report: ConversionReport,
    section_path: str,
) -> str | None:
    parsed_scheme = href.split(":", 1)[0].lower() if ":" in href and not href.startswith("#") else ""
    if parsed_scheme and parsed_scheme not in ALLOWED_SCHEMES and "://" in href:
        report.add(
            IssueSeverity.WARNING,
            "LINK_SCHEME_DROPPED",
            f"Dropped unsafe URL scheme: {href}",
            where=source_href,
        )
        return None
    if parsed_scheme in ALLOWED_SCHEMES:
        return href
    target = targets.resolve(source_href, href)
    if target is None:
        report.add(
            IssueSeverity.WARNING,
            "LINK_UNRESOLVED",
            f"Could not resolve internal link: {href}",
            where=source_href,
        )
        report.stats.unresolved_links += 1
        return "#"
    dest = _relative_to(section_path, target.path)
    if target.anchor:
        return f"{dest}#{target.anchor}"
    return dest


def _rewrite_asset(
    src: str,
    source_href: str,
    asset_map: dict[str, str],
    report: ConversionReport,
) -> str | None:
    if src.startswith(("http://", "https://")):
        report.add(
            IssueSeverity.WARNING,
            "ASSET_REMOTE",
            f"Remote image not fetched: {src}",
            where=source_href,
        )
        return None
    joined, _fragment = split_fragment(posix_join(source_href, src))
    mapped = asset_map.get(joined)
    if mapped is None:
        report.add(
            IssueSeverity.WARNING,
            "ASSET_MISSING",
            f"Referenced asset not copied: {joined}",
            where=source_href,
        )
        return None
    return mapped


def _relative_to(from_path: str, to_path: str) -> str:
    from_parts = from_path.split("/")[:-1]
    to_parts = to_path.split("/")
    while from_parts and to_parts and from_parts[0] == to_parts[0]:
        from_parts.pop(0)
        to_parts.pop(0)
    return "/".join([".."] * len(from_parts) + to_parts)
