# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema de cursores «GoldenGlass», dibujado por código como los de macOS:
flecha negra con borde blanco, manos blancas con borde negro, sombra suave y
rueda de colores animada para «ocupado».

Cada cursor se describe en un lienzo SVG de 32×32 con tamaño nominal 24 (la
convención de Breeze: a tamaño 24 la imagen mide 32 px). De esa descripción
salen los dos formatos:
  cursors_scalable/<nombre>/   SVG + metadata.json (KWin, nítido a cualquier escala)
  cursors/<nombre>             Xcursor (XWayland y apps antiguas), escrito aquí
                               mismo, rasterizado con QtSvg como lo hace KWin
Los nombres alternativos (CSS, X11 y hashes de Qt/GTK) son enlaces simbólicos.

Salida:
  build/cursors/GoldenGlass-cursors/{index.theme,cursors,cursors_scalable}

Uso directo para iterar el diseño:
  python3 tools/cursors.py --preview build/cursors-preview.png
"""

from __future__ import annotations

import colorsys
import json
import math
import shutil
import struct
from dataclasses import dataclass, field
from pathlib import Path

from ggcommon import stamp

THEME_ID = "GoldenGlass-cursors"
THEME_NAME = "GoldenGlass"
CANVAS = 32
NOMINAL = 24
XCURSOR_SIZES = (18, 24, 30, 36, 42, 48, 60, 72)  # múltiplos de 3: imagen entera
WAIT_FRAMES = 24
WAIT_DELAY = 40  # ms por fotograma: una vuelta por segundo

INK = "#000000"
PAPER = "#FFFFFF"
GREEN = "#34C759"
RED = "#FF3B30"


@dataclass
class Shape:
    """Un cursor: siluetas rellenas y trazos, con borde y sombra comunes.

    `fills` y `lines` son elementos SVG sin pintura; el borde se dibuja como
    trazo ancho de todos ellos por detrás del cuerpo, de modo que las piezas
    que se solapan se funden en una sola silueta. `extra` va encima, tal cual.
    """
    hotspot: tuple[float, float]
    fills: str = ""
    lines: str = ""
    line_width: float = 1.6
    body: str = INK
    outline: str = PAPER
    outline_width: float = 2.6      # ancho total del trazo; se ve la mitad
    extra: str = ""
    shadow: bool = True


@dataclass
class Cursor:
    name: str
    frames: list[Shape]
    delay: int = 0
    aliases: list[str] = field(default_factory=list)


# --- piezas -------------------------------------------------------------------

ARROW = "M5 4 L5 21.6 L9.1 17.9 L11.7 23.8 L14.5 22.6 L11.9 16.9 L17.2 16.9 Z"
ARROW_HOT = (5, 4)


def _rect(x0, y0, x1, y1, r):
    return f'<rect x="{x0}" y="{y0}" width="{x1 - x0:g}" height="{y1 - y0:g}" rx="{r}"/>'


def _capsule(x0, y0, x1, y1, w):
    """Cápsula de ancho w entre dos puntos (como polígono redondeado)."""
    length = math.hypot(x1 - x0, y1 - y0)
    angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return (f'<rect x="{x0:.2f}" y="{y0 - w / 2:.2f}" width="{length:.2f}" height="{w}" rx="{w / 2}" '
            f'transform="rotate({angle:.2f} {x0} {y0})"/>')


def _double_arrow(angle: float, span: float = 10.5, bar: bool = False,
                  h: float = 4.6, head: float = 5.0) -> str:
    """Flecha doble centrada en (16,16), horizontal girada `angle` grados: `span`
    es la semilongitud, `h` el semialto de cada punta y `head` su largo.
    Con `bar`, una barra en el centro (redimensionar columnas/filas)."""
    s, sh = span, 1.15  # sh: semigrosor del eje
    if bar:
        g = 2.2  # hueco entre la barra y cada flecha
        pts = [(-s, 0), (-s + head, -h), (-s + head, -sh), (-g, -sh), (-g, sh), (-s + head, sh), (-s + head, h)]
        left = "M" + " L".join(f"{16 + x:g} {16 + y:g}" for x, y in pts) + " Z"
        right = "M" + " L".join(f"{16 - x:g} {16 + y:g}" for x, y in pts) + " Z"
        return (f'<g transform="rotate({angle} 16 16)"><path d="{left}"/><path d="{right}"/>'
                f'{_rect(15, 7, 17, 25, 0.4)}</g>')
    pts = [(-s, 0), (-s + head, -h), (-s + head, -sh), (s - head, -sh), (s - head, -h),
           (s, 0), (s - head, h), (s - head, sh), (-s + head, sh), (-s + head, h)]
    d = "M" + " L".join(f"{16 + x:g} {16 + y:g}" for x, y in pts) + " Z"
    return f'<path transform="rotate({angle} 16 16)" d="{d}"/>'


def _single_arrow(angle: float) -> str:
    """Flecha hacia arriba (girada `angle`), punta en (16,5)."""
    d = "M16 5 L22.5 12 L17.3 12 L17.3 26 L14.7 26 L14.7 12 L9.5 12 Z"
    return f'<path transform="rotate({angle} 16 16)" d="{d}"/>'


def _badge(cx: float, cy: float, r: float, fill: str, inner: str, ring: str = PAPER) -> str:
    """Insignia redonda (copiar, alias, prohibido…) junto a la flecha."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r + 1.1}" fill="{ring}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'
            f'<g transform="translate({cx} {cy})" fill="none" stroke-linecap="round" '
            f'stroke-linejoin="round">{inner}</g>')


