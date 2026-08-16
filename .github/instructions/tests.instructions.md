---
applyTo: "tests/**"
---

# Test review

## Layout

- Unit: `tests/unit/`
- Integration / synthetic EPUBs: `tests/integration/` + `tests/fixtures/epub_builder.py`
- Goldens (when added): `tests/golden/`
- Build EPUBs in-memory via the fixture builder. Do not vendor `.epub` binaries unless the ticket explicitly adds a tiny synthetic file.

## Required checks

- New behavior needs a test. Bug fixes need a regression test.
- Hostile-input tests (zip-slip, bombs, XXE, DRM, unsafe schemes, SVG script) are not optional when those paths change.
- Assert report **codes** (`LINK_UNRESOLVED`, `PLAN_NONLINEAR`, …), not only substrings of messages.
- Prefer `python -m pytest` selectors over whole-suite-only PRs.
- Tests must be deterministic. No network. No wall-clock sleeps. No home-directory writes.

```python
# Avoid
assert "could not resolve" in report_text

# Prefer
assert any(issue.code == "LINK_UNRESOLVED" for issue in report.issues)
```

## Goldens

- Do not approve or rewrite golden trees in the same PR that changes converter output unless the ticket is explicitly a golden update.
- CI must never pass `--update-goldens`.
- Normalize only documented volatile fields (e.g. `tool_version`).

## Fixtures

- One fixture family per ticket when possible (see implementation plan §9 batches).
- Characterization tests for planner B/C may fail on purpose. Do not “fix” them by implementing Phase 3 in a test PR.
- Never add copyrighted books or `LEAFMD_CORPUS` contents.

## Markers

Use existing/planned markers: `unit`, `synthetic`, `integration`, `golden`, `security`, `slow`, `online`, `private`, `differential`, `epubcheck`.

Default CI is `not online and not private and not differential and not epubcheck`. Do not mark required Phase 1 tests as `online` / `private`.
