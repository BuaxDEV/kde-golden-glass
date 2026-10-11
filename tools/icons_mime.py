# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Iconos de tipos de archivo de GoldenGlass, como los documentos de Finder:
hoja blanca con la esquina doblada, el símbolo del tipo en su color y la
extensión en gris abajo. A 16/22/24 px, la misma hoja sin etiqueta.

Hay un icono por categoría (los «generic-icon» de shared-mime-info: lo que usa
KDE cuando no hay icono para el tipo concreto) y uno por tipo común con su
extensión. Los tipos que no están aquí los busca KDE por nombre en la
herencia (WhiteSur) antes de caer en la categoría.

Las etiquetas se convierten a trazos al generar (fuente del tema, en negrita),
así que el SVG no depende de las fuentes instaladas.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import icons

GRAY = "#8E8E93"
RED, ORANGE, GREEN, BLUE = "#FF3B30", "#FF9500", "#34C759", "#007AFF"
CYAN, PINK, PURPLE, INDIGO = "#32ADE6", "#FF2D55", "#AF52DE", "#5856D6"
BROWN, GRAPHITE, YELLOW = "#A2845E", "#48484A", "#E6A800"

# Símbolos propios de los documentos (cuadrícula de 16, como icons.GLYPHS)
_fill = icons._fill
GLYPHS = {
    **icons.GLYPHS,
    "lines": '<path d="M2.5 3.5 H13.5 M2.5 6.5 H13.5 M2.5 9.5 H13.5 M2.5 12.5 H9.5"/>',
    "paragraph": ('<path d="M2.5 3.2 H13.5 M2.5 6.4 H11 M2.5 9.6 H13.5 M2.5 12.8 H8.5"/>'),
    "code": '<path d="M5.2 4.2 L1.8 8 L5.2 11.8 M10.8 4.2 L14.2 8 L10.8 11.8 M9.2 2.8 L6.8 13.2"/>',
    "terminal": ('<rect x="1.6" y="2.6" width="12.8" height="10.8" rx="1.8"/>'
                 '<path d="M4.4 6 L6.8 8 L4.4 10 M8.4 10.4 H11.6"/>'),
    "braces": ('<path d="M5.6 2.4 Q3.6 2.4 3.6 4.4 V6.2 Q3.6 8 2 8 Q3.6 8 3.6 9.8 V11.6 Q3.6 13.6 5.6 13.6 '
               'M10.4 2.4 Q12.4 2.4 12.4 4.4 V6.2 Q12.4 8 14 8 Q12.4 8 12.4 9.8 V11.6 Q12.4 13.6 10.4 13.6"/>'),
    "box": ('<path d="M2.2 5 L8 2.2 L13.8 5 V11.2 L8 14 L2.2 11.2 Z M2.2 5 L8 7.8 L13.8 5 M8 7.8 V14"/>'
            '<path d="M5.1 3.6 L10.9 6.4"/>'),
    "zipper": ('<rect x="3.2" y="1.8" width="9.6" height="12.4" rx="1.6"/>'
               '<path d="M7 2.6 H8 M8 4 H9 M7 5.4 H8 M8 6.8 H9" stroke-width="1.1"/>'
               + _fill('<rect x="6.4" y="8.4" width="3.2" height="4.2" rx=".9"/>')),
    "gear": ('<circle cx="8" cy="8" r="2.2"/><path d="M8 1.6 V3.4 M8 12.6 V14.4 M1.6 8 H3.4 M12.6 8 H14.4 '
             'M3.5 3.5 L4.8 4.8 M11.2 11.2 L12.5 12.5 M3.5 12.5 L4.8 11.2 M11.2 4.8 L12.5 3.5"/>'
             '<circle cx="8" cy="8" r="4.6"/>'),
    "table": ('<rect x="1.8" y="2.6" width="12.4" height="10.8" rx="1.4"/>'
              '<path d="M1.8 6.2 H14.2 M1.8 9.8 H14.2 M6 2.6 V13.4 M10.1 2.6 V13.4"/>'),
    "chart": ('<rect x="1.8" y="2.4" width="12.4" height="8.6" rx="1.2"/><path d="M8 11 V13.8 M5.6 13.8 H10.4"/>'
              + _fill('<path d="M4.3 9 V7 H5.9 V9 Z M7.2 9 V4.8 H8.8 V9 Z M10.1 9 V6 H11.7 V9 Z"/>')),
    "shapes": '<circle cx="6" cy="6" r="3.8"/><rect x="7.6" y="7.6" width="6.6" height="6.6" rx="1"/>',
    "pdf": ('<path d="M3.2 13.2 Q5.6 9.6 7.2 5.2 Q8 2.6 7.2 2.2 Q6.2 2 6.4 4.2 Q7 8.4 12.8 11 Q14.2 11.6 '
            '13.6 12.4 Q12.6 13.2 9.4 10.6 Q6.4 10.8 3.6 12.4 Q2.4 13.4 3.2 13.2 Z"/>'),
    "book": ('<path d="M8 4 Q5.6 2.4 1.8 2.8 V12.6 Q5.6 12.2 8 13.8 Q10.4 12.2 14.2 12.6 V2.8 Q10.4 2.4 8 4 Z '
             'M8 4 V13.8"/>'),
    "database": ('<ellipse cx="8" cy="3.8" rx="5.6" ry="2"/><path d="M2.4 3.8 V12.2 Q2.4 14.2 8 14.2 '
                 'Q13.6 14.2 13.6 12.2 V3.8 M2.4 8 Q2.4 10 8 10 Q13.6 10 13.6 8"/>'),
    "calendar": ('<rect x="1.8" y="2.8" width="12.4" height="11.2" rx="1.8"/><path d="M1.8 6.2 H14.2 '
                 'M5 1.6 V3.8 M11 1.6 V3.8"/>'),
}


