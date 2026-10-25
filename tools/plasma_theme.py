# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generador del Plasma Style "GoldenGlass" a partir de los tokens.

Cada SVG se dibuja por código como piezas de FrameSvg (KSvg): nueve teselas
por marco (`[prefijo]topleft` … `[prefijo]center`), sugerencias de margen
(`hint-*-margin`), máscara para el blur (`mask-*`) y sombra (`shadow-*`).

Los colores no se fijan aquí: se usan las clases `ColorScheme-*`, que Plasma
sustituye por el esquema de color activo. Por eso un único Plasma Style sirve
para las variantes clara y oscura; solo la opacidad queda fija en el SVG.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

THEME_ID = "GoldenGlass"

# Teselas de esquina: (dirección inicio, dirección fin) del arco, en el
# sentido de las agujas del reloj, vistas desde el centro del círculo.
_CORNER_ARCS = {
    "topleft": ((-1, 0), (0, -1)),
    "topright": ((0, -1), (1, 0)),
    "bottomright": ((1, 0), (0, 1)),
    "bottomleft": ((0, 1), (-1, 0)),
}

_STYLE = """<style type="text/css" id="current-color-scheme">
  .ColorScheme-Text { color:#232629; }
  .ColorScheme-Background { color:#eff0f1; }
  .ColorScheme-Highlight { color:#3daee9; }
  .ColorScheme-NeutralText { color:#f67400; }
</style>"""


def _f(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".")


@dataclass(frozen=True)
class Paint:
    """Relleno: clase ColorScheme (o color fijo) + opacidad."""
    cls: str | None
    alpha: float
    color: str = "currentColor"

    def _cls(self) -> str:
        return f' class="{self.cls}"' if self.cls else ""

    def attrs(self) -> str:
        return f'{self._cls()} style="fill:{self.color};fill-opacity:{_f(self.alpha)}"'



BG = "ColorScheme-Background"
TEXT = "ColorScheme-Text"
HIGHLIGHT = "ColorScheme-Highlight"
NEUTRAL = "ColorScheme-NeutralText"
BLACK = Paint(None, 1.0, "#000000")


class Svg:
    """Documento SVG que reserva bloques sin solaparse (una fila por bloque)."""

    GAP = 4

    def __init__(self) -> None:
        self.defs: list[str] = []
        self.body: list[str] = []
        self._y = 0.0
        self._w = 0.0
        self._ids = 0

    def reserve(self, w: float, h: float) -> tuple[float, float]:
        y = self._y
        self._y += h + self.GAP
        self._w = max(self._w, w)
        return 0.0, y

    def uid(self, stem: str) -> str:
        self._ids += 1
        return f"{stem}{self._ids}"

    def hint(self, name: str, w: float, h: float) -> None:
        x, y = self.reserve(w, h)
        self.body.append(f'<rect id="{name}" x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
                         f'style="fill:#000000;fill-opacity:0"/>')

    def render(self) -> str:
        w, h = max(self._w, 1), max(self._y, 1)
        return "\n".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<!-- Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR -->",
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(w)}" height="{_f(h)}" '
            f'viewBox="0 0 {_f(w)} {_f(h)}" version="1.1">',
            "<defs>", _STYLE, *self.defs, "</defs>",
            *self.body,
            "</svg>", "",
        ])


# --- marcos -------------------------------------------------------------------

def frame(svg: Svg, prefix: str, radius: float, fill: Paint,
          border: Paint | None = None, margins: tuple[float, float, float, float] | None = None,
          edge: float = 8, stretch: bool = False, border_width: float = 1) -> None:
    """Marco de 9 teselas con esquinas redondeadas.

    `margins` = (top, right, bottom, left) → `hint-*-margin`.
    """
    c = max(radius, 1.0)
    x0, y0 = svg.reserve(2 * c + edge, 2 * c + edge)
    xs = (x0, x0 + c, x0 + c + edge)
    ys = (y0, y0 + c, y0 + c + edge)
    sizes = (c, edge, c)
    names = (("topleft", "top", "topright"),
             ("left", "center", "right"),
             ("bottomleft", "bottom", "bottomright"))

    for row in range(3):
        for col in range(3):
            name = names[row][col]
            x, y, w, h = xs[col], ys[row], sizes[col], sizes[row]
            parts = [_tile_fill(name, x, y, w, h, c, radius, fill)]
            if border is not None and name != "center":
                parts.append(_tile_border(name, x, y, w, h, c, radius, border, border_width))
            svg.body.append(f'<g id="{prefix}{name}">{"".join(parts)}</g>')

    if margins is not None:
        for side, value in zip(("top", "right", "bottom", "left"), margins):
            horizontal = side in ("top", "bottom")
            svg.hint(f"{prefix}hint-{side}-margin", 1 if horizontal else value, value if horizontal else 1)
    if stretch:
        svg.hint(f"{prefix}hint-stretch-borders", 1, 1)


