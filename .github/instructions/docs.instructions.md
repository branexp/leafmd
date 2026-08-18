---
applyTo: "docs/**/*.md"
---

# Docs review

## Sources of truth

- Current behavior: implementation under `src/leafmd/` plus tests
- User-facing overview/CLI: `README.md`
- Pipeline/boundaries: `docs/architecture.md`
- Output contract: `docs/canonical-format.md`
- Security boundary: `docs/security.md`
- PR process: `docs/github-workflow.md`
- `docs/implementation-plan.md` is retained as historical planning context only; do not use old phase/ticket or privacy statements as current requirements.

## Writing rules

- Document **current** behavior, including the public repository and opt-in `--convert-images` path. Clearly label unimplemented work such as html5lib runtime recovery, EPUBCheck, recursive conversion, and a reading site.
- Distinguish source MathML preservation from OCR-derived formula-to-LaTeX conversion.
- Do not claim `convert` runs `validate` automatically.
- Do not claim ZIP-bomb/member-path limits or parse-based SVG sanitization while the code does not implement them.
- Keep commands copy-pasteable and aligned with CI (`uv run ruff`, `uv run mypy`, filtered `uv run python -m pytest`).
- Do not promise a public upload API, PyPI release, daemon, or website implementation.

## What to flag

- Stale private-repository or historical phase/ticket language presented as current policy
- Docs that describe planned behavior as shipped, or omit a shipped public CLI option
- Instructions that tell people to commit EPUBs/converted libraries/model caches
- Broken relative links between docs
- Security claims stronger than the current implementation or claims that canonical output is safe public HTML