@dataclass(frozen=True)
class Kind:
    glyph: str | None
    color: str
    label: str | None = None


# Categorías: nombre del icono genérico → cómo se dibuja (con sus alias)
GENERIC: dict[tuple[str, ...], Kind] = {
    ("unknown", "application-octet-stream", "application-x-zerosize"): Kind(None, GRAY),
    ("text-x-generic", "text-plain", "text-x-generic-template"): Kind("lines", GRAY),
    ("text-x-script", "text-x-source"): Kind("code", INDIGO),
    ("text-html", "application-xhtml+xml"): Kind("network", BLUE),
    ("image-x-generic",): Kind("pictures", CYAN),
    ("audio-x-generic",): Kind("music", PINK),
    ("video-x-generic",): Kind("videos", PURPLE),
    ("package-x-generic", "application-x-archive"): Kind("zipper", BROWN),
    ("application-x-executable", "application-x-sharedlib"): Kind("gear", GRAPHITE),
    ("application-x-addon",): Kind("box", GRAPHITE),
    ("font-x-generic",): Kind("font", GRAPHITE),
    ("x-office-document",): Kind("paragraph", BLUE),
    ("x-office-spreadsheet",): Kind("table", GREEN),
    ("x-office-presentation",): Kind("chart", ORANGE),
    ("x-office-drawing",): Kind("shapes", YELLOW),
    ("x-office-calendar", "text-calendar"): Kind("calendar", RED),
}