def _tile_fill(name: str, x, y, w, h, c, radius, paint: Paint) -> str:
    if name in _CORNER_ARCS and radius > 0:
        cx, cy = _corner_center(name, x, y, c)
        (sx, sy), (ex, ey) = _CORNER_ARCS[name]
        return (f'<path d="M {_f(cx)},{_f(cy)} L {_f(cx + sx * c)},{_f(cy + sy * c)} '
                f'A {_f(c)},{_f(c)} 0 0 1 {_f(cx + ex * c)},{_f(cy + ey * c)} Z"{paint.attrs()}/>')
    return f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}"{paint.attrs()}/>'


def _tile_border(name: str, x, y, w, h, c, radius, paint: Paint, width: float = 1) -> str:
    """Filo de `width` px en el lado exterior de la tesela."""
    if name in _CORNER_ARCS and radius > 0:
        # Anillo relleno (no trazo): QtSvg suma medio ancho de trazo a los
        # límites del elemento, lo que encoge la tesela y abre rendijas.
        cx, cy = _corner_center(name, x, y, c)
        (sx, sy), (ex, ey) = _CORNER_ARCS[name]
        ri = max(c - width, 0)
        return (f'<path d="M {_f(cx + sx * c)},{_f(cy + sy * c)} A {_f(c)},{_f(c)} 0 0 1 '
                f'{_f(cx + ex * c)},{_f(cy + ey * c)} L {_f(cx + ex * ri)},{_f(cy + ey * ri)} '
                f'A {_f(ri)},{_f(ri)} 0 0 0 {_f(cx + sx * ri)},{_f(cy + sy * ri)} Z"{paint.attrs()}/>')
    lines = []
    if name.startswith("top"):
        lines.append((x, y, w, width))
    if name.startswith("bottom"):
        lines.append((x, y + h - width, w, width))
    if name.endswith("left"):
        lines.append((x, y, width, h))
    if name.endswith("right"):
        lines.append((x + w - width, y, width, h))
    return "".join(f'<rect x="{_f(lx)}" y="{_f(ly)}" width="{_f(lw)}" height="{_f(lh)}"{paint.attrs()}/>'
                   for lx, ly, lw, lh in lines)


def _corner_center(name: str, x, y, c) -> tuple[float, float]:
    return {
        "topleft": (x + c, y + c),
        "topright": (x, y + c),
        "bottomright": (x, y),
        "bottomleft": (x + c, y),
    }[name]


def shadow(svg: Svg, radius: float, size: float, alpha: float) -> None:
    """Sombra para KWindowShadow: esquinas (size+radius)², bordes de grosor size.

    La sombra empieza en el borde del contenido con opacidad `alpha` y decae
    hasta 0; dentro del contenido es transparente (no oscurece el vidrio).
    """
    falloff = [(0.0, 1.0), (0.25, 0.56), (0.5, 0.25), (0.75, 0.06), (1.0, 0.0)]
    corner = size + radius
    inner = radius / corner if corner else 0.0

    for name, (sx, sy) in (("topleft", (1, 1)), ("topright", (0, 1)),
                           ("bottomright", (0, 0)), ("bottomleft", (1, 0))):
        gid = svg.uid("shadowcorner")
        x, y = svg.reserve(corner, corner)
        cx, cy = x + sx * corner, y + sy * corner
        stops = ['<stop offset="0" stop-color="#000" stop-opacity="0"/>',
                 f'<stop offset="{_f(inner)}" stop-color="#000" stop-opacity="0"/>']
        stops += [f'<stop offset="{_f(inner + t * (1 - inner) + (1e-3 if t == 0 else 0))}" '
                  f'stop-color="#000" stop-opacity="{_f(alpha * k)}"/>' for t, k in falloff]
        svg.defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{_f(cx)}" '
                        f'cy="{_f(cy)}" r="{_f(corner)}">{"".join(stops)}</radialGradient>')
        svg.body.append(f'<rect id="shadow-{name}" x="{_f(x)}" y="{_f(y)}" width="{_f(corner)}" '
                        f'height="{_f(corner)}" style="fill:url(#{gid})"/>')

    edge = 8
    for name, horizontal, outer_first in (("top", True, True), ("bottom", True, False),
                                          ("left", False, True), ("right", False, False)):
        gid = svg.uid("shadowside")
        w, h = (edge, size) if horizontal else (size, edge)
        x, y = svg.reserve(w, h)
        # El gradiente va del borde del contenido (opaco) hacia fuera (transparente).
        if horizontal:
            x1, y1, x2, y2 = (x, y + h, x, y) if outer_first else (x, y, x, y + h)
        else:
            x1, y1, x2, y2 = (x + w, y, x, y) if outer_first else (x, y, x + w, y)
        stops = "".join(f'<stop offset="{_f(t)}" stop-color="#000" stop-opacity="{_f(alpha * k)}"/>'
                        for t, k in falloff)
        svg.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{_f(x1)}" '
                        f'y1="{_f(y1)}" x2="{_f(x2)}" y2="{_f(y2)}">{stops}</linearGradient>')
        svg.body.append(f'<rect id="shadow-{name}" x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" '
                        f'height="{_f(h)}" style="fill:url(#{gid})"/>')

    for side in ("top", "right", "bottom", "left"):
        horizontal = side in ("top", "bottom")
        svg.hint(f"shadow-hint-{side}-margin", 1 if horizontal else size, size if horizontal else 1)