def _arrow_with(badge: str) -> Shape:
    return Shape(ARROW_HOT, fills=f'<path d="{ARROW}"/>', extra=badge)


def _wheel(cx: float, cy: float, r: float, rotation: float) -> str:
    """Rueda de colores de «ocupado»: cuñas de tono continuo, brillo encima."""
    n = 48
    wedges = []
    for i in range(n):
        a0 = math.radians(rotation + i * 360 / n - 90)
        a1 = math.radians(rotation + (i + 1.15) * 360 / n - 90)  # solape contra costuras
        hue = (0.62 - i / n) % 1.0  # azul → verde → amarillo → rojo → violeta
        rr, gg, bb = colorsys.hsv_to_rgb(hue, 0.78, 1.0)
        color = f"#{int(rr * 255):02X}{int(gg * 255):02X}{int(bb * 255):02X}"
        wedges.append(
            f'<path fill="{color}" d="M{cx} {cy} L{cx + r * math.cos(a0):.3f} {cy + r * math.sin(a0):.3f} '
            f'A{r} {r} 0 0 1 {cx + r * math.cos(a1):.3f} {cy + r * math.sin(a1):.3f} Z"/>')
    gid = f"gloss{int(cx)}{int(r * 10)}"
    return (
        f'<defs><radialGradient id="{gid}" cx="{cx - r * 0.35}" cy="{cy - r * 0.45}" r="{r * 1.35}" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="#FFFFFF" stop-opacity=".75"/>'
        f'<stop offset=".45" stop-color="#FFFFFF" stop-opacity=".08"/>'
        f'<stop offset="1" stop-color="#000000" stop-opacity=".28"/></radialGradient></defs>'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 0.9}" fill="{PAPER}"/>'
        + "".join(wedges)
        + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{gid})"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r + 0.45}" fill="none" stroke="#000000" stroke-opacity=".35" stroke-width=".5"/>'
    )


# Manos (blancas con borde negro, como en macOS)
HAND = dict(body=PAPER, outline=INK, outline_width=2.0)
FINGER_LINE = '<path d="{d}" fill="none" stroke="#000000" stroke-width=".9" stroke-linecap="round"/>'

POINTER = Shape(
    (12.5, 3.2),
    fills="".join([
        _rect(10.5, 3.2, 14.5, 18, 2),       # índice
        _rect(14.4, 10.6, 18.2, 18, 1.9),    # corazón
        _rect(18.1, 11.6, 21.7, 18.5, 1.8),  # anular
        _rect(21.6, 13.2, 24.6, 19.5, 1.5),  # meñique
        _rect(10.5, 14.5, 24.6, 25.5, 4),    # palma
        _capsule(6.6, 15.6, 12.2, 21.8, 3.3),  # pulgar
        _rect(12.6, 23.5, 22.4, 28.4, 1),    # muñeca
    ]),
    extra="".join(FINGER_LINE.format(d=d) for d in
                  ("M14.45 12.8 V16.2", "M18.15 13.4 V16.4", "M21.65 15 V17.2")),
    **HAND,
)

