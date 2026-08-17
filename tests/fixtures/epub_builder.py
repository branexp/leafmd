"""Minimal EPUB 2/3 builders for tests. Not a general authoring tool."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

MIN_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

MIN_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect width="1" height="1"/></svg>'

HOSTILE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" '
    b'xmlns:xlink="http://www.w3.org/1999/xlink" width="1" height="1">'
    b"<script>alert(1)</script>"
    b'<rect width="1" height="1" onclick="alert(1)" handler="evil()"/>'
    b'<a xlink:href="https://evil.example/x" href="javascript:alert(1)"/>'
    b'<foreignObject width="1" height="1">'
    b'<body xmlns="http://www.w3.org/1999/xhtml"><script>alert(2)</script></body>'
    b"</foreignObject></svg>"
)

CONTAINER_XML = b"""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _write_epub(members: dict[str, bytes], *, compress_all: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, members["mimetype"])
        for name, data in members.items():
            if name == "mimetype":
                continue
            compress = zipfile.ZIP_DEFLATED if compress_all or name != "mimetype" else zipfile.ZIP_STORED
            archive.writestr(name, data, compress_type=compress)
    return buffer.getvalue()


def write_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _xhtml(title: str, body: str) -> bytes:
    return (
        '<?xml version="1.0"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        f"<head><title>{title}</title></head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    ).encode()


def make_epub3(*, with_image: bool = True, broken_link: bool = False) -> bytes:
    ch2_href = "missing.xhtml#nope" if broken_link else "ch01.xhtml#p1"
    image_item = (
        '    <item id="cover" href="images/cover.png" media-type="image/png" properties="cover-image"/>\n'
        '    <item id="pic" href="images/pic.svg" media-type="image/svg+xml"/>\n'
        if with_image
        else ""
    )
    img_tag = '<p><img src="images/pic.svg" alt="dot"/></p>' if with_image else ""
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
        "EPUB/content.opf": f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:leafmd-epub3</dc:identifier>
    <dc:title>Sample EPUB 3</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:description>A tiny fixture book.</dc:description>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ch01" href="ch01.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch02" href="ch02.xhtml" media-type="application/xhtml+xml"/>
{image_item}  </manifest>
  <spine>
    <itemref idref="ch01"/>
    <itemref idref="ch02"/>
  </spine>
</package>
""".encode(),
        "EPUB/nav.xhtml": b"""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head><title>Nav</title></head>
  <body>
    <nav epub:type="toc">
      <ol>
        <li><a href="ch01.xhtml">Chapter 1 Welcome</a></li>
        <li><a href="ch02.xhtml">Chapter 2 Next</a></li>
      </ol>
    </nav>
  </body>
</html>
""",
        "EPUB/ch01.xhtml": f"""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body>
    <h1 id="welcome">Chapter 1 Welcome</h1>
    <p id="p1">Hello from chapter one.</p>
    {img_tag}
  </body>
</html>
""".encode(),
        "EPUB/ch02.xhtml": f"""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 2</title></head>
  <body>
    <h1>Chapter 2 Next</h1>
    <p>See <a href="{ch2_href}">the first paragraph</a>.</p>
  </body>
</html>
""".encode(),
    }
    if with_image:
        members["EPUB/images/cover.png"] = MIN_PNG
        members["EPUB/images/pic.svg"] = MIN_SVG
    return _write_epub(members)


def make_epub2() -> bytes:
    return _write_epub(
        {
            "mimetype": b"application/epub+zip",
            "META-INF/container.xml": b"""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
            "OEBPS/content.opf": b"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:identifier id="bookid">urn:uuid:leafmd-epub2</dc:identifier>
    <dc:title>Sample EPUB 2</dc:title>
    <dc:creator opf:role="aut">Legacy Author</dc:creator>
    <dc:language>en</dc:language>
    <meta name="cover" content="cover"/>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="ch01" href="ch01.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="cover.png" media-type="image/png"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="ch01"/>
  </spine>
  <guide>
    <reference type="text" title="Start" href="ch01.xhtml"/>
  </guide>
</package>
""",
            "OEBPS/toc.ncx": b"""<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:leafmd-epub2"/>
  </head>
  <docTitle><text>Sample EPUB 2</text></docTitle>
  <navMap>
    <navPoint id="np1" playOrder="1">
      <navLabel><text>Only Chapter</text></navLabel>
      <content src="ch01.xhtml"/>
    </navPoint>
  </navMap>
</ncx>
""",
            "OEBPS/ch01.xhtml": b"""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Only Chapter</title></head>
  <body>
    <h1>Only Chapter</h1>
    <p>EPUB 2 body text.</p>
    <p><img src="cover.png" alt="cover"/></p>
  </body>
</html>
""",
            "OEBPS/cover.png": MIN_PNG,
        }
    )


def make_guide_cover_book(*, xhtml_cover: bool = False, jpeg: bool = False) -> bytes:
    """Build an EPUB whose only cover declaration is an OPF guide reference."""
    image_name = "cover.jpg" if jpeg else "cover.png"
    image_type = "image/jpeg" if jpeg else "image/png"
    cover_href = "cover.xhtml" if xhtml_cover else image_name
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
        "EPUB/content.opf": f'''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Guide Cover</dc:title></metadata>
  <manifest>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover-doc" href="cover.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover-image" href="{image_name}" media-type="{image_type}"/>
  </manifest>
  <spine><itemref idref="chapter"/></spine>
  <guide><reference type="cover" title="Front Cover" href="{cover_href}"/></guide>
</package>
'''.encode(),
        "EPUB/chapter.xhtml": _xhtml("Chapter", "<h1>Chapter</h1><p>Text.</p>"),
        "EPUB/cover.xhtml": _xhtml("Cover", f'<img src="{image_name}" alt="cover"/>'),
        f"EPUB/{image_name}": MIN_JPEG if jpeg else MIN_PNG,
    }
    return _write_epub(members)


def make_zip_slip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("../evil.txt", "nope")
        archive.writestr("META-INF/container.xml", CONTAINER_XML)
    return buffer.getvalue()


def make_drm() -> bytes:
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
        "META-INF/encryption.xml": b"""<?xml version="1.0"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"/>
""",
        "EPUB/content.opf": b"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">drm</dc:identifier>
    <dc:title>DRM</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="ch01" href="ch01.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch01"/>
  </spine>
</package>
""",
        "EPUB/ch01.xhtml": b"<html xmlns='http://www.w3.org/1999/xhtml'><body><p>x</p></body></html>",
    }
    return _write_epub(members)