# --- piezas del tema ----------------------------------------------------------

def glass_alpha(tokens: dict, level: float | None = None) -> float:
    """Opacidad del vidrio para un nivel del slider (interpolación entre muescas)."""
    if level is None:
        level = tokens["glass"]["default_level"]
    notches = sorted(tokens["glass"]["notch"].values(), key=lambda n: n["position"])
    level = min(max(level, notches[0]["position"]), notches[-1]["position"])
    for a, b in zip(notches, notches[1:]):
        if a["position"] <= level <= b["position"]:
            t = (level - a["position"]) / (b["position"] - a["position"])
            return a["alpha"] + t * (b["alpha"] - a["alpha"])
    return notches[-1]["alpha"]


def glass_surface(tokens: dict, radius: float, margin: float, shadow_size: float,
                  shadow_alpha: float, alpha: float) -> str:
    """Superficie de vidrio completa: marco + máscara de blur + sombra."""
    border = Paint(TEXT, tokens["glass"]["border"]["alpha"])
    svg = Svg()
    frame(svg, "", radius, Paint(BG, alpha), border, margins=(margin,) * 4)
    frame(svg, "mask-", radius, BLACK)
    shadow(svg, radius, shadow_size, shadow_alpha)
    return svg.render()


def tasks_svg(tokens: dict) -> str:
    """Elementos del gestor de tareas: punto bajo las apps abiertas, como el Dock.

    El punto vive en la tesela del borde exterior (abajo en un dock inferior) y
    se estira con `hint-stretch-borders`; la tesela se dibuja al ancho típico
    de un elemento para que el punto quede redondo.
    """
    p = tokens["plasma"]
    dot = p["task_dot_size"]
    span = p["dock_icon_size"]               # ancho del borde ≈ ancho del icono
    thick = dot + 2                          # grosor del borde con el punto
    corner = 2
    none = Paint(None, 0.0, "#000000")
    svg = Svg()

    orientations = {"": "bottom", "north-": "top", "west-": "left", "east-": "right"}
    states = {
        "normal": (None, Paint(TEXT, p["task_dot_alpha"])),
        "minimized": (None, Paint(TEXT, p["task_dot_minimized_alpha"])),
        "focus": (None, Paint(TEXT, p["task_dot_focus_alpha"])),
        "attention": (None, Paint(NEUTRAL, 1.0)),  # naranja del esquema (claro u oscuro)
        "hover": (None, Paint(TEXT, p["task_dot_alpha"])),  # el Dock de macOS no resalta al pasar
        "progress": (Paint(HIGHLIGHT, p["task_progress_alpha"]), None),
    }

    for orient, side in orientations.items():
        for state, (fill, dot_paint) in states.items():
            # Sin hint-*-margin: KSvg usa el tamaño de cada borde como margen,
            # así el icono queda separado del punto solo en el lado exterior.
            _dot_frame(svg, f"{orient}{state}-", side, fill or none, dot_paint, corner, span, thick, dot)
    svg.hint("hint-stretch-borders", 1, 1)

    # Flechas de grupo: el Dock de macOS no las muestra; elementos vacíos.
    for side in ("top", "bottom", "left", "right"):
        svg.hint(f"group-expander-{side}", 1, 1)
    return svg.render()