OPEN_HAND = Shape(
    (16, 15),
    fills="".join([
        _rect(10.2, 6.4, 13.4, 18, 1.6),
        _rect(13.4, 4.4, 16.6, 18, 1.6),
        _rect(16.6, 5.4, 19.8, 18, 1.6),
        _rect(19.8, 8.2, 22.7, 18.5, 1.45),
        _rect(10.2, 14, 22.7, 25.5, 4),
        _capsule(6.2, 12.6, 11.6, 20.4, 3.2),
        _rect(12.4, 23.5, 21.2, 28.2, 1),
    ]),
    extra="".join(FINGER_LINE.format(d=d) for d in
                  ("M13.4 12.4 V16.3", "M16.6 12.4 V16.3", "M19.8 13 V16.5")),
    **HAND,
)

CLOSED_HAND = Shape(
    (16, 15),
    fills="".join([
        _rect(10.4, 9.6, 13.5, 16, 1.55),
        _rect(13.4, 9.0, 16.6, 16, 1.6),
        _rect(16.5, 9.4, 19.7, 16, 1.6),
        _rect(19.6, 10.4, 22.6, 16.5, 1.5),
        _rect(10.4, 12.5, 22.6, 24.5, 4),
        _capsule(8.4, 15.2, 12.4, 19.6, 3.1),
        _rect(12.4, 22.5, 21.2, 27.2, 1),
    ]),
    extra="".join(FINGER_LINE.format(d=d) for d in
                  ("M13.45 11.6 V14.2", "M16.55 11.4 V14.2", "M19.65 12 V14.6")),
    **HAND,
)

IBEAM = "M12.2 6 Q16 6 16 9 Q16 6 19.8 6 M16 9 V23 M12.2 26 Q16 26 16 23 Q16 26 19.8 26"
TEXT = Shape((16, 16), lines=f'<path d="{IBEAM}"/>', line_width=1.5, outline_width=2.4)
VERTICAL_TEXT = Shape((16, 16), lines=f'<path transform="rotate(90 16 16)" d="{IBEAM}"/>',
                      line_width=1.5, outline_width=2.4)

QUESTION = ('<path d="M-1.75 -1.5 A1.85 1.85 0 1 1 0.9 0.05 C0.25 0.35 0 0.75 0 1.3" '
            'stroke="#FFFFFF" stroke-width="1.35"/><circle cx="0" cy="3.4" r=".85" fill="#FFFFFF"/>')
PLUS = '<path d="M-2.6 0 H2.6 M0 -2.6 V2.6" stroke="#FFFFFF" stroke-width="1.6"/>'
ALIAS = ('<path d="M-2.4 2.4 V0.6 A2.2 2.2 0 0 1 -0.2 -1.6 H2.2" stroke="#FFFFFF" stroke-width="1.3"/>'
         '<path d="M0.6 -3.4 L2.6 -1.6 L0.6 0.2" stroke="#FFFFFF" stroke-width="1.3"/>')
FORBIDDEN = ('<circle r="3" stroke="#FFFFFF" stroke-width="1.4"/>'
             '<path d="M-2.1 2.1 L2.1 -2.1" stroke="#FFFFFF" stroke-width="1.4"/>')
MENU = ('<rect x="-3" y="-3.3" width="6" height="6.6" rx=".9" fill="#FFFFFF"/>'
        '<path d="M-1.7 -1.4 H1.7 M-1.7 0.4 H1.7 M-1.7 2.0 H1.7" stroke="#000000" stroke-width=".8"/>')

BADGE_C, BADGE_R = (22.6, 23.4), 4.6


def _magnifier(sign: str) -> Shape:
    """Lupa: aro y mango negros, cristal claro y el signo encima."""
    mark = "M10.2 13 H15.8" + (" M13 10.2 V15.8" if sign == "+" else "")
    return Shape((13, 13),
                 lines='<circle cx="13" cy="13" r="6.2"/><path d="M17.6 17.6 L24.5 24.5" stroke-width="3.4"/>',
                 line_width=1.8, outline_width=2.4,
                 extra=(f'<circle cx="13" cy="13" r="5.3" fill="#FFFFFF" fill-opacity=".92"/>'
                        f'<path d="{mark}" stroke="#000000" stroke-width="1.6" stroke-linecap="round"/>'))


PENCIL = Shape(
    (5, 27),
    fills=('<path transform="rotate(-45 5 27)" '
           'd="M5 27 L10.5 24.4 L24 24.4 A2.6 2.6 0 0 1 24 29.6 L10.5 29.6 Z"/>'),
    extra=('<path transform="rotate(-45 5 27)" d="M10.5 24.6 V29.4 M21.4 24.6 V29.4" '
           'stroke="#FFFFFF" stroke-width=".9" fill="none"/>'),
)

