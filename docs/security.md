# Security

Treat every EPUB as hostile.

## Ingest

- Reject `..`, absolute paths, and names that escape the archive root
- Limit entry count, uncompressed size, single-member size, and compression ratio
- Reject `META-INF/encryption.xml`
- Parse XML with entity resolution off and no network
- Do not extract the whole archive to disk

## Transform

- Drop `script`, `iframe`, `object`, `embed`, `form`, and event handlers
- Allow `http`, `https`, `mailto`, and internal relative links
- Sanitize SVG (`script`, event attributes, external http refs)
- Never fetch remote assets

## Site

Astro / any HTML renderer must sanitize again. Converter output is not a public-HTML trust boundary.
