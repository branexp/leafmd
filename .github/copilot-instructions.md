# leafmd Copilot code review

These rules apply to every pull request. Path-specific rules live in `.github/instructions/`.

leafmd is a **private personal-library CLI**. It compiles hostile EPUB 2/3 input into a regenerate-only Markdown book directory. It is not a website, not a public upload service, and not an EPUB editor.

## Product invariants — flag violations

- EPUB is the source of truth. Output is regenerate-only. Do not add edit overlays, caches, or incremental convert.
- Our OPF / nav / NCX parse is authoritative. Never use EbookLib `book.toc`.
- Nothing above `leafmd.parse.ebooklib_adapter` may import `ebooklib`.
- Planner default remains case A (one spine XHTML → one Markdown file). The shipped P3 contract also supports evidence-ranked cases B/C and virtual TOC parts; preserve that contract and require an explicit ticket for any new planner behavior. Keep `linear="no"` as its own file.
- `linear="no"` stays as its own file and must emit `PLAN_NONLINEAR`. Do not drop it.
- Compatibility anchors are explicit HTML `<a id="src-<stem>-<id>"></a>`. Heading slugs / github-slugger ids are not the contract.
- TOC fragments in `toc.json` / `toc.md` must go through the same global target map as content links. Never emit raw EPUB ids.
- Allowed URL schemes: `http`, `https`, `mailto`, plus internal relative links. Drop `javascript:`, `data:`, `file:`, `vbscript:`, and unknown schemes.
- No network I/O during convert/inspect/validate. Do not fetch remote images.
- Copy referenced JPEG/PNG/GIF/WebP/SVG and the cover. Skip fonts/CSS/JS/audio/video/SMIL with `MEDIA_SKIPPED`.
- MathML stays raw HTML. No MathML→LaTeX in v1.
- Converter output is **not** a public-HTML trust boundary. Do not claim the site sanitizer is done here.

## Security — treat as blocking

- Reject zip-slip (`..`, absolute paths, backslash, drive letters).
- Enforce ingest caps (entry count, uncompressed size, member size, ratio).
- Reject `META-INF/encryption.xml` / DRM. Do not bypass DRM.
- XML parse: entity resolution off, no network, no DTD expansion.
- Drop `script`, `iframe`, `object`, `embed`, `form`, and `on*` handlers.
- Sanitize SVG: no script, no event attrs, no external http refs.
- Never commit copyrighted EPUBs, converted personal libraries, `.corpus/`, or `LEAFMD_CORPUS` trees.

## Review style

- Be specific and actionable. Cite the invariant or file.
- Prefer correctness and hostile-input safety over refactors.
- Do not request website, SWAG/DNS, PyPI, public GitHub, config files, or a daemon.
- Do not re-litigate frozen decisions in `docs/implementation-plan.md` §2.
- One §8 ticket per PR. Flag drive-by file changes outside the stated write-scope.
- Copilot reviews leave comments only. Do not try to block merge or rewrite the PR overview.

## Quality gate

PRs must stay green:

```bash
ruff check src tests
ruff format --check src tests
mypy
python -m pytest
```

CI must not update goldens. Golden refresh is an explicit local flag and a reviewed PR.
