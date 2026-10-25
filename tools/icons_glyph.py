# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Glyphs of third-party app icons for the Tinted and Clear styles.

A Tinted or Clear tile needs a monochrome glyph: a luminance mask (icons_apps.
styled_tile). GoldenGlass draws its own apps as masks; for any other app the
glyph comes from its installed, full-colour icon:

  1. render it at `render_size` px;
  2. model the background of each row from the solid pixels at each end of
     the row (blended in between, so a horizontal gradient is background),
     each end smoothed over `background_rows` rows;
  3. measure each pixel's contrast against its row, channel by channel;
  4. build the mask alpha·(floor + (1 − floor)·smoothstep(contrast)^gamma): the
     icon's body at the style's glyph floor and what stands out of it in full.
     A body that is a plain shape (square, circle, rounded tile) says nothing
     about the app and is left out (floor 0);
  5. check that the result reads as a symbol: `ink` (how much of the body
     stands out) and `detail` (outline length against the area: a busy photo
     has far too much, a soft shading far too little). When too much of the
     body stands out, read once more inside what stood out: a plate over the
     background (JetBrains' black square) is a body of its own;
  6. otherwise fall back to the silhouette (when the outline itself is
     distinctive), else to a monogram (initial of Name=), else to no styled
     icon at all (the parent theme's wrapped icon shows);
  7. [icon_style.overrides] forces any of those per icon name.

Pure Python (no numpy, it is not a dependency of the package); QImage renders
and gives the pixels. The tunables are the [icon_style.extract] tokens.

Review sheet of the installed apps, with the counts of each outcome:
  python3 tools/wrap_icons.py --sheet sheet.png [--accent '#AF52DE']
"""

from __future__ import annotations

import base64
import fnmatch
import math
import subprocess
from dataclasses import dataclass, replace
from enum import Enum
from functools import cache

CANVAS = 64            # icons_apps draws on a 64 unit canvas
SHAPE_ALPHA = 0.5      # a pixel this opaque belongs to the icon's outline
SOLID_ALPHA = 0.9      # only fully drawn pixels model the background: the antialiased rim is not its colour
VISIBLE = 0.02         # mask values below this stay out of the glyph's bounding box
WHITE = "#FFFFFF"      # full strength in a luminance mask


class Kind(Enum):
    """What a third-party icon becomes in a styled theme, in fallback order."""

    GLYPH = "glyph"              # its own symbol, from the contrast inside the icon
    SILHOUETTE = "silhouette"    # its outline
    MONOGRAM = "monogram"        # the initial of its Name=
    SKIP = "skip"                # no styled icon: the parent theme's wrapped one shows


@dataclass(frozen=True)
class ExtractTokens:
    """[icon_style.extract]."""

    render_size: int
    edge_samples: int
    background_rows: int
    contrast_low: float
    contrast_high: float
    gamma: float
    ink_min: float
    ink_max: float
    detail_min: float
    detail_max: float
    silhouette_detail_min: float
    glyph_size: float
    monogram_font: str
    monogram_size: float

    @classmethod
    def from_tokens(cls, tokens: dict) -> "ExtractTokens":
        return cls(**tokens["icon_style"]["extract"])


def overrides(tokens: dict) -> dict[str, Kind]:
    """[icon_style.overrides]: icon name or fnmatch pattern → forced outcome."""
    return {name: Kind(value) for name, value in tokens["icon_style"]["overrides"].items()}


def override_for(name: str, table: dict[str, Kind]) -> Kind | None:
    """The forced outcome of `name`: its exact entry, else the first matching pattern in sorted order."""
    if name in table:
        return table[name]
    return next((table[pattern] for pattern in sorted(table) if fnmatch.fnmatchcase(name, pattern)), None)


# --- pixels -------------------------------------------------------------------------

@dataclass(frozen=True)
class Pixels:
    """Unpremultiplied channels in 0..1 of a square render, row by row."""

    size: int
    red: tuple[float, ...]
    green: tuple[float, ...]
    blue: tuple[float, ...]
    alpha: tuple[float, ...]


def pixels(image, size: int) -> Pixels:
    """`image` (a QImage) fitted and centred in a transparent `size`×`size` square."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QImage, QPainter

    canvas = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(0)
    scaled = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    painter = QPainter(canvas)
    painter.drawImage((size - scaled.width()) // 2, (size - scaled.height()) // 2, scaled)
    painter.end()
    rgba = canvas.convertToFormat(QImage.Format.Format_RGBA8888)   # bytes R G B A, unpremultiplied
    data = rgba.constBits().asstring(size * size * 4)
    return Pixels(size, *(tuple(value / 255 for value in data[channel::4]) for channel in range(4)))


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


Color = tuple[float, float, float]


@dataclass(frozen=True)
class RowBackground:
    """Background of one row: a colour at each end of its solid span, blended in between
    (a horizontal gradient stays background)."""

    left: Color
    right: Color
    start: int    # first and last solid pixel of the row
    end: int

    def at(self, x: int) -> Color:
        t = min(1.0, max(0.0, (x - self.start) / max(1, self.end - self.start)))
        return tuple(a + (b - a) * t for a, b in zip(self.left, self.right))


def _smoothed(raw: list[Color | None], window: int) -> list[Color | None]:
    """Median over `window` rows, so that a symbol touching the end of a few rows is not background."""
    half = window // 2
    out: list[Color | None] = []
    for y in range(len(raw)):
        near = [color for color in raw[max(0, y - half):y + half + 1] if color is not None]
        out.append(tuple(_median([color[c] for color in near]) for c in range(3)) if near else None)
    return out


def row_background(px: Pixels, edge_samples: int, window: int) -> list[RowBackground | None]:
    """Background of each row from the median of its first and of its last
    `edge_samples` solid pixels, each end smoothed over `window` rows. None: no
    solid pixel in the row (it has no background to stand out of)."""
    n = px.size
    lefts: list[Color | None] = []
    rights: list[Color | None] = []
    spans: list[tuple[int, int] | None] = []
    for y in range(n):
        solid = [x for x in range(n) if px.alpha[y * n + x] >= SOLID_ALPHA]

        def colour(xs: list[int], row: int = y) -> Color:
            return tuple(_median([channel[row * n + x] for x in xs]) for channel in (px.red, px.green, px.blue))

        lefts.append(colour(solid[:edge_samples]) if solid else None)
        rights.append(colour(solid[-edge_samples:]) if solid else None)
        spans.append((solid[0], solid[-1]) if solid else None)
    lefts, rights = _smoothed(lefts, window), _smoothed(rights, window)
    return [RowBackground(left, right, *span) if span else None for left, right, span in zip(lefts, rights, spans)]


def smoothstep(low: float, high: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - low) / (high - low)))
    return t * t * (3 - 2 * t)


def symbol(px: Pixels, background: list[RowBackground | None], et: ExtractTokens) -> list[float]:
    """How much each pixel stands out of its row's background, 0..1: the largest
    channel difference through a smoothstep and the gamma (alpha not applied)."""
    n = px.size
    out = [0.0] * (n * n)
    for y, row in enumerate(background):
        if row is None:
            continue
        for x in range(n):
            i = y * n + x
            if px.alpha[i] > 0:
                bg = row.at(x)
                contrast = max(abs(px.red[i] - bg[0]), abs(px.green[i] - bg[1]), abs(px.blue[i] - bg[2]))
                out[i] = smoothstep(et.contrast_low, et.contrast_high, contrast) ** et.gamma
    return out


# --- legibility -----------------------------------------------------------------------

def ink(values: list[float], alpha: tuple[float, ...]) -> float:
    """Share of the icon's body that the mask `values` covers, 0..1."""
    body = sum(alpha)
    return sum(values) / body if body else 0.0


def detail(values: list[float] | tuple[float, ...], size: int) -> float:
    """Outline length over the square root of the area: scale-free, about 3.5 for
    a disc, 4 for a square, more for a symbol with holes and branches, tens for noise."""
    area = sum(values)
    if not area:
        return 0.0
    edge = 0.0
    for y in range(size):
        for x in range(size):
            i = y * size + x
            dx = values[i + 1] - values[i] if x + 1 < size else -values[i]
            dy = values[i + size] - values[i] if y + 1 < size else -values[i]
            edge += math.hypot(dx, dy)
    return edge / math.sqrt(area)


# --- glyph ---------------------------------------------------------------------------

def initial(label: str) -> str:
    """The monogram letter of an app name: its first letter or digit, upper case ("" if none)."""
    return next((c.upper() for c in label if c.isalnum()), "")


@dataclass(frozen=True)
class Layer:
    """One reading of the icon: a body (alpha) and how much each pixel stands out of it."""

    size: int
    body: tuple[float, ...]
    symbol: tuple[float, ...]
    ink: float
    detail: float
    plain_body: bool               # the body's outline is a plain shape: it is left out of the mask

    @property
    def marked(self) -> list[float]:
        return [a * s for a, s in zip(self.body, self.symbol)]

    def legible(self, et: ExtractTokens) -> bool:
        return et.ink_min <= self.ink <= et.ink_max and et.detail_min <= self.detail <= et.detail_max


def outline(alpha: tuple[float, ...]) -> tuple[float, ...]:
    """The icon's shape at full strength, keeping only the antialiasing of its edge."""
    return tuple(min(1.0, a / SHAPE_ALPHA) for a in alpha)


def read_layer(px: Pixels, et: ExtractTokens) -> Layer:
    """Steps 2 to 5 for the body given by the alpha of `px`."""
    standout = symbol(px, row_background(px, et.edge_samples, et.background_rows), et)
    marked = [a * s for a, s in zip(px.alpha, standout)]
    plain = detail(outline(px.alpha), px.size) < et.silhouette_detail_min
    return Layer(px.size, px.alpha, tuple(standout), ink(marked, px.alpha), detail(marked, px.size), plain)


@dataclass(frozen=True)
class Glyph:
    """The outcome for one icon; mask() draws it for a style's glyph floor."""

    kind: Kind
    layer: Layer                   # the reading the glyph comes from
    alpha: tuple[float, ...]       # the icon's own alpha, for the silhouette
    outline_detail: float
    letter: str

    @property
    def ink(self) -> float:
        return self.layer.ink

    @property
    def detail(self) -> float:
        return self.layer.detail

    def mask(self, floor: float, et: ExtractTokens) -> str:
        """Luminance-mask SVG on the 64 canvas ("" for SKIP)."""
        if self.kind is Kind.SKIP:
            return ""
        if self.kind is Kind.MONOGRAM:
            return monogram(self.letter, et)
        size = self.layer.size
        if self.kind is Kind.SILHOUETTE:
            return fitted_image(list(self.alpha), size, et.glyph_size)
        body = 0.0 if self.layer.plain_body else floor
        values = [a * (body + (1 - body) * s) for a, s in zip(self.layer.body, self.layer.symbol)]
        return fitted_image(values, size, et.glyph_size)


def extract(image, label: str, et: ExtractTokens, forced: Kind | None = None) -> Glyph:
    """The glyph of `image` (any QImage), or its fallback; `forced` is an override."""
    px = pixels(image, et.render_size)
    layer = read_layer(px, et)
    if layer.ink > et.ink_max:
        # Most of the body stands out: it may hold a plate of its own (JetBrains'
        # black square over a gradient). Read again inside what stood out.
        inner = read_layer(replace(px, alpha=tuple(layer.marked)), et)
        if inner.legible(et):
            layer = inner
    outline_detail = detail(outline(px.alpha), px.size)
    letter = initial(label)
    kind = forced or (Kind.GLYPH if layer.legible(et) else
                      Kind.SILHOUETTE if outline_detail >= et.silhouette_detail_min else
                      Kind.MONOGRAM if letter else Kind.SKIP)
    if kind is Kind.MONOGRAM and not letter:
        kind = Kind.SKIP
    return Glyph(kind, layer, px.alpha, outline_detail, letter)


def _bounds(values: list[float], size: int) -> tuple[int, int, int, int] | None:
    rows = [y for y in range(size) if any(v >= VISIBLE for v in values[y * size:(y + 1) * size])]
    cols = [x for x in range(size) if any(values[y * size + x] >= VISIBLE for y in range(size))]
    return (cols[0], rows[0], cols[-1] + 1, rows[-1] + 1) if rows else None


def fitted_image(values: list[float], size: int, box: float) -> str:
    """`values` (size×size, 0..1) cropped to what is visible, as a grey PNG fitted
    and centred in a `box` square of the 64 canvas ("" when nothing is visible)."""
    bounds = _bounds(values, size)
    if bounds is None:
        return ""
    left, top, right, bottom = bounds
    width, height = right - left, bottom - top
    scale = box / max(width, height)
    x, y = (CANVAS - width * scale) / 2, (CANVAS - height * scale) / 2
    grey = [bytes(round(255 * values[row * size + col]) for col in range(left, right)) for row in range(top, bottom)]
    return (f'<image x="{x:.2f}" y="{y:.2f}" width="{width * scale:.2f}" height="{height * scale:.2f}" '
            f'preserveAspectRatio="none" xlink:href="data:image/png;base64,{_grey_png(grey, width)}"/>')


def _grey_png(rows: list[bytes], width: int) -> str:
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
    from PyQt6.QtGui import QImage

    stride = (width + 3) & ~3   # QImage scanlines are 32-bit aligned
    data = b"".join(row + bytes(stride - width) for row in rows)
    image = QImage(data, width, len(rows), stride, QImage.Format.Format_Grayscale8).copy()
    buffer_data = QByteArray()
    buffer = QBuffer(buffer_data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return base64.b64encode(bytes(buffer_data)).decode()


@cache
def _font_family(name: str) -> str:
    """The real family behind a fontconfig alias such as «GoldenGlass Sans»."""
    try:
        return subprocess.run(["fc-match", "-f", "%{family[0]}", f"{name}:bold"],
                              capture_output=True, text=True, check=True).stdout or name
    except (OSError, subprocess.CalledProcessError):
        return name


def monogram(letter: str, et: ExtractTokens) -> str:
    """`letter` as a white path centred on the 64 canvas, `monogram_size` units tall (cap height)."""
    import icons_mime

    outline = icons_mime.text_path(letter, _font_family(et.monogram_font), et.monogram_size, et.glyph_size)
    baseline = CANVAS / 2 + et.monogram_size / 2
    return f'<path transform="translate({CANVAS // 2} {baseline:g})" d="{outline}" fill="{WHITE}"/>'