def make_xxe() -> bytes:
    evil = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>&xxe;</p></body></html>
"""
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
        "EPUB/content.opf": b"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">xxe</dc:identifier>
    <dc:title>XXE</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="ch01" href="ch01.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="ch01"/>
  </spine>
</package>
""",
        "EPUB/nav.xhtml": b"""<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <body><nav epub:type="toc"><ol><li><a href="ch01.xhtml">Ch</a></li></ol></nav></body>
</html>
""",
        "EPUB/ch01.xhtml": evil,
    }
    return _write_epub(members)


def make_custom_epub3(
    *,
    title: str = "Custom",
    chapters: list[tuple[str, str, str]],
    extras: dict[str, bytes] | None = None,
    manifest_extra: str = "",
    nav_items: list[tuple[str, str]] | None = None,
    spine: list[tuple[str, bool]] | None = None,
) -> bytes:
    """Build a small EPUB 3 from chapter tuples of (id, package-relative href, inner HTML)."""
    extras = extras or {}
    nav_items = nav_items or [(f"Chapter {index}", href) for index, (_id, href, _html) in enumerate(chapters, start=1)]
    spine_items = spine or [(item_id, True) for item_id, _href, _html in chapters]
    members: dict[str, bytes] = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": CONTAINER_XML,
    }
    chapter_items: list[str] = []
    for item_id, href, html in chapters:
        chapter_items.append(f'    <item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>')
        members[f"EPUB/{href}"] = _xhtml(item_id, html)
    if nav_items and nav_items[0][1].startswith("#") and len(nav_items) > 1:
        label, href = nav_items[0]
        nested = "\n".join(
            f'          <li><a href="{child_href}">{child_label}</a></li>' for child_label, child_href in nav_items[1:]
        )
        nav_lis = f'        <li><a href="{href}">{label}</a><ol>\n{nested}\n        </ol></li>'
    else:
        nav_lis = "\n".join(f'        <li><a href="{href}">{label}</a></li>' for label, href in nav_items)
    spine_refs = []
    for item_id, linear in spine_items:
        extra = "" if linear else ' linear="no"'
        spine_refs.append(f'    <itemref idref="{item_id}"{extra}/>')
    spine_xml = "\n".join(spine_refs)
    members["EPUB/nav.xhtml"] = (
        '<?xml version="1.0"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        "  <head><title>Nav</title></head>\n"
        '  <body>\n    <nav epub:type="toc">\n      <ol>\n'
        f"{nav_lis}\n"
        "      </ol>\n    </nav>\n  </body>\n</html>\n"
    ).encode()
    members["EPUB/content.opf"] = (
        '<?xml version="1.0"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">\n'
        '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '    <dc:identifier id="bookid">urn:uuid:leafmd-custom</dc:identifier>\n'
        f"    <dc:title>{title}</dc:title>\n"
        "    <dc:language>en</dc:language>\n"
        "  </metadata>\n  <manifest>\n"
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
        + "\n".join(chapter_items)
        + "\n"
        + manifest_extra
        + "  </manifest>\n  <spine>\n"
        + spine_xml
        + "\n  </spine>\n</package>\n"
    ).encode()
    members.update(extras)
    return _write_epub(members)


