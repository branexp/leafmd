# Changelog

## 0.2.0 — 2026-08-16

Phase 3 semantic reconstruction.

- Cover discovery: EPUB2 meta, EPUB3 `cover-image`, OPF guide (`cover` / `other.ms-coverimage-standard`), then manifest ids `cover` / `coverimagestandard`. XHTML cover pages follow the first local image. Warn `COVER_MISSING` when a guide cover cannot resolve.
- Evidence-ranked classification: `epub:type` > landmark > nav > guide > NCX > headings > filename/id. New types: `cover`, `about-author`, `other`. Book-title-only and `.` titles are not classified as `chapter`.
- Planner cases B/C: merge only explicit split-file continuations such as `ch01a`/`ch01b` and `in1`/`in1_b`; split one XHTML with multiple fragment-targeted chapter headings. Virtual parts stay TOC-only (`section_id: null`). TOC is nav ∪ NCX (nav titles win), with legacy HTML TOC fallback when usable EPUB navigation is absent. Overlapping nav+NCX fragments are not sliced twice.
- Classification safeguards: numbered primary chapter titles are not reclassified by later subsection headings, and HTML TOC documents are labeled `other` with a stable “Table of Contents” title when needed.
- Text cleanup: drop-cap `**T**hen` and combined-style `***T**hunder` → `Then` / `Thunder`, end-of-line hyphen joins (`seclu- sive` → `seclusive`, not `Zodiac- and`), promote a leading bold title to ATX when no heading exists, convert simple OPF description HTML in `index.md`. No OCR rewriting.
- Phase 4 rich-content reconstruction: conservative GFM tables and local footnotes; raw-HTML fallback for complex tables and cross-document notes; preservation of MathML, ruby, and bidi markup; synthetic fixtures, deterministic conversion checks, and output validation for rich content.

## 0.1.0 — 2026-08-16

- Initial private Phase 1 vertical slice: EPUB 2/3 → canonical Markdown book directory.
- Commands: `convert`, `inspect`, `validate`, `report`.
- Phase 2: fragment/duplicate-id map, scheme filter, hostile SVG sanitize, asset name collisions, validator schema/TOC-anchor checks.