COLOR_PICKER = Shape(
    (5, 27),
    fills=('<g transform="rotate(-45 5 27)">'
           '<path d="M5 27 L8 25.8 L16 25.8 L16 28.2 L8 28.2 Z"/>'
           f'{_rect(15.5, 24.2, 19, 29.8, 0.6)}<circle cx="22.4" cy="27" r="3.6"/></g>'),
)


def cursors() -> list[Cursor]:
    arrow = Shape(ARROW_HOT, fills=f'<path d="{ARROW}"/>')
    hor, ver = _double_arrow(0), _double_arrow(90)
    fdiag, bdiag = _double_arrow(45, 9.5), _double_arrow(-45, 9.5)

    def frames(fn) -> list[Shape]:
        return [fn(i * 360 / WAIT_FRAMES) for i in range(WAIT_FRAMES)]

    wait = frames(lambda rot: Shape((16, 16), extra=_wheel(16, 16, 9, rot), shadow=False))
    progress = frames(lambda rot: Shape(ARROW_HOT, fills=f'<path d="{ARROW}"/>',
                                        extra=_wheel(22.4, 23.2, 4.8, rot)))

    def resize(fill: str) -> Shape:
        return Shape((16, 16), fills=fill)

    return [
        Cursor("default", [arrow], aliases=["arrow", "left_ptr", "size-bdiag", "size-fdiag", "size-hor",
                                            "size-ver", "top_left_arrow", "wayland-cursor"]),
        Cursor("right_ptr", [Shape((27, 4), fills=f'<path transform="matrix(-1 0 0 1 32 0)" d="{ARROW}"/>')]),
        Cursor("center_ptr", [Shape((16, 5), fills=_single_arrow(0))]),
        Cursor("pointer", [POINTER], aliases=["9d800788f1b08800ae810202380a0822",
                                              "e29285e634086352946a0e7090d73106",
                                              "hand1", "hand2", "pointing_hand"]),
        Cursor("openhand", [OPEN_HAND], aliases=["grab"]),
        Cursor("dnd-move", [CLOSED_HAND], aliases=["4498f0e0c1937ffe01fd06f973665830",
                                                   "9081237383d90e509aa00f00170e968f", "closedhand",
                                                   "dnd-none", "fcf21c00b30f7e3f83fe0dfd12e71cff",
                                                   "grabbing", "move"]),
        Cursor("text", [TEXT], aliases=["ibeam", "xterm"]),
        Cursor("vertical-text", [VERTICAL_TEXT]),
        Cursor("crosshair", [Shape((16, 16), lines='<path d="M16 5 V27 M5 16 H27"/>', line_width=1.3,
                                   outline_width=2.3)], aliases=["cross", "tcross"]),
        Cursor("cell", [Shape((16, 16), fills=(_rect(13.8, 6.5, 18.2, 25.5, 0.6)
                                               + _rect(6.5, 13.8, 25.5, 18.2, 0.6)),
                              body=PAPER, outline=INK, outline_width=2.0)], aliases=["plus"]),
        Cursor("help", [_arrow_with(_badge(*BADGE_C, BADGE_R, INK, QUESTION))],
               aliases=["5c6cd98b3f3ebcb1f9c7f1c204630408", "d9ce0ab605698f320427677b458ad60b",
                        "left_ptr_help", "question_arrow", "whats_this"]),
        Cursor("copy", [_arrow_with(_badge(*BADGE_C, BADGE_R, GREEN, PLUS))],
               aliases=["1081e37283d90000800003c07f3ef6bf", "6407b0e94181790501fd1e167b474872",
                        "b66166c04f8c3109214a4fbd64a50fc8", "dnd-copy"]),
        Cursor("alias", [_arrow_with(_badge(*BADGE_C, BADGE_R, INK, ALIAS))],
               aliases=["3085a0e285430894940527032f8b26df", "640fb0e74195791501fd1ed57b41487f",
                        "a2a266d0498c3104214a47bd64ab0fc8", "link", "dnd-link"]),
        Cursor("context-menu", [_arrow_with(_badge(*BADGE_C, BADGE_R, INK, MENU))]),
        Cursor("not-allowed", [_arrow_with(_badge(*BADGE_C, BADGE_R, RED, FORBIDDEN))],
               aliases=["circle", "crossed_circle", "03b6e0fcb3499374a867c041f52298f0",
                        "no-drop", "dnd-no-drop", "forbidden"]),
        Cursor("progress", progress, WAIT_DELAY,
               aliases=["00000000000000020006000e7e9ffc3f", "08e8e1c95fe2fc01f976f1e063a24ccd",
                        "3ecb610c1bf2410f44200f48c40d3599", "half-busy", "left_ptr_watch"]),
        Cursor("wait", wait, WAIT_DELAY, aliases=["watch"]),
        Cursor("size_hor", [resize(hor)], aliases=["e-resize", "ew-resize", "h_double_arrow",
                                                   "sb_h_double_arrow", "w-resize", "left_side",
                                                   "right_side"]),
        Cursor("size_ver", [resize(ver)], aliases=["00008160000006810000408080010102", "n-resize",
                                                   "ns-resize", "sb_v_double_arrow", "s-resize",
                                                   "v_double_arrow", "top_side", "bottom_side"]),
        Cursor("size_fdiag", [resize(fdiag)], aliases=["nw-resize", "nwse-resize", "se-resize",
                                                       "top_left_corner", "bottom_right_corner"]),
        Cursor("size_bdiag", [resize(bdiag)], aliases=["ne-resize", "nesw-resize", "sw-resize",
                                                       "top_right_corner", "bottom_left_corner"]),
        Cursor("col-resize", [resize(_double_arrow(0, bar=True))], aliases=["split_h"]),
        Cursor("row-resize", [resize(_double_arrow(90, bar=True))], aliases=["split_v"]),
        Cursor("fleur", [resize(_double_arrow(0, 11, h=3.7, head=4.4) + _double_arrow(90, 11, h=3.7, head=4.4))],
               aliases=["all-scroll", "size_all"]),
        Cursor("up-arrow", [Shape((16, 5), fills=_single_arrow(0))], aliases=["sb_up_arrow"]),
        Cursor("right-arrow", [Shape((27, 16), fills=_single_arrow(90))], aliases=["sb_right_arrow"]),
        Cursor("down-arrow", [Shape((16, 27), fills=_single_arrow(180))], aliases=["sb_down_arrow"]),
        Cursor("left-arrow", [Shape((5, 16), fills=_single_arrow(270))], aliases=["sb_left_arrow"]),
        Cursor("zoom-in", [_magnifier("+")]),
        Cursor("zoom-out", [_magnifier("-")]),
        Cursor("pencil", [PENCIL], aliases=["draft"]),
        Cursor("color-picker", [COLOR_PICKER]),
        Cursor("x-cursor", [Shape((16, 16), lines='<path d="M9.5 9.5 L22.5 22.5 M22.5 9.5 L9.5 22.5"/>',
                                  line_width=2.6)], aliases=["X_cursor", "pirate"]),
    ]


