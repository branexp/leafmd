# Security

Treat every EPUB as hostile input. Leafmd's converter-side protections reduce risk and preserve a deterministic local output format; they are not a general HTML-sanitization guarantee.

## Archive and XML boundary

- Reject invalid ZIP input and reject EPUBs containing `META-INF/encryption.xml`; leafmd does not bypass DRM.
- Read archive members directly with `zipfile`; leafmd does not extract EPUB member names to the filesystem.
- Current ingest intentionally has **no** ZIP entry-count, uncompressed-size, member-size, compression-ratio, or archive-member-path filtering policy. Do not document such limits unless code adds them.
- XML uses lxml with entity resolution, DTD loading/validation, and network access disabled; `huge_tree` is off. Spine content falls back from the XML parser to lxml HTML recovery when needed.
- Generated paths come from normalized metadata/plans and slugified names rather than raw archive paths. The independent validator also rejects generated relative links/TOC targets that escape the book directory.

## XHTML, links, and assets

- Source-tree rewriting drops active elements including `script`, `iframe`, `object`, `embed`, and `form`, and strips event-handler attributes.
- Rich-content sanitization additionally removes `base`, `applet`, `portal`, and embedded `svg`; strips `style`/`srcdoc`; constrains `dir` to `ltr|rtl|auto`; and removes unsafe URL-bearing attributes.
- Internal links are rewritten through `TargetMap`. External links keep only `http`, `https`, and `mailto`; unsafe/unknown schemes are dropped.
- Remote raster assets are never fetched. Referenced local JPEG/PNG/GIF/WebP/SVG assets and the cover may be copied.
- SVG copying currently uses conservative regex-based removal of scripts, `foreignObject`, event/handler attributes, and external/active hrefs. This is not a complete parse-based SVG sanitizer.

## Optional image analyzer boundary

`--convert-images` is opt-in and executes the `paddleocr` program found on `PATH`. Leafmd stages only already-copied eligible raster images in a temporary directory, consumes PP-StructureV3 JSON, and preserves originals when results are visual/ambiguous/unsafe or when analysis fails after startup.

PaddleOCR is an external process and is **not sandboxed by leafmd**. Leafmd does not install Paddle or download models, but a user's Paddle installation may use its own model cache or perform downloads depending on how it is provisioned. Environments requiring strict no-network execution should pre-provision the backend and enforce isolation outside leafmd.

Recovered table HTML is re-parsed with lxml (`no_network=True`), reduced to an allowlist, stripped of attributes except bounded table spans, and rejected if it cannot be represented safely. This does not make arbitrary analyzer output trusted HTML.

## Output / site boundary

The generated book directory is not safe public HTML by definition. Any website or HTML renderer must apply its own independent sanitization and content-security policy.
