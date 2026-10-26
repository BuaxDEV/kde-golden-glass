# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Glyphs of third-party icons (icons_glyph.py), on synthetic QImages for each branch."""

from __future__ import annotations

import copy
import random
import re

import pytest
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPolygonF

import icons_apps
import icons_glyph
from gen_tokens import validate_icon_style
from icons_glyph import ExtractTokens, Kind
from icons_style import Style
from test_icon_styles import ACCENT, close, hex_rgb, render, rgb

SIZE = 128
WHITE, BLUE, ORANGE, BLACK = "#FFFFFF", "#0A84FF", "#FF9500", "#000000"
STAR = ((64, 6), (80, 46), (122, 46), (88, 72), (100, 120), (64, 94), (28, 120), (40, 72), (6, 46), (48, 46))


@pytest.fixture
def et(tokens) -> ExtractTokens:
    return ExtractTokens.from_tokens(tokens)


@pytest.fixture(autouse=True)
def _qt():
    import icons_mime
    icons_mime._app()


def canvas():
    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    return img


def paint(img, draw):
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    draw(p)
    p.end()
    return img


def color(value: str) -> QColor:
    return QColor(value)


def rounded_tile(fill, glyph=None):
    """A plain rounded tile (a shape that says nothing) with an optional glyph drawn on it."""
    def draw(p):
        p.setBrush(fill)
        p.drawRoundedRect(QRectF(8, 8, 112, 112), 26, 26)
        if glyph:
            glyph(p)
    return paint(canvas(), draw)


def bar_glyph(paint_color=WHITE):
    """An «L»: two bars, a symbol with a real outline."""
    def draw(p):
        p.setBrush(color(paint_color))
        p.drawRect(QRectF(40, 30, 14, 66))
        p.drawRect(QRectF(40, 82, 48, 14))
    return draw


def star(fill: str):
    def draw(p):
        p.setBrush(color(fill))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in STAR]))
    return paint(canvas(), draw)


def disc(fill: str):
    def draw(p):
        p.setBrush(color(fill))
        p.drawEllipse(QRectF(8, 8, 112, 112))
    return paint(canvas(), draw)


def horizontal_gradient(left: str, right: str):
    gradient = QLinearGradient(8, 0, 120, 0)
    gradient.setColorAt(0, color(left))
    gradient.setColorAt(1, color(right))
    return gradient


def noise():
    """A busy photo: random colours in 2 px blocks."""
    rng = random.Random(7)
    img = canvas()
    for y in range(0, SIZE, 2):
        for x in range(0, SIZE, 2):
            c = color(f"#{rng.randrange(1 << 24):06X}")
            for dy in (0, 1):
                for dx in (0, 1):
                    img.setPixelColor(x + dx, y + dy, c)
    return img


# --- the pipeline, branch by branch ---------------------------------------------------

def test_a_symbol_on_a_plain_tile_is_its_glyph_without_the_tile(et):
    glyph = icons_glyph.extract(rounded_tile(color(BLUE), bar_glyph()), "Lister", et)
    assert glyph.kind is Kind.GLYPH
    assert glyph.layer.plain_body and et.ink_min <= glyph.ink <= et.ink_max
    mask = glyph.mask(0.4, et)
    assert mask.startswith("<image ") and "data:image/png;base64," in mask


def test_a_horizontal_gradient_is_background(et):
    gradient = horizontal_gradient("#30D158", "#BF5AF2")
    plain = icons_glyph.extract(rounded_tile(gradient), "Gradient", et)
    assert plain.ink < et.ink_min      # nothing stands out of the gradient
    assert icons_glyph.extract(rounded_tile(gradient, bar_glyph()), "Gradient", et).kind is Kind.GLYPH


def test_a_plate_over_the_background_is_read_again_inside(et):
    """JetBrains-like: a black plate on a gradient, the letter on the plate."""
    def plate(p):
        p.setBrush(color(BLACK))
        p.drawRect(QRectF(16, 16, 96, 96))
        bar_glyph()(p)

    glyph = icons_glyph.extract(rounded_tile(horizontal_gradient(ORANGE, "#FF2D55"), plate), "IJ", et)
    assert glyph.kind is Kind.GLYPH
    # the reading inside the plate: the letter is a small part of it, not the whole plate
    assert glyph.ink < 0.5 and sum(glyph.layer.body) < 0.8 * sum(glyph.alpha)


def test_a_flat_distinctive_shape_falls_back_to_its_silhouette(et):
    glyph = icons_glyph.extract(star(ORANGE), "Star", et)
    assert glyph.ink < et.ink_min and glyph.outline_detail >= et.silhouette_detail_min
    assert glyph.kind is Kind.SILHOUETTE


def test_a_flat_plain_shape_falls_back_to_a_monogram(et):
    glyph = icons_glyph.extract(disc(BLUE), "  2048 game", et)
    assert glyph.outline_detail < et.silhouette_detail_min
    assert glyph.kind is Kind.MONOGRAM and glyph.letter == "2"
    mask = glyph.mask(0.4, et)
    assert mask.startswith('<path transform="translate(32 ') and 'fill="#FFFFFF"' in mask


def test_a_busy_photo_is_not_a_glyph(et):
    glyph = icons_glyph.extract(noise(), "photo", et)
    assert glyph.detail > et.detail_max
    assert glyph.kind is Kind.MONOGRAM and glyph.letter == "P"