# --- SVG ----------------------------------------------------------------------

SHADOW_FILTER = ('<filter id="shadow" x="-50%" y="-50%" width="200%" height="200%" '
                 'color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation=".75"/></filter>')


def svg(shape: Shape) -> str:
    ow = shape.outline_width
    lw = shape.line_width

    def layer(color: str, grow: float) -> str:
        parts = []
        if shape.fills:
            stroke = f' stroke="{color}" stroke-width="{grow:g}"' if grow else ""
            parts.append(f'<g fill="{color}"{stroke}>{shape.fills}</g>')
        if shape.lines:
            parts.append(f'<g fill="none" stroke="{color}" stroke-width="{lw + grow:g}">{shape.lines}</g>')
        return "".join(parts)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS}" height="{CANVAS}" '
           f'viewBox="0 0 {CANVAS} {CANVAS}" stroke-linejoin="round" stroke-linecap="round">']
    if shape.shadow and (shape.fills or shape.lines):
        out.append(f"<defs>{SHADOW_FILTER}</defs>")
        out.append(f'<g filter="url(#shadow)" opacity=".38" transform="translate(0 .9)">{layer("#000000", ow)}</g>')
    if shape.fills or shape.lines:
        out.append(layer(shape.outline, ow))
        out.append(layer(shape.body, 0))
    out.append(shape.extra)
    out.append("</svg>\n")
    return "".join(out)


# --- Xcursor ------------------------------------------------------------------

def _rasterize(svg_text: str, px: int):
    """SVG → bytes ARGB premultiplicado (orden de Xcursor), con QtSvg."""
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(svg_text.encode()))
    img = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    # ARGB32 en memoria little-endian = BGRA = el entero ARGB de Xcursor
    return img.constBits().asstring(px * px * 4)


