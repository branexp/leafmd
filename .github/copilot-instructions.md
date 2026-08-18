# leafmd Copilot code review

These rules apply to every pull request. Path-specific rules live in `.github/instructions/`.

leafmd is a **public repository for a local/personal-library CLI**. It compiles hostile EPUB 2/3 input into a regenerate-only Markdown book directory. It is not a website, upload service, or EPUB editor.

## Product invariants — flag violations

- EPUB is the source of truth. Generated output is regenerate-only; do not add an edit overlay or silently make caches/incremental state authoritative.
- Direct OPF/nav/NCX parsing is authoritative. Never use EbookLib `book.toc`, and do not import `ebooklib` above `leafmd.parse.ebooklib_adapter`.
- Planner case A remains the default, with the shipped conservative merge/split and virtual-TOC behavior preserved. Keep `linear="no"` as its own file and keep `PLAN_NONLINEAR` reporting.
- Compatibility anchors are explicit HTML `<a id="src-<stem>-<id>"></a>`. TOC/content fragments must use the same global `TargetMap`; do not substitute heading slugs or raw EPUB ids.
- Keep only `http`, `https`, `mailto`, and internal relative links. Drop unsafe/unknown schemes. Never fetch remote EPUB assets.
- Copy supported referenced image assets and the cover; unsupported media remains skipped/reported.
- Source MathML stays sanitized raw HTML. Optional OCR-derived formulas may be LaTeX only through the explicit image-analysis path.
- `--convert-images` stays opt-in. PaddleOCR remains an external executable/dependency, original assets stay copied, and analyzer failures must not destroy otherwise convertible books.
- `convert` and `validate` are separate operations; do not document or implement automatic validation unless that contract is deliberately changed.
- Converter output is **not** a public-HTML trust boundary.

## Security — treat as blocking

- Reject DRM/`META-INF/encryption.xml`; never add DRM bypass behavior.
- Keep XML entity resolution, DTD loading/validation, and parser network access disabled.
- Archive members are read in place, not extracted. Current ingest intentionally has no ZIP-bomb limits or member-path filter; do not claim those protections exist. If extraction or resource-budget policy is added later, review it as a new security boundary.
- Drop active HTML and event handlers; keep unsafe URL schemes out of emitted content.
- Preserve the existing SVG hardening and do not describe it as parse-based/full sanitization while it remains regex-based.
- Core conversion must not add network clients or remote-asset/model fetching. The opt-in external Paddle process is a separate boundary and may have backend-specific model/cache behavior outside leafmd.
- Generated output paths and validator-resolved links/TOC targets must stay inside the book directory.
- Never commit copyrighted EPUBs, converted personal libraries, `.corpus/`, `LEAFMD_CORPUS` trees, model caches, or secrets.

## Review style

- Be specific and actionable. Cite code/docs that establish the current contract.
- Prefer correctness, fidelity, and hostile-input safety over refactors.
- Use `README.md`, `docs/architecture.md`, `docs/canonical-format.md`, and `docs/security.md` as current documentation. `docs/implementation-plan.md` is historical planning context, not a frozen source of truth.
- Flag unrelated file churn, but do not require historical phase/ticket ids.
- Behavior/public-CLI changes should update `CHANGELOG.md`; release changes must keep both version declarations synchronized.

## Quality gate

PRs must stay green under the same commands as CI:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run python -m pytest -m "not online and not private and not differential and not epubcheck"
```

Default CI must not update goldens, access a private corpus, download models, or require optional external services.
