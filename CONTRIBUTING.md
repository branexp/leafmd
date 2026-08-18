# Contributing

`leafmd` is a public repository for a local/personal-library EPUB-to-Markdown CLI: [`branexp/leafmd`](https://github.com/branexp/leafmd).

Use a focused branch, open a PR into `main`, let CI pass, then squash-merge and delete the branch. See [docs/github-workflow.md](docs/github-workflow.md).

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## CI-equivalent checks

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run python -m pytest -m "not online and not private and not differential and not epubcheck"
```

Run broader or focused pytest selectors locally when appropriate. Tests for optional external analyzers should use deterministic fakes/mocks by default rather than requiring PaddleOCR model downloads or network access.

Behavior or public-CLI changes should update `CHANGELOG.md` (use `Unreleased` until a release is cut). Release PRs must keep `pyproject.toml` and `src/leafmd/__init__.py` versions identical. Documentation-only changes do not require a version bump.

Do not commit copyrighted EPUBs or converted personal-library trees. Synthetic fixtures live under `tests/`. A private corpus, if any, belongs in `LEAFMD_CORPUS` or another gitignored directory.