def _dot_frame(svg: Svg, prefix: str, side: str, fill: Paint, dot: Paint | None,
               corner: float, span: float, thick: float, size: float) -> None:
    """Marco plano cuyo borde `side` lleva un punto centrado."""
    horizontal = side in ("top", "bottom")
    w = 2 * corner + span if horizontal else 2 * thick + span
    h = 2 * thick + span if horizontal else 2 * corner + span
    x0, y0 = svg.reserve(w + 2 * thick, h + 2 * thick)
    cw = thick if not horizontal else corner      # ancho de columnas laterales
    ch = thick if horizontal else corner          # alto de filas sup./inf.
    xs = (x0, x0 + cw, x0 + cw + span)
    ys = (y0, y0 + ch, y0 + ch + span)
    sizes_x, sizes_y = (cw, span, cw), (ch, span, ch)
    names = (("topleft", "top", "topright"),
             ("left", "center", "right"),
             ("bottomleft", "bottom", "bottomright"))
    for row in range(3):
        for col in range(3):
            name = names[row][col]
            x, y, tw, th = xs[col], ys[row], sizes_x[col], sizes_y[row]
            parts = [f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(tw)}" height="{_f(th)}"{fill.attrs()}/>']
            if dot is not None and name == side:
                cx, cy = x + tw / 2, y + th / 2
                parts.append(f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(size / 2)}"{dot.attrs()}/>')
            svg.body.append(f'<g id="{prefix}{name}">{"".join(parts)}</g>')


def viewitem_svg(tokens: dict) -> str:
    """Resaltado de elementos de lista (Kickoff, KRunner, popups)."""
    p = tokens["plasma"]
    r = tokens["radius"]["control"]
    margins = (p["item_padding_v"], p["item_padding_h"]) * 2
    svg = Svg()
    frame(svg, "normal-", r, Paint(None, 0.0, "#000000"), margins=margins)
    frame(svg, "hover-", r, Paint(TEXT, p["item_hover_alpha"]), margins=margins)
    frame(svg, "selected-", r, Paint(HIGHLIGHT, p["item_selected_alpha"]), margins=margins)
    frame(svg, "selected+hover-", r,
          Paint(HIGHLIGHT, min(1.0, p["item_selected_alpha"] + p["item_selected_hover_boost"])), margins=margins)
    svg.hint("hint-tile-center", 1, 1)
    return svg.render()


def lineedit_svg(tokens: dict) -> str:
    """Campo de texto de vidrio (KRunner/Spotlight, contraseña de bloqueo).

    Relleno y filo derivan del color de texto, así funciona igual sobre el
    vidrio claro, el oscuro y el fondo de la pantalla de bloqueo.
    """
    p = tokens["plasma"]
    r = tokens["radius"]["field"]
    margins = (p["field_padding_v"], p["field_padding_h"]) * 2
    clear = Paint(None, 0.0, "#000000")
    svg = Svg()
    frame(svg, "base-", r, Paint(TEXT, p["field_alpha"]), Paint(TEXT, p["field_border_alpha"]), margins=margins)
    # Plasma agranda hover/focus hacia fuera según sus márgenes: cada anillo
    # cubre el filo de 1 px de base y sobresale solo lo que le queda de ancho.
    frame(svg, "hover-", r + 1, clear, Paint(TEXT, p["field_hover_alpha"]), margins=(1, 1, 1, 1), border_width=2)
    ring = tokens["focus_ring"]
    out = ring["width"] - 1
    for prefix in ("focus-", "focusframe-"):
        frame(svg, prefix, r + out, clear, Paint(HIGHLIGHT, ring["alpha"]),
              margins=(out, out, out, out), border_width=ring["width"])
    svg.hint("hint-focus-over-base", 1, 1)
    svg.hint("hint-tile-center", 1, 1)
    return svg.render()


def menubaritem_svg(tokens: dict) -> str:
    """Menús de la app en la barra de menús (applet de menú global).

    Margen lateral de macOS entre títulos. Al pasar o abrir un menú el applet
    pinta el texto con el color de texto resaltado: el fondo tiene que ser el
    acento entero para que se lea.
    """
    r = tokens["radius"]["control"]
    pad = tokens["plasma"]["menubar_item_padding"]
    # arriba y abajo, un margen real: KSvg no lee una marca de 0 px y usaría la esquina
    margins = (4, pad, 4, pad)
    svg = Svg()
    frame(svg, "normal-", r, Paint(None, 0.0, "#000000"), margins=margins)
    frame(svg, "hover-", r, Paint(HIGHLIGHT, 1.0), margins=margins)
    frame(svg, "pressed-", r, Paint(HIGHLIGHT, 1.0), margins=margins)
    return svg.render()


