# Security

Treat every EPUB as hostile.

## Ingest

- Reject `..`, absolute paths, and names that escape the archive root
- Limit entry count, uncompressed size, single-member size, and compression ratio
- Reject `META-INF/encryption.xml`
- Parse XML with entity resolution off and no network
- Do not extract the whole archive to disk

## Transform

- Rich XHTML trees drop `script`, `iframe`, `object`, `embed`, `form`, `base`, `applet`, `portal`, and `svg`; event handlers, `style`, and `srcdoc` are stripped
- Sanitize rich directionality to safe `dir="rtl|ltr|auto"`; remove unsafe URL-bearing attributes
- Allow `http`, `https`, `mailto`, and internal relative links
- Sanitize SVG assets separately (`script`, event attributes, foreign content, and external HTTP references)
- Never fetch remote assets

## Site

Astro / any HTML renderer must sanitize again. Converter output is not a public-HTML trust boundary.
