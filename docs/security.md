# Security

Treat every EPUB as hostile.

## Ingest

- Reject malformed ZIP/EPUB archives
- Reject `META-INF/encryption.xml`
- Read package members directly; never extract archive names to the filesystem
- Parse XML with entity resolution off and no network

This private-library tool intentionally does not impose ZIP-bomb size/count or
archive-member path filters. It does not use member names as output paths. The
generated book directory is produced from normalized package metadata and
slugified output names.

## Transform

- Rich XHTML trees drop `script`, `iframe`, `object`, `embed`, `form`, `base`, `applet`, `portal`, and `svg`; event handlers, `style`, and `srcdoc` are stripped
- Sanitize rich directionality to safe `dir="rtl|ltr|auto"`; remove unsafe URL-bearing attributes
- Allow `http`, `https`, `mailto`, and internal relative links
- Sanitize SVG assets separately (`script`, event attributes, foreign content, and external HTTP references)
- Never fetch remote assets

## Site

Astro / any HTML renderer must sanitize again. Converter output is not a public-HTML trust boundary.
