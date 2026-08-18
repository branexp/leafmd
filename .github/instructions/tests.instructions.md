---
applyTo: "tests/**"
---

# Test review

## Layout

- Unit: `tests/unit/`
- Integration / synthetic EPUBs: `tests/integration/` + `tests/fixtures/epub_builder.py`
- Goldens (if/when added): `tests/golden/`
- Build EPUBs in memory through the fixture builder; do not vendor copyrighted `.epub` binaries.

## Required checks

- New behavior needs a test; bug fixes need a regression test.
- When hostile-input paths change, cover the protections the code actually has: invalid ZIP, DRM/encryption, XML entities/DTD/network, unsafe URL schemes/active HTML, SVG hardening, and generated-output path escapes as applicable.
- Do not require tests for nonexistent ZIP-bomb/member-path filters unless code deliberately introduces that policy.
- Assert stable report **codes** (`LINK_UNRESOLVED`, `PLAN_NONLINEAR`, `IMAGE_ANALYSIS_FAILED`, …), not only message substrings.
- Prefer focused `python -m pytest` selectors while developing; keep the CI marker filter green before merge.
- Tests must be deterministic: no network, wall-clock sleeps, home-directory writes, implicit model downloads, or dependence on a private corpus.

```python
# Avoid
assert "could not resolve" in report_text

# Prefer
assert any(issue.code == "LINK_UNRESOLVED" for issue in report.issues)
```

## Optional image analysis

- Parser/decision tests should use PP-StructureV3-shaped JSON fixtures or direct normalized results.
- Pipeline tests should inject a fake `ImageAnalyzer`; do not require PaddleOCR to be installed in default CI.
- Subprocess-adapter tests must mock/stub execution unless explicitly marked for a provisioned external environment.
- Cover visual/unknown labels, tables/formulas/text, inline-context preservation, analyzer failure/missing result, original-asset retention, and report counters when behavior changes.

## Goldens and fixtures

- Do not approve/rewrite golden trees in the same PR that changes converter output unless the PR is explicitly a reviewed golden update.
- CI must never update goldens.
- Normalize only documented volatile fields such as `tool_version`.
- Planner merge/split behavior is shipped and must continue to pass.
- Never add copyrighted books, converted library trees, `LEAFMD_CORPUS` contents, or model caches.

## Markers

Registered markers are `unit`, `synthetic`, `integration`, `golden`, `security`, `slow`, `online`, `private`, `differential`, and `epubcheck`.

Default CI uses `not online and not private and not differential and not epubcheck`.
