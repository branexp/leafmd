# Contributing

This repo is a private personal-library tool: [`branexp/leafmd`](https://github.com/branexp/leafmd).

Branch off `main`, open a PR, squash-merge, delete the branch. Full process: [docs/github-workflow.md](docs/github-workflow.md).

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Checks

```bash
ruff check src tests
ruff format --check src tests
mypy
python -m pytest
```

Do not commit copyrighted EPUBs. Synthetic fixtures live under `tests/`. A private corpus, if any, belongs in `LEAFMD_CORPUS` or a gitignored directory.