# Tipos concretos: (nombres de icono…) → (categoría, etiqueta). El nombre es
# el tipo MIME canónico con «/» → «-».
SPECIFIC: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("text-markdown", "text-x-markdown"), "text-x-generic", "MD"),
    (("text-x-log",), "text-x-generic", "LOG"),
    (("text-x-python", "text-x-python3"), "text-x-script", "PY"),
    (("text-x-csrc",), "text-x-script", "C"),
    (("text-x-c++src",), "text-x-script", "CPP"),
    (("text-x-chdr",), "text-x-script", "H"),
    (("text-x-c++hdr",), "text-x-script", "HPP"),
    (("text-x-java",), "text-x-script", "JAVA"),
    (("text-rust",), "text-x-script", "RS"),
    (("text-x-go",), "text-x-script", "GO"),
    (("text-javascript", "application-javascript", "application-x-javascript"), "text-x-script", "JS"),
    (("application-typescript",), "text-x-script", "TS"),
    (("text-x-qml",), "text-x-script", "QML"),
    (("text-css",), "text-x-script", "CSS"),
    (("application-x-php",), "text-x-script", "PHP"),
    (("application-x-ruby",), "text-x-script", "RB"),
    (("text-x-lua",), "text-x-script", "LUA"),
    (("text-x-kotlin",), "text-x-script", "KT"),
    (("text-x-csharp",), "text-x-script", "CS"),
    (("application-sql",), "text-x-script", "SQL"),
    (("text-x-cmake",), "text-x-script", "CMAKE"),
    (("text-x-makefile",), "text-x-script", "MAKE"),
    (("text-x-shellscript", "application-x-shellscript"), "shell", "SH"),
    (("application-json",), "data", "JSON"),
    (("application-xml", "text-xml"), "data", "XML"),
    (("application-yaml", "application-x-yaml"), "data", "YAML"),
    (("application-toml",), "data", "TOML"),
    (("text-html",), "text-html", "HTML"),
    (("image-png",), "image-x-generic", "PNG"),
    (("image-jpeg",), "image-x-generic", "JPG"),
    (("image-gif",), "image-x-generic", "GIF"),
    (("image-webp",), "image-x-generic", "WEBP"),
    (("image-svg+xml", "image-svg+xml-compressed"), "image-x-generic", "SVG"),
    (("image-heif",), "image-x-generic", "HEIC"),
    (("image-avif",), "image-x-generic", "AVIF"),
    (("image-bmp",), "image-x-generic", "BMP"),
    (("image-tiff",), "image-x-generic", "TIFF"),
    (("audio-mpeg",), "audio-x-generic", "MP3"),
    (("audio-flac",), "audio-x-generic", "FLAC"),
    (("audio-vnd.wave", "audio-x-wav"), "audio-x-generic", "WAV"),
    (("audio-ogg", "audio-x-vorbis+ogg"), "audio-x-generic", "OGG"),
    (("audio-x-opus+ogg",), "audio-x-generic", "OPUS"),
    (("audio-mp4", "audio-x-m4a"), "audio-x-generic", "M4A"),
    (("audio-aac",), "audio-x-generic", "AAC"),
    (("video-mp4",), "video-x-generic", "MP4"),
    (("video-matroska", "video-x-matroska"), "video-x-generic", "MKV"),
    (("video-webm",), "video-x-generic", "WEBM"),
    (("video-quicktime",), "video-x-generic", "MOV"),
    (("video-vnd.avi", "video-x-msvideo"), "video-x-generic", "AVI"),
    (("application-zip",), "package-x-generic", "ZIP"),
    (("application-x-tar",), "package-x-generic", "TAR"),
    (("application-x-compressed-tar",), "package-x-generic", "TGZ"),
    (("application-gzip", "application-x-gzip"), "package-x-generic", "GZ"),
    (("application-x-xz-compressed-tar",), "package-x-generic", "TXZ"),
    (("application-x-zstd-compressed-tar",), "package-x-generic", "TZST"),
    (("application-x-xz",), "package-x-generic", "XZ"),
    (("application-zstd",), "package-x-generic", "ZST"),
    (("application-x-bzip2",), "package-x-generic", "BZ2"),
    (("application-x-7z-compressed",), "package-x-generic", "7Z"),
    (("application-vnd.rar", "application-x-rar"), "package-x-generic", "RAR"),
    (("application-vnd.debian.binary-package", "application-x-deb"), "application-x-addon", "DEB"),
    (("application-x-rpm",), "application-x-addon", "RPM"),
    (("application-vnd.appimage", "application-x-appimage"), "application-x-executable", "APP"),
    (("application-x-executable",), "application-x-executable", "EXEC"),
    (("application-pdf",), "pdf", "PDF"),
    (("application-epub+zip",), "ebook", "EPUB"),
    (("application-vnd.sqlite3", "application-x-sqlite3"), "database", "DB"),
    (("application-vnd.openxmlformats-officedocument.wordprocessingml.document",), "x-office-document", "DOCX"),
    (("application-msword",), "x-office-document", "DOC"),
    (("application-vnd.oasis.opendocument.text",), "x-office-document", "ODT"),
    (("application-rtf", "text-rtf"), "x-office-document", "RTF"),
    (("application-vnd.openxmlformats-officedocument.spreadsheetml.sheet",), "x-office-spreadsheet", "XLSX"),
    (("application-vnd.ms-excel",), "x-office-spreadsheet", "XLS"),
    (("application-vnd.oasis.opendocument.spreadsheet",), "x-office-spreadsheet", "ODS"),
    (("text-csv",), "x-office-spreadsheet", "CSV"),
    (("application-vnd.openxmlformats-officedocument.presentationml.presentation",), "x-office-presentation", "PPTX"),
    (("application-vnd.ms-powerpoint",), "x-office-presentation", "PPT"),
    (("application-vnd.oasis.opendocument.presentation",), "x-office-presentation", "ODP"),
    (("font-ttf",), "font-x-generic", "TTF"),
    (("font-otf",), "font-x-generic", "OTF"),
    (("font-woff", "font-woff2"), "font-x-generic", "WOFF"),
)

