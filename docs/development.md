# Development

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check src tests
ruff format --check src tests
mypy
python -m pytest
```

`python -m pytest` is the reliable invocation (puts the repo root on `sys.path`). Bare `pytest` also works because `tool.pytest.ini_options.pythonpath` includes `.`.

GitHub remote is private `branexp/leafmd`. Branch off `main` → PR → squash merge. Details: [github-workflow.md](github-workflow.md).

Synthetic EPUBs are built in `tests/fixtures/epub_builder.py`. Do not vendor copyrighted books. Optional private corpus: `LEAFMD_CORPUS`.
