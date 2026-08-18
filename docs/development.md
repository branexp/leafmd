# Development

## Environment

Python 3.11+ is supported; `.python-version` selects 3.12 for the repository by default.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Quality gate

Use the CI-equivalent commands:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run python -m pytest -m "not online and not private and not differential and not epubcheck"
```

`python -m pytest` is the preferred pytest entry point because it behaves consistently with the configured project path. Focused selectors are encouraged while developing; run the CI-equivalent gate before opening or merging a PR.

## Tests and optional integrations

Synthetic EPUBs are built in `tests/fixtures/epub_builder.py`; integration tests live in `tests/integration/` and focused behavior tests in `tests/unit/`. Do not vendor copyrighted books or generated personal-library trees. Optional private corpus data belongs under `LEAFMD_CORPUS` or another gitignored path.

PaddleOCR is not a leafmd or dev dependency. Image-analysis unit/integration coverage should use normalized PP-StructureV3 fixtures, fakes, or mocks unless a test is explicitly designed for a locally provisioned external executable. Default CI must not download models or require Paddle.

The repository is public at `branexp/leafmd`. Branch off `main`, open a focused PR, let CI pass, and squash-merge. Details: [github-workflow.md](github-workflow.md).
