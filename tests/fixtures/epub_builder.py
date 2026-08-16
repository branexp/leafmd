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

MIN_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><rect width="1" height="1"/></svg>'


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
        "META-INF/container.xml": b"""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
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


def make_zip_slip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("../evil.txt", "nope")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
    return buffer.getvalue()


def make_drm() -> bytes:
    members = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b"""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
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
        "META-INF/container.xml": b"""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
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
