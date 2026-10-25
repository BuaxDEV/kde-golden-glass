# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Iconos de aplicaciones de GoldenGlass, como los de macOS 27.

Cada app es un squircle (superelipse) con sombra, brillo y filo de vidrio:
  - claro: fondo en degradado del color de la app y símbolo blanco;
  - oscuro: fondo grafito y el símbolo con el degradado del color de la app
    (como el modo de iconos oscuros de macOS).
Algunas apps (Terminal, Calculadora…) tienen un dibujo propio en ambos modos.

Lienzo de 64; el squircle ocupa 6–58, como la rejilla de macOS (824/1024).
Las marcas de terceros no se dibujan: esas apps las encierra install.sh en un
squircle a partir de su icono instalado.

The Tinted and Clear styles (icons_style.py) redraw the same glyphs as a
luminance mask over their own tile: styled_tile() and glyph_mask().
"""

from __future__ import annotations

import json
import math
import os
import re
import tomllib
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable

import icons_mime
from icons_style import ACCENT_CLASS, STYLE_JSON, XLINK_NS, Style, StyleTokens

Pair = tuple[str, str]


def _alpha(value: float) -> str:
    """Opacidad SVG con dos decimales y sin el cero inicial: 0.3 → «.30»."""
    text = f"{value:.2f}"
    return text[1:] if text.startswith("0.") else text


def _length(value: float) -> str:
    """Medida SVG sin ceros sobrantes ni cero inicial: 1.30 → «1.3», 0.8 → «.8»."""
    text = f"{value:g}"
    return text[1:] if text.startswith("0.") else text


@dataclass(frozen=True)
class TileTokens:
    """La sección [icon_tile] de los tokens: todo lo visual del squircle."""

    white: Pair
    graphite: Pair
    paper: Pair
    wrap_paper: Pair
    highlight: str
    shadow_color: str
    shadow_blur: float
    shadow_dy: float
    shadow_alpha: float
    glyph_shadow_blur: float
    glyph_shadow_dy: float
    glyph_shadow_alpha: float
    sheen_light: float
    sheen_dark: float
    rim_width: float
    rim_top_light: float
    rim_top_dark: float
    rim_mid: float
    rim_bottom_light: float
    rim_bottom_dark: float
    edge_alpha: float
    edge_width: float

    @classmethod
    def from_tokens(cls, tokens: dict) -> "TileTokens":
        section = dict(tokens["icon_tile"])
        for key in ("white", "graphite", "paper", "wrap_paper"):
            top, bottom = section[key]
            section[key] = (top, bottom)
        return cls(**section)

    def filters(self) -> str:
        """Filtros de sombra del squircle (tileshadow) y del símbolo (glyphshadow)."""
        def shadow(fid: str, blur: float, dy: float, alpha: float) -> str:
            return (
                f'<filter id="{fid}" x="-20%" y="-20%" width="140%" height="140%" '
                'color-interpolation-filters="sRGB">'
                f'<feGaussianBlur in="SourceAlpha" stdDeviation="{_length(blur)}"/>'
                f'<feOffset dy="{_length(dy)}" result="b"/>'
                f'<feFlood flood-color="{self.shadow_color}" flood-opacity="{_alpha(alpha)}"/>'
                '<feComposite in2="b" operator="in"/>'
                '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
        return (shadow("tileshadow", self.shadow_blur, self.shadow_dy, self.shadow_alpha)
                + shadow("glyphshadow", self.glyph_shadow_blur, self.glyph_shadow_dy, self.glyph_shadow_alpha))


HERE = Path(__file__).resolve().parent
REPO_TOKENS = HERE.parent / "tokens" / "goldenglass.toml"   # solo existe en el repositorio
TILE_JSON = "icon-tile.json"                                  # lo genera icons.build()
SCHEME_FALLBACK_KEYS = ("accent", "label")                    # [light] keys of color_scheme_fallback()


def _data_dirs() -> list[Path]:
    home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return [home, *map(Path, os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"))]


def _tokens_source(json_name: str) -> Path | None:
    """The TOML of the repository (development), else the installed `json_name`
    (XDG_DATA_DIRS/goldenglass/ and next to tools/), or None."""
    if REPO_TOKENS.is_file():
        return REPO_TOKENS
    for path in (*(d / "goldenglass" / json_name for d in _data_dirs()), HERE.parent / json_name):
        if path.is_file():
            return path
    return None


def _load_tokens(json_name: str) -> dict:
    path = _tokens_source(json_name)
    if path is None:
        raise SystemExit(f"cannot find the icon tokens ({json_name} in $XDG_DATA_DIRS/goldenglass/ "
                         f"or tokens/goldenglass.toml): reinstall goldenglass-icons")
    if path.suffix == ".json":
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    with path.open("rb") as f:
        return tomllib.load(f)


def tile_tokens_source() -> Path | None:
    """Where [icon_tile] comes from: the repository TOML (development), else the installed
    icon-tile.json (XDG_DATA_DIRS/goldenglass/ and next to tools/), or None."""
    return _tokens_source(TILE_JSON)


def style_tokens_source() -> Path | None:
    """Where [icon_style] comes from: like tile_tokens_source(), with icon-style.json."""
    return _tokens_source(STYLE_JSON)


@lru_cache(maxsize=1)
def _default_tile_tokens() -> TileTokens:
    return TileTokens.from_tokens(_load_tokens(TILE_JSON))


@lru_cache(maxsize=1)
def _default_style_tokens() -> StyleTokens:
    return StyleTokens.from_tokens(_load_tokens(STYLE_JSON))


def tile_tokens(tokens: dict | None = None) -> TileTokens:
    """[icon_tile] de `tokens`, o de la fuente por defecto (ver tile_tokens_source)."""
    return TileTokens.from_tokens(tokens) if tokens is not None else _default_tile_tokens()


def style_tokens(tokens: dict | None = None) -> StyleTokens:
    """[icon_style] of `tokens`, or of the default source (see style_tokens_source)."""
    return StyleTokens.from_tokens(tokens) if tokens is not None else _default_style_tokens()


def write_tile_json(tokens: dict, path: Path) -> Path:
    """Writes [icon_tile] as JSON for the installed tools (no TOML, no ggcommon)."""
    return _write_json({"icon_tile": tokens["icon_tile"]}, path)


def style_token_data() -> dict:
    """The tokens that carry [icon_style] and the colour scheme fallback, from style_tokens_source()."""
    return _load_tokens(STYLE_JSON)


def color_scheme_fallback(tokens: dict | None = None) -> dict[str, str]:
    """Colours of the ColorScheme-* classes outside KDE (KIconLoader replaces them):
    the light accent and text of `tokens`, or of the default source."""
    light = (tokens if tokens is not None else style_token_data())["light"]
    return {"accent": light["accent"], "text": light["label"][:7]}


def write_style_json(tokens: dict, path: Path) -> Path:
    """Writes [icon_style] as JSON for the installed tools, with the light colours
    that color_scheme_fallback() needs; later subsections go along unchanged."""
    light = {key: tokens["light"][key] for key in SCHEME_FALLBACK_KEYS}
    return _write_json({"icon_style": tokens["icon_style"], "light": light}, path)


def _write_json(data: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _squircle(cx: float = 32, cy: float = 32, r: float = 26, n: float = 5.0, steps: int = 96) -> str:
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = cx + r * math.copysign(abs(c) ** (2 / n), c)
        y = cy + r * math.copysign(abs(s) ** (2 / n), s)
        pts.append(f"{x:.2f} {y:.2f}")
    return "M" + " L".join(pts) + " Z"


SQUIRCLE = _squircle()

def _grad(gid: str, top: str, bottom: str, y1: float = 6, y2: float = 58) -> str:
    return (f'<linearGradient id="{gid}" x1="0" y1="{y1}" x2="0" y2="{y2}" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>')


def _sheen(tt: TileTokens, top_alpha: str) -> str:
    return ('<linearGradient id="sheen" x1="0" y1="6" x2="0" y2="34" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{tt.highlight}" stop-opacity="{top_alpha}"/>'
            f'<stop offset="1" stop-color="{tt.highlight}" stop-opacity="0"/></linearGradient>')


def _rim(tt: TileTokens, top: str, mid: str, bottom: str, diagonal: bool = False) -> str:
    """Rim gradient: vertical, or from the top left corner (a specular edge) when `diagonal`."""
    x1, x2 = ("6", "58") if diagonal else ("0", "0")
    hi = tt.highlight
    return (f'<linearGradient id="rim" x1="{x1}" y1="6" x2="{x2}" y2="58" gradientUnits="userSpaceOnUse">'
            f'<stop offset="0" stop-color="{hi}" stop-opacity="{top}"/>'
            f'<stop offset=".5" stop-color="{hi}" stop-opacity="{mid}"/>'
            f'<stop offset="1" stop-color="{hi}" stop-opacity="{bottom}"/></linearGradient>')


def _outline(tt: TileTokens, shape: str = f'<path d="{SQUIRCLE}"') -> str:
    """Glass rim and the thin outer edge, on top of everything; `shape` opens the squircle element."""
    return (f'{shape} fill="none" stroke="url(#rim)" stroke-width="{_length(tt.rim_width)}"/>'
            f'{shape} fill="none" stroke="{tt.shadow_color}" stroke-opacity="{_alpha(tt.edge_alpha)}" '
            f'stroke-width="{_length(tt.edge_width)}"/>')


def tile(bg: Pair, fg: Pair, glyph: str, dark: bool, style: Style = Style.DEFAULT,
         tt: TileTokens | None = None, st: StyleTokens | None = None) -> str:
    """Squircle with the `bg` gradient and the glyph, painted with url(#fg), on top.

    The other styles ignore `bg` and `fg` and draw `glyph` as a mask (see glyph_mask)."""
    tt = tt or tile_tokens()
    if style is not Style.DEFAULT:
        st = st or style_tokens()
        return styled_tile(glyph_mask(glyph, st.glyph_floor(style)), dark, style, tt, st)
    sheen = _alpha(tt.sheen_dark if dark else tt.sheen_light)
    rim_top = _alpha(tt.rim_top_dark if dark else tt.rim_top_light)
    rim_bottom = _alpha(tt.rim_bottom_dark if dark else tt.rim_bottom_light)
    return (
        "<defs>" + tt.filters() + _grad("bg", *bg) + _grad("fg", *fg, y1=14, y2=50)
        + _sheen(tt, sheen) + _rim(tt, rim_top, _alpha(tt.rim_mid), rim_bottom)
        + "</defs>"
        f'<path d="{SQUIRCLE}" fill="url(#bg)" filter="url(#tileshadow)"/>'
        f'<path d="{SQUIRCLE}" fill="url(#sheen)"/>'
        f'<g filter="url(#glyphshadow)">{glyph}</g>'
        + _outline(tt)
    )


# --- Tinted and Clear (icons_style.py) -----------------------------------------

FIXED_PAINT = re.compile(r'\b(fill|stroke)="(#[0-9A-Fa-f]{6})"')
GLYPH_MASK_ID = "glyph"
SQUIRCLE_ID = "squircle"
# The squircle path is defined once and reused: a styled tile draws it five times.
SQUIRCLE_DEF = f'<path id="{SQUIRCLE_ID}" d="{SQUIRCLE}"/>'
SQUIRCLE_USE = f'<use xlink:href="#{SQUIRCLE_ID}"'


def _lightness(color: str) -> float:
    """CIE L* of an sRGB colour, in 0..1: how light the colour looks."""
    def linear(channel: int) -> float:
        c = channel / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    y = 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)
    return (116 * y ** (1 / 3) - 16) / 100 if y > 216 / 24389 else y * 24389 / 27 / 100


def _grey(level: float) -> str:
    value = round(255 * level)
    return f"#{value:02X}{value:02X}{value:02X}"


def glyph_mask(glyph: str, floor: float) -> str:
    """Luminance mask of a glyph drawn for the default tile: its own paint
    (url(#fg)) is white, the background details (url(#bg)) cut it, and each
    fixed colour keeps its lightness, never below `floor`."""
    keep_lightness = FIXED_PAINT.sub(
        lambda m: f'{m.group(1)}="{_grey(floor + (1 - floor) * _lightness(m.group(2)))}"', glyph)
    return keep_lightness.replace("url(#fg)", "#FFFFFF").replace("url(#bg)", "#000000")


def _masked(paint: str) -> str:
    return f'<rect width="64" height="64" {paint} mask="url(#{GLYPH_MASK_ID})"/>'


def styled_tile(mask: str, dark: bool, style: Style, tt: TileTokens | None = None,
                st: StyleTokens | None = None) -> str:
    """Tinted or Clear squircle whose glyph is the luminance mask `mask` (SVG on the 64 canvas)."""
    tt = tt or tile_tokens()
    st = st or style_tokens()
    mask_def = (f'<mask id="{GLYPH_MASK_ID}" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
                f'{mask}</mask>')
    return {Style.TINTED: _tinted, Style.CLEAR: _clear}[style](mask_def, dark, tt, st)


def _tinted(mask_def: str, dark: bool, tt: TileTokens, st: StyleTokens) -> str:
    t = st.tinted
    accent = f'class="{ACCENT_CLASS}" fill="currentColor"'
    wash = _alpha(t.dark_wash_alpha if dark else t.light_wash_alpha)
    # currentColor works in fills but not in stop-color: the lightened accent is
    # an accent wash over a light base, the darkened accent black over the glyph.
    shade = "" if dark else _masked(f'fill="{tt.shadow_color}" fill-opacity="{_alpha(t.light_glyph_shade)}"')
    sheen = _alpha(tt.sheen_dark if dark else tt.sheen_light)
    rim_top = _alpha(tt.rim_top_dark if dark else tt.rim_top_light)
    rim_bottom = _alpha(tt.rim_bottom_dark if dark else tt.rim_bottom_light)
    return (
        "<defs>" + SQUIRCLE_DEF + tt.filters() + _grad("bg", *(t.dark_background if dark else t.light_background))
        + _sheen(tt, sheen) + _rim(tt, rim_top, _alpha(tt.rim_mid), rim_bottom) + mask_def + "</defs>"
        f'{SQUIRCLE_USE} fill="url(#bg)" filter="url(#tileshadow)"/>'
        f'{SQUIRCLE_USE} {accent} fill-opacity="{wash}"/>'
        f'{SQUIRCLE_USE} fill="url(#sheen)"/>'
        f'<g filter="url(#glyphshadow)">{_masked(accent)}{shade}</g>'
        + _outline(tt, SQUIRCLE_USE)
    )


def _clear(mask_def: str, dark: bool, tt: TileTokens, st: StyleTokens) -> str:
    c = st.clear
    glass = replace(tt, glyph_shadow_blur=c.glyph_shadow_blur, glyph_shadow_alpha=c.glyph_shadow_alpha,
                    rim_width=c.rim_width)
    fill, fill_alpha = (c.dark_fill, c.dark_fill_alpha) if dark else (c.light_fill, c.light_fill_alpha)
    glyph_paint = f'fill="{c.glyph}" fill-opacity="{_alpha(c.glyph_alpha)}"'
    return (
        "<defs>" + SQUIRCLE_DEF + glass.filters() + _sheen(glass, _alpha(c.specular_alpha))
        + _rim(glass, _alpha(c.rim_top), _alpha(c.rim_mid), _alpha(c.rim_bottom), diagonal=True)
        + mask_def + "</defs>"
        f'{SQUIRCLE_USE} fill="{fill}" fill-opacity="{_alpha(fill_alpha)}" filter="url(#tileshadow)"/>'
        f'{SQUIRCLE_USE} fill="url(#sheen)"/>'
        f'<g filter="url(#glyphshadow)">{_masked(glyph_paint)}</g>'
        + _outline(glass, SQUIRCLE_USE)
    )


@dataclass(frozen=True)
class App:
    names: tuple[str, ...]
    tint: Pair | None                     # degradado del color de la app (arriba, abajo); None con custom
    glyph: Callable[[bool], str]          # símbolo; pinta con url(#fg) (o colores propios)
    custom: Callable[[bool, TileTokens], tuple[Pair, Pair]] | None = None  # (bg, fg) propios

    def svg(self, dark: bool, style: Style = Style.DEFAULT, tt: TileTokens | None = None,
            st: StyleTokens | None = None) -> str:
        tt = tt or tile_tokens()
        if style is not Style.DEFAULT:
            st = st or style_tokens()
            # the dark drawing of a glyph is the light-on-dark one, the shape a mask needs
            return styled_tile(glyph_mask(self.glyph(True), st.glyph_floor(style)), dark, style, tt, st)
        if self.custom:
            bg, fg = self.custom(dark, tt)
        else:
            bg, fg = (tt.graphite, self.tint) if dark else (self.tint, tt.white)
        return tile(bg, fg, self.glyph(dark), dark, style, tt)


F = 'fill="url(#fg)"'
S = 'fill="none" stroke="url(#fg)" stroke-linecap="round" stroke-linejoin="round"'


def _const(svg: str) -> Callable[[bool], str]:
    return lambda dark: svg


# --- símbolos -----------------------------------------------------------------

FOLDER = (f'<path {F} d="M15 22 Q15 18.5 18.5 18.5 H26 L29.5 22 H45.5 Q49 22 49 25.5 V42.5 Q49 46 45.5 46 '
          f'H18.5 Q15 46 15 42.5 Z"/>'
          '<path d="M15 27 H49" stroke="#000000" stroke-opacity=".12" stroke-width="1"/>')

GEAR = (f'<path {F} fill-rule="evenodd" d="' + "".join(
    f"{'M' if i == 0 else 'L'}{32 + r * math.cos(math.radians(a)):.2f} {32 + r * math.sin(math.radians(a)):.2f} "
    for i, (a, r) in enumerate(
        (deg + off, rad) for deg in range(0, 360, 30)
        for off, rad in ((-8, 13.5), (-5, 17.5), (5, 17.5), (8, 13.5)))
) + 'Z M32 25.5 A6.5 6.5 0 1 0 32 38.5 A6.5 6.5 0 1 0 32 25.5 Z"/>')


def terminal_custom(dark: bool, tt: TileTokens):
    return (("#2C2C2E", "#0E0E10") if dark else ("#4A4A4E", "#1C1C1F")), ("#FFFFFF", "#D8D8DC")


def terminal(prompt: str = "#FFFFFF", extra: str = "") -> Callable[[bool], str]:
    return _const(
        f'<path d="M19 24 L26 30 L19 36" fill="none" stroke="{prompt}" stroke-width="3.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M30 37.5 H42" stroke="{prompt}" stroke-width="3.2" stroke-linecap="round"/>' + extra)


def calculator(dark: bool) -> str:
    keys = []
    for row in range(4):
        for col in range(3):
            x, y = 17 + col * 10.5, 25 + row * 6.6
            color = "#FF9F0A" if col == 2 else ("#A5A5AA" if row == 0 else "#5A5A5E")
            keys.append(f'<rect x="{x}" y="{y}" width="9" height="5.2" rx="2.6" fill="{color}"/>')
    return ('<rect x="17" y="15" width="30" height="7.5" rx="2" fill="#000000" fill-opacity=".35"/>'
            '<path d="M43 20.6 V16.9" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round"/>'
            + "".join(keys))


INK = 'fill="url(#bg)"'                 # «tinta»: el fondo, para detalles sobre el símbolo
INK_S = 'fill="none" stroke="url(#bg)" stroke-linecap="round" stroke-linejoin="round"'


def _arc(cx, cy, r, a0, a1) -> str:
    """Arco SVG de a0 a a1 grados (0 = arriba, sentido horario)."""
    def pt(a):
        t = math.radians(a - 90)
        return f"{cx + r * math.cos(t):.2f} {cy + r * math.sin(t):.2f}"
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{pt(a0)} A{r} {r} 0 {large} 1 {pt(a1)}"


PAGE = f'<rect x="19" y="13.5" width="26" height="37" rx="3.5" {F}/>'

KATE = PAGE + (f'<path {INK_S} stroke-width="2.6" d="M27.5 25 L22.8 30.5 L27.5 36 M36.5 25 L41.2 30.5 L36.5 36 '
               'M33.6 22.5 L30.4 38.5"/>')
KWRITE = PAGE + f'<path {INK_S} stroke-width="2.4" d="M24 22 H40 M24 28 H40 M24 34 H40 M24 40 H33"/>'
SPECTACLE = (f'<path {S} stroke-width="3.4" d="M16 24 V19 Q16 16 19 16 H24 M40 16 H45 Q48 16 48 19 V24 '
             'M48 40 V45 Q48 48 45 48 H40 M24 48 H19 Q16 48 16 45 V40"/>'
             f'<circle cx="32" cy="32" r="6.5" {F}/><circle cx="32" cy="32" r="2.6" {INK}/>')
GWENVIEW = (f'<rect x="14.5" y="18" width="35" height="28" rx="4.5" {F}/>'
            f'<path {INK} d="M18.5 42 L27 31.5 L33 38 L37.5 33 L45.5 42 Z"/><circle cx="40" cy="25.5" r="3" {INK}/>')
ARK = (f'<rect x="14.5" y="16" width="35" height="8" rx="2.5" {F}/>'
       f'<path {F} d="M17 26 H47 V44.5 Q47 48 43.5 48 H20.5 Q17 48 17 44.5 Z"/>'
       f'<rect x="27" y="29.5" width="10" height="4" rx="2" {INK}/>')
HARUNA = f'<circle cx="32" cy="32" r="15" {S} stroke-width="3.2"/><path {F} d="M28 24.5 L40.5 32 L28 39.5 Z"/>'
PARTITION = (f'<circle cx="32" cy="32" r="16" {F}/><path {INK} d="M32 32 V16 A16 16 0 0 1 47.2 27 Z"/>'
             f'<circle cx="32" cy="32" r="3" {INK}/>')
INFO = (f'<circle cx="32" cy="32" r="16" {S} stroke-width="3.2"/><circle cx="32" cy="24" r="2.6" {F}/>'
        f'<rect x="29.6" y="29" width="4.8" height="13" rx="2.4" {F}/>')
CONNECT = (f'<rect x="22.5" y="13.5" width="19" height="37" rx="4.5" {F}/>'
           f'<rect x="25" y="18" width="14" height="25.5" rx="1.5" {INK}/>'
           f'<path {S} stroke-width="2.4" d="M28 30.5 L31 33.5 L36.5 27"/>')
WALLET = (f'<circle cx="24" cy="32" r="8.5" {F}/><circle cx="21.5" cy="32" r="2.6" {INK}/>'
          f'<path {F} d="M30 29.6 H48 Q49.5 29.6 49.5 31.1 V32.9 Q49.5 34.4 48 34.4 H46 V38.5 H42.5 V34.4 '
          'H40 V37.5 H36.5 V34.4 H30 Z"/>')
EMOJI = (f'<circle cx="32" cy="32" r="15.5" {S} stroke-width="3.2"/>'
         f'<ellipse cx="26.5" cy="28" rx="2.2" ry="3" {F}/><ellipse cx="37.5" cy="28" rx="2.2" ry="3" {F}/>'
         f'<path {S} stroke-width="3" d="M24.5 36 Q32 43.5 39.5 36"/>')
MENUEDIT = "".join(f'<circle cx="19.5" cy="{y}" r="2.6" {F}/><rect x="25" y="{y - 2.2}" width="21" height="4.4" '
                   f'rx="2.2" {F}/>' for y in (21, 32, 43))
KLIPPER = (f'<rect x="17" y="17" width="30" height="33" rx="4" {F}/>'
           f'<rect x="25" y="13.5" width="14" height="7.5" rx="2.5" {F}/>'
           f'<rect x="27" y="15.5" width="10" height="3.5" rx="1.5" {INK}/>'
           f'<path {INK_S} stroke-width="2.4" d="M23 29 H41 M23 35 H41 M23 41 H34"/>')
THEME = (f'<rect x="15" y="15" width="24" height="24" rx="5" {F} fill-opacity=".55"/>'
         f'<rect x="25" y="25" width="24" height="24" rx="5" {F}/>'
         f'<path d="M27.5 28 H46.5" stroke="#FFFFFF" stroke-opacity=".6" stroke-width="1" stroke-linecap="round"/>')
HELLO = (f'<path {F} d="M14.5 21 Q14.5 15.5 20 15.5 H44 Q49.5 15.5 49.5 21 V36 Q49.5 41.5 44 41.5 H28 L20 48.5 '
         'V41.5 Q14.5 41.5 14.5 36 Z"/>'
         + "".join(f'<circle cx="{x}" cy="28.5" r="2.6" {INK}/>' for x in (24, 32, 40)))
KERNEL = (f'<path {S} stroke-width="2.6" d="M26 13.5 V18 M32 13.5 V18 M38 13.5 V18 M26 46 V50.5 M32 46 V50.5 '
          'M38 46 V50.5 M13.5 26 H18 M13.5 32 H18 M13.5 38 H18 M46 26 H50.5 M46 32 H50.5 M46 38 H50.5"/>'
          f'<rect x="18" y="18" width="28" height="28" rx="4.5" {F}/><rect x="25" y="25" width="14" height="14" '
          f'rx="2.5" {INK}/>')
SCX = (f'<path {S} stroke-width="3.4" d="{_arc(32, 35, 15, -120, 120)}"/>'
       f'<path {F} d="M30.6 36.4 L42 25 L33.4 39.2 Z"/><circle cx="32" cy="37" r="3.2" {F}/>')
UPDATE = (f'<path {S} stroke-width="3.2" d="{_arc(32, 32, 14.5, 40, 320)}"/>'
          f'<path {F} d="M41.6 14.6 L44.8 24.4 L34.6 22.8 Z"/>'
          f'<path {S} stroke-width="3" d="M32 24 V38.5 M26.5 33 L32 38.5 L37.5 33"/>')
MELD = (f'<rect x="14" y="16" width="15" height="32" rx="3" {F}/><rect x="35" y="16" width="15" height="32" '
        f'rx="3" {F}/><path {INK_S} stroke-width="2" d="M17.5 23 H25.5 M17.5 28 H25.5 M38.5 33 H46.5 M38.5 38 H46.5"/>'
        f'<path {S} stroke-width="2.2" d="M29.5 32 H34.5"/>')
PAVU = "".join(f'<path {S} stroke-width="2.6" d="M{x} 16 V48"/><rect x="{x - 4.5}" y="{y}" width="9" height="6" '
               f'rx="3" {F}/>' for x, y in ((21, 34), (32, 21), (43, 29)))
KVANTUM = (f'<path {F} d="M32 14 C43 14 51 21.5 51 30 C51 36 46.5 38 42.5 37 C39 36 37 38 38 41.5 C39 45.5 37 50 32 50 '
           'C21 50 13 42 13 32 C13 22 21 14 32 14 Z"/>'
           + "".join(f'<circle cx="{x}" cy="{y}" r="2.9" {INK}/>' for x, y in ((23, 27), (31, 21.5), (40, 24.5), (22, 37))))
BTRFS = "".join(f'<path {F} fill-opacity="{o}" d="M32 {y} L48 {y + 7} L32 {y + 14} L16 {y + 7} Z"/>'
                for y, o in ((30, ".55"), (24, ".8"), (18, "1")))
GHOST = (f'<path {F} d="M19 30 Q19 16 32 16 Q45 16 45 30 V47 L41 44 L36.5 47.5 L32 44 L27.5 47.5 L23 44 L19 47 Z"/>'
         f'<ellipse cx="27" cy="30" rx="2.4" ry="3.4" {INK}/><ellipse cx="37" cy="30" rx="2.4" ry="3.4" {INK}/>')


def monitor(dark: bool) -> str:
    grid = "".join(f'<path d="M15 {y} H49" stroke="#FFFFFF" stroke-opacity=".08" stroke-width=".8"/>'
                   for y in (22, 30, 38, 46))
    return (grid + '<path d="M14 38 L20 38 L23.5 28 L28 44 L32.5 22 L36.5 36 L40 31 L43 38 L50 38" fill="none" '
            'stroke="#30D158" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')


def btop(dark: bool) -> str:
    bars = (("#30D158", 30), ("#30D158", 22), ("#FFD60A", 16), ("#FF9F0A", 26), ("#30D158", 34), ("#FF453A", 19))
    return "".join(f'<rect x="{15.5 + i * 5.7:.1f}" y="{y}" width="4" height="{47 - y}" rx="1.4" fill="{c}"/>'
                   for i, (c, y) in enumerate(bars))


def filelight(dark: bool) -> str:
    colors = ("#0A84FF", "#30D158", "#FFD60A", "#FF9F0A", "#FF453A", "#BF5AF2")
    spans = (0, 95, 160, 210, 255, 300, 360)
    rings = "".join(f'<path d="{_arc(32, 32, 12.5, spans[i] + 2, spans[i + 1] - 2)}" fill="none" stroke="{c}" '
                    f'stroke-width="7"/>' for i, c in enumerate(colors))
    outer = "".join(f'<path d="{_arc(32, 32, 18.5, a0 + 2, a1 - 2)}" fill="none" stroke="{c}" stroke-opacity=".55" '
                    f'stroke-width="3.6"/>' for a0, a1, c in ((0, 60, "#0A84FF"), (95, 140, "#30D158"),
                                                               (210, 240, "#FF9F0A"), (300, 345, "#BF5AF2")))
    return rings + outer


def color_wheel(dark: bool) -> str:
    import colorsys
    out = []
    for i in range(12):
        r, g, b = colorsys.hsv_to_rgb(i / 12, 0.8, 1.0)
        out.append(f'<path d="{_arc(32, 32, 12, i * 30 + 1.5, (i + 1) * 30 - 1.5)}" fill="none" '
                   f'stroke="#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}" stroke-width="9"/>')
    return "".join(out) + f'<circle cx="32" cy="32" r="5" fill="{"#3A3A3E" if dark else "#FFFFFF"}"/>'


def fonts(dark: bool) -> str:
    d = icons_mime.text_path("Aa", "Inter", 17, 34)
    return f'<path transform="translate(32 40.5)" d="{d}" fill="{"#FFFFFF" if dark else "#1C1C1E"}"/>'


def _custom_dark(top: str = "#2C2C2E", bottom: str = "#111113"):
    return lambda dark, tt: ((("#2C2C2E", "#0E0E10") if dark else (top, bottom)), tt.white)


def _custom_paper(dark: bool, tt: TileTokens):
    return (tt.graphite if dark else tt.paper), tt.white


def apps_grid(dark: bool) -> str:
    """Icono de Apps (el lanzador del dock): cuadrícula de 3×3 apps de colores."""
    colors = ("#FF5F57", "#FEBC2E", "#28C840", "#5AC8FA", "#007AFF", "#AF52DE", "#FF9500", "#34C759", "#FF2D55")
    side, gap, start = 8.4, 2.8, 17.2
    return "".join(f'<rect x="{start + (i % 3) * (side + gap):.1f}" y="{start + (i // 3) * (side + gap):.1f}" '
                   f'width="{side}" height="{side}" rx="2.4" fill="{c}"/>' for i, c in enumerate(colors))


APPS: tuple[App, ...] = (
    App(("org.kde.dolphin", "dolphin", "system-file-manager"), ("#5AC8FA", "#0A6CFF"), _const(FOLDER)),
    App(("utilities-terminal", "org.kde.konsole", "konsole", "terminal"), None, terminal(), custom=terminal_custom),
    App(("preferences-system", "systemsettings", "org.kde.systemsettings"), ("#AEAEB2", "#636366"), _const(GEAR)),
    App(("accessories-calculator", "kcalc", "org.kde.kcalc"), None, calculator,
        custom=_custom_dark("#58585C", "#2C2C2E")),
    App(("kate", "org.kde.kate"), ("#8E8CFF", "#4B48C8"), _const(KATE)),
    App(("kwrite", "org.kde.kwrite", "accessories-text-editor"), ("#FFB340", "#FF8A00"), _const(KWRITE)),
    App(("spectacle", "org.kde.spectacle"), ("#FF7A7A", "#E0303A"), _const(SPECTACLE)),
    App(("gwenview", "org.kde.gwenview"), ("#5BE07A", "#1FA548"), _const(GWENVIEW)),
    App(("ark", "org.kde.ark", "utilities-file-archiver"), ("#D6AE80", "#94704A"), _const(ARK)),
    App(("haruna", "org.kde.haruna"), ("#F06BD2", "#B5179E"), _const(HARUNA)),
    App(("utilities-system-monitor", "org.kde.plasma-systemmonitor", "ksysguard"), None, monitor,
        custom=_custom_dark("#3A3A3E", "#141416")),
    App(("filelight", "org.kde.filelight"), None, filelight, custom=_custom_paper),
    App(("partitionmanager", "org.kde.partitionmanager"), ("#A0AEC0", "#5A6B85"), _const(PARTITION)),
    App(("hwinfo", "org.kde.kinfocenter", "kinfocenter"), ("#4DA3FF", "#0A5FD8"), _const(INFO)),
    App(("kdeconnect", "org.kde.kdeconnect.app", "org.kde.kdeconnect"), ("#7AD7F0", "#2D8FD0"), _const(CONNECT)),
    App(("kwalletmanager", "org.kde.kwalletmanager"), ("#C7CBD1", "#7C838D"), _const(WALLET)),
    App(("kfontview", "org.kde.kfontview", "kfontinst"), None, fonts, custom=_custom_paper),
    App(("preferences-desktop-emoticons", "org.kde.plasma.emojier"), ("#FFD60A", "#FF9F0A"), _const(EMOJI)),
    App(("kmenuedit", "org.kde.kmenuedit"), ("#8C9BB4", "#4B5A70"), _const(MENUEDIT)),
    App(("klipper", "org.kde.klipper"), ("#63E6BE", "#12B886"), _const(KLIPPER)),
    App(("preferences-desktop-theme", "goldenglass-settings"), ("#F7C76B", "#D98E2B"), _const(THEME)),
    App(("goldenglass-apps",), None, apps_grid, custom=_custom_paper),
    App(("preferences-desktop-color", "org.kde.kcolorschemeeditor"), None, color_wheel, custom=_custom_paper),
    App(("org.cachyos.hello", "cachyos-hello"), ("#2EE6C0", "#00897B"), _const(HELLO)),
    App(("org.cachyos.KernelManager",), ("#4CD964", "#1E8E3E"), _const(KERNEL)),
    App(("org.cachyos.scx-manager",), ("#FFAA33", "#E8590C"), _const(SCX)),
    App(("cachy-update-blue", "arch-update"), ("#6EA8FF", "#2F5BEA"), _const(UPDATE)),
    App(("Alacritty", "alacritty"), None, terminal("#FF9F0A"), custom=terminal_custom),
    App(("kitty",), None, terminal("#FFD60A", '<path d="M18 21 L21 15.5 L24 21 M40 21 L43 15.5 L46 21" '
                                     'fill="none" stroke="#FFD60A" stroke-width="2.2" stroke-linejoin="round" '
                                     'stroke-linecap="round"/>'), custom=terminal_custom),
    App(("com.mitchellh.ghostty", "ghostty"), ("#6B7BFF", "#2B3496"), _const(GHOST)),
    App(("foot",), None, terminal("#64D2FF"), custom=terminal_custom),
    App(("btop",), None, btop, custom=_custom_dark("#3A3A3E", "#141416")),
    App(("org.gnome.Meld", "meld"), ("#A3E635", "#4D7C0F"), _const(MELD)),
    App(("org.pulseaudio.pavucontrol", "pavucontrol", "multimedia-volume-control"), ("#FF7AB6", "#D6336C"),
        _const(PAVU)),
    App(("kvantum",), ("#B197FC", "#7048E8"), _const(KVANTUM)),
    App(("btrfs-assistant",), ("#C0CA33", "#7C8A12"), _const(BTRFS)),
)


def files(tokens: dict | None = None, style: Style = Style.DEFAULT,
          dark: bool = False) -> list[tuple[str, str, tuple[str, ...]]]:
    """(relative path, SVG body on the 64 canvas, aliases) of every app; `tokens` defaults to goldenglass.toml."""
    tt = tile_tokens(tokens)
    return [(f"apps/scalable/{app.names[0]}.svg", app.svg(dark, style, tt), app.names[1:]) for app in APPS]


PREVIEW_BACKDROPS = {False: "#E8E8ED", True: "#1E1E22"}           # window colours behind the icons
PREVIEW_WALLPAPER = ("#F5A15C", "#D9788A", "#5B5FA6", "#1B2A4A")   # a stand-in for the Clear backdrop
PREVIEW_ACCENT = "#007AFF"


def preview(path, styles: tuple[Style, ...] = (Style.DEFAULT,), cols: int = 8, accent: str = PREVIEW_ACCENT) -> None:
    """Contact sheet: each app at 128 and 32 px, a light and a dark band per style.

    The accent replaces ColorScheme-Accent as KIconLoader would. Clear bands sit
    on a wallpaper-like gradient on their right half, to show the translucency."""
    icons_mime._app()
    from PyQt6.QtCore import QByteArray, QPointF, QRectF
    from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    cell = 150
    rows = -(-len(APPS) // cols)
    band_h = rows * cell
    bands = [(style, dark) for style in styles for dark in (False, True)]
    img = QImage(cols * cell, band_h * len(bands), QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    scheme = f'<style type="text/css">.{ACCENT_CLASS}{{color:{accent};}}</style>'
    for band, (style, dark) in enumerate(bands):
        top = band * band_h
        p.fillRect(0, top, cols * cell, band_h, QColor(PREVIEW_BACKDROPS[dark]))
        if style is Style.CLEAR:
            half = cols * cell // 2
            wallpaper = QLinearGradient(QPointF(half, top), QPointF(cols * cell, top + band_h))
            for i, color in enumerate(PREVIEW_WALLPAPER):
                wallpaper.setColorAt(i / (len(PREVIEW_WALLPAPER) - 1), QColor(color))
            p.fillRect(half, top, cols * cell - half, band_h, wallpaper)
        for i, app in enumerate(APPS):
            x, y = (i % cols) * cell, top + (i // cols) * cell
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="{XLINK_NS}" viewBox="0 0 64 64">'
                   f'<defs>{scheme}</defs>{app.svg(dark, style)}</svg>')
            r = QSvgRenderer(QByteArray(svg.encode()))
            r.render(p, QRectF(x + 2, y + 2, 112, 112))
            r.render(p, QRectF(x + 116, y + 82, 32, 32))
    p.end()
    img.save(str(path))


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", type=Path, required=True)
    ap.add_argument("--style", action="append", choices=[s.value for s in Style],
                    help="estilo de la hoja (se puede repetir; por defecto, el de fábrica)")
    ap.add_argument("--accent", default=PREVIEW_ACCENT, help="color de acento (#RRGGBB)")
    args = ap.parse_args()
    preview(args.preview, tuple(Style(s) for s in args.style or [Style.DEFAULT.value]), accent=args.accent)