def test_without_a_letter_the_icon_is_skipped(et):
    glyph = icons_glyph.extract(disc(BLUE), "★ ·", et)
    assert glyph.kind is Kind.SKIP and glyph.mask(0.4, et) == ""


@pytest.mark.parametrize("forced", list(Kind), ids=lambda k: k.value)
def test_an_override_wins(et, forced):
    glyph = icons_glyph.extract(rounded_tile(color(BLUE), bar_glyph()), "Lister", et, forced)
    assert glyph.kind is forced


def test_a_forced_monogram_without_a_letter_is_skipped(et):
    assert icons_glyph.extract(disc(BLUE), "…", et, Kind.MONOGRAM).kind is Kind.SKIP


def test_a_distinctive_body_stays_at_the_floor(et):
    """A star with a symbol inside: the star at the style's floor, the symbol in full."""
    def draw(p):
        bar_glyph(BLACK)(p)
    img = star(ORANGE)
    paint(img, draw)
    glyph = icons_glyph.extract(img, "Star", et)
    assert glyph.kind is Kind.GLYPH and not glyph.layer.plain_body
    floors = {round(a * (0.3 + 0.7 * s), 2) for a, s in zip(glyph.layer.body, glyph.layer.symbol) if a == 1}
    assert {0.3, 1.0} <= floors
    assert glyph.mask(0.3, et) != glyph.mask(0.6, et)


# --- pieces ----------------------------------------------------------------------------

@pytest.mark.parametrize("label, letter", [("Firefox", "F"), ("  zoom", "Z"), ("µTorrent", "Μ"), ("—", "")])
def test_initial(label, letter):
    assert icons_glyph.initial(label) == letter


def test_detail_is_scale_free_and_orders_shapes():
    def square(side):
        values = [0.0] * (SIZE * SIZE)
        for y in range(side):
            for x in range(side):
                values[(10 + y) * SIZE + 10 + x] = 1.0
        return values
    assert icons_glyph.detail(square(20), SIZE) == pytest.approx(icons_glyph.detail(square(80), SIZE), rel=0.02)
    assert icons_glyph.detail(square(40), SIZE) == pytest.approx(4.0, rel=0.05)
    assert icons_glyph.detail([0.0] * (SIZE * SIZE), SIZE) == 0


def test_fitted_image_centres_the_visible_part_in_the_box():
    values = [0.0] * (SIZE * SIZE)
    for y in range(10, 30):
        for x in range(90, 100):     # 10 × 20 px, far from the centre
            values[y * SIZE + x] = 1.0
    svg = icons_glyph.fitted_image(values, SIZE, 36)
    x, y, w, h = (float(v) for v in re.match(
        r'<image x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', svg).groups())
    assert (w, h) == (18, 36) and (x + w / 2, y + h / 2) == (32, 32)
    assert icons_glyph.fitted_image([0.0] * (SIZE * SIZE), SIZE, 36) == ""


def test_override_for_prefers_the_exact_name():
    table = {"google-chrome*": Kind.MONOGRAM, "google-chrome-beta": Kind.SKIP, "a*": Kind.GLYPH}
    assert icons_glyph.override_for("google-chrome", table) is Kind.MONOGRAM
    assert icons_glyph.override_for("google-chrome-beta", table) is Kind.SKIP
    assert icons_glyph.override_for("firefox", table) is None


def test_the_extracted_mask_paints_the_accent(et):
    """End to end: a Tinted dark tile paints the extracted symbol in the accent."""
    glyph = icons_glyph.extract(rounded_tile(color(BLUE), bar_glyph()), "Lister", et)
    body = icons_apps.styled_tile(glyph.mask(0.4, et), True, Style.TINTED)
    img = render(body)
    # the «L» is 36 units tall: its vertical bar spans x 19–26.5 units (38–53 px of the render)
    assert close(rgb(img.pixelColor(45, 64)), hex_rgb(ACCENT), 10)
    assert not close(rgb(img.pixelColor(80, 50)), hex_rgb(ACCENT), 40)


# --- tokens ------------------------------------------------------------------------------

def test_toml_has_exactly_the_extract_fields(tokens):
    assert set(tokens["icon_style"]["extract"]) == set(ExtractTokens.__dataclass_fields__)
    assert all(isinstance(k, Kind) for k in icons_glyph.overrides(tokens).values())


@pytest.mark.parametrize("key, value", [
    ("render_size", 16), ("render_size", 128.0), ("gamma", 0), ("ink_max", 1.5), ("glyph_size", 60),
    ("contrast_high", 0.05), ("detail_max", 1.0), ("monogram_font", ""), ("edge_samples", True),
])
def test_validate_rejects_bad_extract_values(tokens, key, value):
    style = copy.deepcopy(tokens["icon_style"])
    style["extract"][key] = value
    with pytest.raises(SystemExit, match=r"extract"):
        validate_icon_style(style)


def test_validate_rejects_unknown_overrides_and_missing_tables(tokens):
    style = copy.deepcopy(tokens["icon_style"])
    style["overrides"]["firefox"] = "hide"
    with pytest.raises(SystemExit, match="firefox"):
        validate_icon_style(style)
    for table in ("extract", "overrides"):
        style = copy.deepcopy(tokens["icon_style"])
        del style[table]
        with pytest.raises(SystemExit, match=table):
            validate_icon_style(style)
    style = copy.deepcopy(tokens["icon_style"])
    style["extract"]["unknown"] = 1
    with pytest.raises(SystemExit, match="unknown"):
        validate_icon_style(style)