# Variantes que no son una categoría genérica de shared-mime-info
EXTRA_KINDS = {
    "shell": Kind("terminal", GRAPHITE),
    "data": Kind("braces", INDIGO),
    "pdf": Kind("pdf", RED),
    "ebook": Kind("book", ORANGE),
    "database": Kind("database", GRAPHITE),
}


# No se publican: dentro de cada tema KDE recorta un nombre que no encuentra
# («audio-volume-muted» → «audio») y, si queda un tipo de medio, prueba
# «<tipo>-x-generic» ANTES de mirar los temas heredados. Con estos iconos, un
# tema parcial como este se quedaría con cientos de iconos ajenos (volumen,
# menús, edición de imagen…). Los tipos concretos sí se publican; el resto de
# cada categoría sale de WhiteSur.
MEDIA_GENERICS = {"text-x-generic", "image-x-generic", "audio-x-generic", "video-x-generic",
                  "application-x-generic"}


def _kind(category: str) -> Kind:
    for names, kind in GENERIC.items():
        if category in names:
            return kind
    return EXTRA_KINDS[category]


# --- texto a trazos -----------------------------------------------------------

@cache
def _app():
    from PyQt6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication(["goldenglass-icons", "-platform", "offscreen"])


@cache
def text_path(text: str, family: str, cap_height: float, max_width: float) -> str:
    """`text` como trazo SVG, centrado en x=0 con la línea base en y=0."""
    _app()
    from PyQt6.QtGui import QFont, QFontMetricsF, QPainterPath

    font = QFont(family)
    font.setPixelSize(100)
    font.setWeight(QFont.Weight.Bold)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
    path = QPainterPath()
    path.addText(0, 0, font, text)
    rect = path.boundingRect()
    scale = cap_height / QFontMetricsF(font).capHeight()
    scale = min(scale, max_width / rect.width())
    dx = -rect.center().x()

    def pt(x, y):
        return f"{(x + dx) * scale:.2f} {y * scale:.2f}"

    out, i, n = [], 0, path.elementCount()
    while i < n:
        e = path.elementAt(i)
        if e.isMoveTo():
            out.append("M" + pt(e.x, e.y))
        elif e.isLineTo():
            out.append("L" + pt(e.x, e.y))
        else:  # CurveTo + 2 CurveToData
            c2, end = path.elementAt(i + 1), path.elementAt(i + 2)
            out.append("C" + pt(e.x, e.y) + " " + pt(c2.x, c2.y) + " " + pt(end.x, end.y))
            i += 2
        i += 1
    return "".join(out) + "Z"