def make_fragment_book() -> bytes:
    return make_custom_epub3(
        title="Fragments",
        chapters=[
            (
                "ch01",
                "text/ch01.xhtml",
                '<h1 id="welcome">Chapter 1</h1>'
                '<p id="here">Same file target.</p>'
                '<p><a href="#here">same file</a></p>'
                '<p><a href="../other/ch02.xhtml#there">cross file</a></p>',
            ),
            (
                "ch02",
                "other/ch02.xhtml",
                '<h1>Chapter 2</h1><p id="there">Cross-file target.</p>',
            ),
        ],
        nav_items=[
            ("Chapter 1", "text/ch01.xhtml#welcome"),
            ("Chapter 2", "other/ch02.xhtml#there"),
        ],
    )


def make_duplicate_id_book() -> bytes:
    return make_custom_epub3(
        title="Duplicate Ids",
        chapters=[
            (
                "ch01",
                "ch01.xhtml",
                '<h1 id="dup">First</h1><p id="dup">Second same-file dup.</p>',
            ),
            (
                "ch02",
                "ch02.xhtml",
                '<h1 id="dup">Other file same id</h1><p><a href="ch01.xhtml#dup">to first dup</a></p>',
            ),
        ],
    )


def make_scheme_book() -> bytes:
    return make_custom_epub3(
        title="Schemes",
        chapters=[
            (
                "ch01",
                "ch01.xhtml",
                "<h1>Schemes</h1>"
                '<p><a href="javascript:alert(1)">js</a></p>'
                '<p><a href="data:text/html,hi">data</a></p>'
                '<p><a href="file:///etc/passwd">file</a></p>'
                '<p><a href="https://example.com">ok</a></p>',
            )
        ],
    )


def make_missing_image_book() -> bytes:
    return make_custom_epub3(
        title="Missing Image",
        chapters=[("ch01", "ch01.xhtml", '<h1>Missing</h1><p><img src="images/gone.png" alt="gone"/></p>')],
    )


def make_remote_image_book() -> bytes:
    return make_custom_epub3(
        title="Remote Image",
        chapters=[
            (
                "ch01",
                "ch01.xhtml",
                '<h1>Remote</h1><p><img src="https://example.com/x.png" alt="remote"/></p>',
            )
        ],
    )


def make_hostile_svg_book() -> bytes:
    return make_custom_epub3(
        title="Hostile SVG",
        chapters=[("ch01", "ch01.xhtml", '<h1>SVG</h1><p><img src="images/evil.svg" alt="evil"/></p>')],
        extras={"EPUB/images/evil.svg": HOSTILE_SVG},
        manifest_extra='    <item id="evil" href="images/evil.svg" media-type="image/svg+xml"/>\n',
    )


def make_colliding_assets_book() -> bytes:
    return make_custom_epub3(
        title="Colliding Assets",
        chapters=[
            (
                "ch01",
                "ch01.xhtml",
                '<h1>Pics</h1><p><img src="one/pic.png" alt="one"/></p><p><img src="two/pic.png" alt="two"/></p>',
            )
        ],
        extras={
            "EPUB/one/pic.png": MIN_PNG,
            "EPUB/two/pic.png": MIN_PNG,
        },
        manifest_extra=(
            '    <item id="one" href="one/pic.png" media-type="image/png"/>\n'
            '    <item id="two" href="two/pic.png" media-type="image/png"/>\n'
        ),
    )


def make_many_headings_one_file() -> bytes:
    return make_custom_epub3(
        title="Many Headings",
        chapters=[
            (
                "all",
                "all.xhtml",
                '<h1 id="c1">Chapter 1 One</h1><p>first</p><h1 id="c2">Chapter 2 Two</h1><p>second</p>',
            )
        ],
        nav_items=[("Chapter 1 One", "all.xhtml#c1"), ("Chapter 2 Two", "all.xhtml#c2")],
    )


def make_split_chapter_files() -> bytes:
    return make_custom_epub3(
        title="Split Chapter",
        chapters=[
            ("p1", "ch01a.xhtml", "<h1>Chapter 1</h1><p>part a</p>"),
            ("p2", "ch01b.xhtml", "<p>part b of the same chapter</p>"),
        ],
        nav_items=[("Chapter 1", "ch01a.xhtml")],
    )


def make_virtual_part_book() -> bytes:
    return make_custom_epub3(
        title="Virtual Part",
        chapters=[
            ("ch01", "ch01.xhtml", "<h1>Chapter 1</h1><p>in part one</p>"),
            ("ch02", "ch02.xhtml", "<h1>Chapter 2</h1><p>also in part one</p>"),
        ],
        nav_items=[("Part I", "#part1"), ("Chapter 1", "ch01.xhtml"), ("Chapter 2", "ch02.xhtml")],
    )


def make_malformed_html_book() -> bytes:
    return make_custom_epub3(
        title="Malformed",
        chapters=[
            (
                "ch01",
                "ch01.xhtml",
                "<h1>Broken</h1><p>Unclosed paragraph<div>nested</p></div>",
            )
        ],
    )