def plasmoidheading_svg(tokens: dict) -> str:
    """Cabecera/pie de los popups: transparentes, como en macOS."""
    m = tokens["plasma"]["popup_margin"]
    svg = Svg()
    clear = Paint(None, 0.0, "#000000")
    frame(svg, "header-", 0, clear)
    frame(svg, "footer-", 0, clear)
    for side in ("top", "right", "bottom", "left"):
        horizontal = side in ("top", "bottom")
        v = m / 2
        svg.hint(f"hint-{side}-margin", 1 if horizontal else v, v if horizontal else 1)
    svg.hint("hint-stretch-borders", 1, 1)
    return svg.render()


# --- paquete ------------------------------------------------------------------

def build(tokens: dict, out: Path, level: float | None = None) -> list[Path]:
    """Escribe el Plasma Style en `out/plasma/desktoptheme/GoldenGlass`."""
    root = out / "plasma" / "desktoptheme" / THEME_ID
    p = tokens["plasma"]
    rad = tokens["radius"]
    # Barra de menús y dock comparten panel-background. Al crear un panel,
    # Plasma limita su altura a esquina superior + inferior del fondo (todos
    # los bordes activos), así que el radio del dock acota la barra de menús.
    if 2 * rad["dock"] > p["menubar_height"]:
        raise SystemExit(f"radius.dock ({rad['dock']}) debe ser ≤ plasma.menubar_height / 2 "
                         f"({p['menubar_height'] / 2:g}): Plasma no deja bajar la barra de menús "
                         f"de {2 * rad['dock']} px")
    alpha = glass_alpha(tokens, level)
    files: dict[str, str] = {}

    variants = {"translucent/": alpha, "": 1.0, "opaque/": 1.0, "solid/": 1.0}
    for prefix, a in variants.items():
        files[f"{prefix}dialogs/background.svg"] = glass_surface(
            tokens, rad["popup"], p["popup_margin"], p["popup_shadow"], p["popup_shadow_alpha"], a)
        files[f"{prefix}widgets/panel-background.svg"] = glass_surface(
            tokens, rad["dock"], p["dock_padding"], p["popup_shadow"], p["popup_shadow_alpha"], a)
        files[f"{prefix}widgets/tooltip.svg"] = glass_surface(
            tokens, rad["tooltip"], p["tooltip_margin"], p["tooltip_shadow"], p["tooltip_shadow_alpha"], a)
        files[f"{prefix}widgets/background.svg"] = glass_surface(
            tokens, rad["popup"], p["popup_margin"], p["popup_shadow"], p["popup_shadow_alpha"], a)

    files["widgets/tasks.svg"] = tasks_svg(tokens)
    files["widgets/viewitem.svg"] = viewitem_svg(tokens)
    files["widgets/menubaritem.svg"] = menubaritem_svg(tokens)
    files["widgets/lineedit.svg"] = lineedit_svg(tokens)
    files["widgets/plasmoidheading.svg"] = plasmoidheading_svg(tokens)

    vib = tokens["glass"]["vibrancy"]
    files["plasmarc"] = "\n".join([
        "# Generado por tools/gen_tokens.py — NO EDITAR",
        "[ContrastEffect]", "enabled=true",
        f"contrast={vib['contrast']}", f"intensity={vib['intensity']}", f"saturation={vib['saturation']}",
        "", "[BlurBehindEffect]", "enabled=true",
        "", "[AdaptiveTransparency]", "enabled=false",
        # Fondo por defecto (escritorios nuevos y pantalla de bloqueo).
        "", "[Wallpaper]", "defaultWallpaperTheme=GoldenGlass", "defaultFileSuffix=.jpg",
        "defaultWidth=5120", "defaultHeight=2880", "",
    ])
    files["metadata.json"] = json.dumps({
        "KPlugin": {
            "Authors": [{"Name": "GoldenGlass contributors"}],
            "Category": "",
            "Description": "Glass Plasma style inspired by macOS 27",
            "EnabledByDefault": True,
            "Id": THEME_ID,
            "License": "GPL-3.0-or-later",
            "Name": "GoldenGlass",
            "Version": tokens["meta"]["version"],
            "Website": "https://github.com/BuaxDEV/kde-golden-glass",
        },
        "X-Plasma-API": "5.0",
    }, indent=4) + "\n"

    written = []
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