# --- dibujo -------------------------------------------------------------------

PAGE = "M15.5 4 H40 L52 16 V56.5 Q52 60 48.5 60 H15.5 Q12 60 12 56.5 V7.5 Q12 4 15.5 4 Z"
FOLD = "M40 4 V12.5 Q40 16 43.5 16 H52 Z"


def _glyph(kind: Kind, cx: float, cy: float, scale: float, family: str) -> str:
    if kind.glyph is None:
        return ""
    if kind.glyph == "font":
        d = text_path("Aa", family, 9.6 * scale / 1.45, 30)
        return f'<path transform="translate({cx} {cy + 4.8 * scale / 1.45:.2f})" d="{d}" fill="{kind.color}"/>'
    body = GLYPHS[kind.glyph].replace("currentColor", kind.color)
    return (f'<g transform="translate({cx - 8 * scale:.2f} {cy - 8 * scale:.2f}) scale({scale})" fill="none" '
            f'stroke="{kind.color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{body}</g>')


def preview(path, family: str = "Inter") -> None:
    """Hoja con todos los tipos a 16, 32, 64 y 128 px."""
    _app()
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtGui import QColor, QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    items = [(kind, None) for kind in GENERIC.values()] + [(_kind(c), label) for _, c, label in SPECIFIC]
    cols, cell_w, cell_h = 6, 16 + 32 + 64 + 128 + 40, 136
    rows = -(-len(items) // cols)
    img = QImage(cols * cell_w, rows * cell_h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor("#ECECEC"))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    for i, (kind, label) in enumerate(items):
        x, y = (i % cols) * cell_w + 4, (i // cols) * cell_h + 4
        for size in (16, 32, 64, 128):
            body = document(kind, label, family, small=size < 32)
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{body}</svg>'
            QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(x, y + 128 - size, size, size))
            x += size + 8
    p.end()
    img.save(str(path))


def document(kind: Kind, label: str | None, family: str, small: bool = False) -> str:
    page = (
        '<defs><linearGradient id="page" x1="0" y1="4" x2="0" y2="60" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#F2F2F5"/></linearGradient>'
        '<linearGradient id="fold" x1="40" y1="16" x2="52" y2="4" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#D8D8DE"/><stop offset="1" stop-color="#F4F4F7"/></linearGradient></defs>'
        f'<path d="{PAGE}" transform="translate(0 1)" fill="#000000" fill-opacity=".14"/>'
        f'<path d="{PAGE}" fill="url(#page)" stroke="#C4C4CA" stroke-width="{1.6 if small else 0.8}"/>'
        f'<path d="{FOLD}" fill="url(#fold)" stroke="#C4C4CA" stroke-width="{1.6 if small else 0.8}" '
        'stroke-linejoin="round"/>'
    )
    if small or not label:
        return page + _glyph(kind, 32, 35, 1.9 if small else 1.45, family)
    d = text_path(label, family, 6.2, 34)
    return (page + _glyph(kind, 32, 30, 1.45, family)
            + f'<path transform="translate(32 53)" d="{d}" fill="{GRAY}"/>')


def files(family: str) -> list[tuple[str, tuple[int, str], tuple[str, ...]]]:
    """(ruta relativa, (lienzo, SVG sin envolver), alias) de los iconos de tipos."""
    out = []

    def add(names: tuple[str, ...], kind: Kind, label: str | None) -> None:
        main, aliases = names[0], names[1:]
        out.append((f"mimetypes/scalable/{main}.svg", (64, document(kind, label, family)), aliases))
        for size in icons.SMALL:
            out.append((f"mimetypes/{size}/{main}.svg", (64, document(kind, None, family, small=True)), aliases))

    specific_names = {n for names, _, _ in SPECIFIC for n in names}
    for names, kind in GENERIC.items():
        names = tuple(n for n in names if n not in specific_names | MEDIA_GENERICS)  # el concreto gana
        if names:
            add(names, kind, None)
    for names, category, label in SPECIFIC:
        add(names, _kind(category), label)
    return out