def xcursor(cursor: Cursor) -> bytes:
    images = []
    for size in XCURSOR_SIZES:
        px = size * CANVAS // NOMINAL
        for shape in cursor.frames:
            hx = min(px - 1, int(shape.hotspot[0] * px / CANVAS))
            hy = min(px - 1, int(shape.hotspot[1] * px / CANVAS))
            header = struct.pack("<9I", 36, 0xFFFD0002, size, 1, px, px, hx, hy, cursor.delay or 50)
            images.append((size, header + _rasterize(svg(shape), px)))
    ntoc = len(images)
    pos = 16 + 12 * ntoc
    toc, chunks = [], []
    for size, chunk in images:
        toc.append(struct.pack("<3I", 0xFFFD0002, size, pos))
        chunks.append(chunk)
        pos += len(chunk)
    return struct.pack("<4s3I", b"Xcur", 16, 0x10000, ntoc) + b"".join(toc) + b"".join(chunks)


# --- paquete ------------------------------------------------------------------

def _stamp() -> str:
    return stamp(Path(__file__))


def _symlink(target: str, link: Path) -> None:
    if link.exists() or link.is_symlink():
        return  # un nombre real gana a un alias repetido
    link.symlink_to(target)


def build(out: Path) -> list[Path]:
    """Genera el tema; se salta si el generador no cambió."""
    root = out / "cursors" / THEME_ID
    stamp_file = root / ".stamp"
    if stamp_file.exists() and stamp_file.read_text() == _stamp():
        return []
    if root.exists():
        shutil.rmtree(root)
    xdir, sdir = root / "cursors", root / "cursors_scalable"
    xdir.mkdir(parents=True)
    sdir.mkdir()

    all_cursors = cursors()
    for cur in all_cursors:
        folder = sdir / cur.name
        folder.mkdir()
        meta = []
        for i, shape in enumerate(cur.frames):
            filename = f"{cur.name}-{i + 1:02d}.svg" if len(cur.frames) > 1 else f"{cur.name}.svg"
            (folder / filename).write_text(svg(shape), encoding="utf-8")
            entry = {"filename": filename, "hotspot_x": shape.hotspot[0], "hotspot_y": shape.hotspot[1],
                     "nominal_size": NOMINAL}
            if cur.delay:
                entry["delay"] = cur.delay
            meta.append(entry)
        (folder / "metadata.json").write_text(json.dumps(meta, indent=4) + "\n", encoding="utf-8")
        (xdir / cur.name).write_bytes(xcursor(cur))

    for cur in all_cursors:
        for alias in cur.aliases:
            _symlink(cur.name, xdir / alias)
            _symlink(cur.name, sdir / alias)

    (root / "index.theme").write_text(
        "[Icon Theme]\n"
        f"Name={THEME_NAME}\n"
        "Comment=macOS-inspired cursors for GoldenGlass\n"
        "Inherits=breeze_cursors\n", encoding="utf-8")
    stamp_file.write_text(_stamp())
    return [root]


def preview(path: Path, px: int = 64) -> None:
    """Hoja con todos los cursores sobre fondo claro y oscuro."""
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtGui import QColor, QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    items = cursors()
    cols = 9
    rows = math.ceil(len(items) / cols)
    cell = px + 16
    img = QImage(cols * cell, rows * cell * 2, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for band, bg in enumerate((QColor("#ECECEC"), QColor("#2B2B2E"))):
        painter.fillRect(0, band * rows * cell, cols * cell, rows * cell, bg)
        for i, cur in enumerate(items):
            x = (i % cols) * cell + 8
            y = band * rows * cell + (i // cols) * cell + 8
            shape = cur.frames[len(cur.frames) // 3]
            QSvgRenderer(QByteArray(svg(shape).encode())).render(painter, QRectF(x, y, px, px))
            hx, hy = x + shape.hotspot[0] * px / CANVAS, y + shape.hotspot[1] * px / CANVAS
            painter.setPen(QColor(255, 0, 255))
            painter.drawPoint(int(hx), int(hy))
    painter.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", type=Path, required=True, help="PNG con todos los cursores")
    ap.add_argument("--size", type=int, default=64, help="lado de cada cursor en la hoja")
    args = ap.parse_args()
    preview(args.preview, args.size)
    print(args.preview)
