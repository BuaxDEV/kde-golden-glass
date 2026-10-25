# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tinted and Clear app icons (icons_style.py): tokens, glyph masks and rendered colours."""

from __future__ import annotations

import copy
import json

import pytest

import icons_apps
from gen_tokens import validate_icon_style
from icons_style import (ACCENT_CLASS, STYLE_JSON, ClearTokens, Style, StyleTokens, TintedTokens, theme_id,
                         theme_name)

STYLES = (Style.TINTED, Style.CLEAR)
ACCENT = "#AF52DE"


@pytest.fixture
def tt(tokens) -> icons_apps.TileTokens:
    return icons_apps.TileTokens.from_tokens(tokens)


@pytest.fixture
def st(tokens) -> StyleTokens:
    return StyleTokens.from_tokens(tokens)


@pytest.mark.parametrize("style, dark, expected", [
    (Style.DEFAULT, False, "GoldenGlass"), (Style.DEFAULT, True, "GoldenGlass-Dark"),
    (Style.CLEAR, False, "GoldenGlass-Clear"), (Style.CLEAR, True, "GoldenGlass-Clear-Dark"),
    (Style.TINTED, False, "GoldenGlass-Tinted"), (Style.TINTED, True, "GoldenGlass-Tinted-Dark"),
])
def test_theme_id(style, dark, expected):
    assert theme_id(style, dark) == expected
    assert theme_name(style, dark) == expected.replace("-", " ")


# --- glyph mask ------------------------------------------------------------------

def test_glyph_mask_whitens_the_glyph_and_cuts_the_details():
    mask = icons_apps.glyph_mask('<path fill="url(#fg)"/><circle stroke="url(#bg)"/>', 0.4)
    assert mask == '<path fill="#FFFFFF"/><circle stroke="#000000"/>'


@pytest.mark.parametrize("color, level", [("#FFFFFF", 0xFF), ("#000000", 0x66), ("#777777", 0xB3)])
def test_glyph_mask_keeps_the_lightness_of_fixed_colours_above_the_floor(color, level):
    mask = icons_apps.glyph_mask(f'<rect fill="{color}" stroke="{color}"/>', 0.4)
    grey = f"#{level:02X}{level:02X}{level:02X}"
    assert mask == f'<rect fill="{grey}" stroke="{grey}"/>'


@pytest.mark.parametrize("style", STYLES, ids=lambda s: s.value)
@pytest.mark.parametrize("dark", (False, True), ids=("light", "dark"))
def test_styled_svg_has_no_paint_that_ignores_currentcolor(tt, st, style, dark):
    """QtSvg ignores currentColor in stop-color and flood-color: the accent never goes there."""
    for app in icons_apps.APPS:
        svg = app.svg(dark, style, tt, st)
        assert 'stop-color="currentColor"' not in svg and 'flood-color="currentColor"' not in svg
        # the glyph's own paints became mask greys; only the tinted base keeps a gradient
        assert "url(#fg)" not in svg
        assert svg.count("url(#bg)") == (1 if style is Style.TINTED else 0)


def test_only_tinted_follows_the_accent(tt, st):
    for dark in (False, True):
        assert ACCENT_CLASS in icons_apps.APPS[0].svg(dark, Style.TINTED, tt, st)
        assert ACCENT_CLASS not in icons_apps.APPS[0].svg(dark, Style.CLEAR, tt, st)


def test_tile_with_a_style_draws_the_glyph_as_a_mask(tt, st):
    glyph = '<path fill="url(#fg)" d="M0 0"/>'
    assert icons_apps.tile(tt.white, tt.white, glyph, True, Style.TINTED, tt, st) == icons_apps.styled_tile(
        icons_apps.glyph_mask(glyph, st.tinted.glyph_floor), True, Style.TINTED, tt, st)


# --- rendered colours ---------------------------------------------------------------

def render(body: str, size: int = 128):
    import icons_mime
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    icons_mime._app()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="{icons_apps.XLINK_NS}" viewBox="0 0 64 64">'
           f'<defs><style type="text/css">.{ACCENT_CLASS}{{color:{ACCENT};}}</style></defs>{body}</svg>')
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    painter = QPainter(img)
    QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, size, size))
    painter.end()
    return img


def rgb(color) -> tuple[int, int, int]:
    return color.red(), color.green(), color.blue()


def hex_rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def mix(top: tuple, bottom: tuple, alpha: float) -> tuple[float, ...]:
    return tuple(t * alpha + b * (1 - alpha) for t, b in zip(top, bottom))


def close(actual: tuple, expected: tuple, tolerance: int = 6) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


# The Dolphin glyph is a folder: (64, 64) on a 128 px render is inside it, (64, 20) is tile above it.
GLYPH, TILE = (64, 70), (64, 22)


def test_tinted_dark_glyph_is_the_accent(tt, st):
    img = render(icons_apps.APPS[0].svg(True, Style.TINTED, tt, st))
    assert close(rgb(img.pixelColor(*GLYPH)), hex_rgb(ACCENT))


def test_tinted_light_glyph_is_the_accent_darkened(tt, st):
    img = render(icons_apps.APPS[0].svg(False, Style.TINTED, tt, st))
    expected = mix(hex_rgb(tt.shadow_color), hex_rgb(ACCENT), st.tinted.light_glyph_shade)
    assert close(rgb(img.pixelColor(*GLYPH)), expected)


def test_tinted_light_tile_is_the_accent_lightened(tt, st):
    img = render(icons_apps.APPS[0].svg(False, Style.TINTED, tt, st))
    tile = rgb(img.pixelColor(*TILE))
    accent = hex_rgb(ACCENT)
    white = (255, 255, 255)
    # between white and the accent, closer to white, and with the accent's hue (purple: blue > green)
    assert all(a <= t <= w for t, a, w in zip(tile, accent, white))
    assert sum(tile) > sum(mix(accent, white, 0.5)) and tile[2] > tile[1]


def test_clear_tile_is_translucent_and_its_glyph_white(tt, st):
    img = render(icons_apps.APPS[0].svg(True, Style.CLEAR, tt, st))
    # at most the fill under the full specular: the wallpaper still shows through
    c = st.clear
    assert 0 < img.pixelColor(*TILE).alpha() <= 255 * (1 - (1 - c.dark_fill_alpha) * (1 - c.specular_alpha)) + 2
    glyph = img.pixelColor(*GLYPH)
    assert len(set(rgb(glyph))) == 1 and glyph.red() > 235   # white over the dark glass
    assert glyph.alpha() >= round(255 * st.clear.glyph_alpha)


# --- tokens -----------------------------------------------------------------------

def _changed(value):
    if isinstance(value, list):
        return ["#123456", "#654321"]
    if isinstance(value, str):
        return "#123456"
    return value / 2 if value else 0.5


def styled_svgs(tokens) -> dict[str, str]:
    tt, st = icons_apps.TileTokens.from_tokens(tokens), StyleTokens.from_tokens(tokens)
    return {f"{app.names[0]}.{style.value}.{dark}": app.svg(dark, style, tt, st)
            for app in icons_apps.APPS for style in STYLES for dark in (False, True)}


@pytest.mark.parametrize("section, key", [
    *(("tinted", key) for key in TintedTokens.__dataclass_fields__),
    *(("clear", key) for key in ClearTokens.__dataclass_fields__),
])
def test_every_style_token_changes_the_svg(tokens, section, key):
    other = copy.deepcopy(tokens)
    other["icon_style"][section][key] = _changed(other["icon_style"][section][key])
    assert styled_svgs(other) != styled_svgs(tokens), f"{section}.{key}"


def test_styles_leave_the_default_drawing_alone(tokens):
    other = copy.deepcopy(tokens)
    for section in ("tinted", "clear"):
        for key, value in other["icon_style"][section].items():
            other["icon_style"][section][key] = _changed(value)
    assert icons_apps.files(other) == icons_apps.files(tokens)
    assert icons_apps.files(other, dark=True) == icons_apps.files(tokens, dark=True)


@pytest.mark.parametrize("section, key, value", [
    ("tinted", "light_wash_alpha", 1.5),
    ("tinted", "dark_background", ["#2C2C2E"]),
    ("tinted", "light_background", ["#FFFFFF", "#F2F2F780"]),
    ("clear", "glyph", "#FFF"),
    ("clear", "rim_width", 12),
    ("clear", "glyph_alpha", "0.9"),
])
def test_validate_rejects_bad_values(tokens, section, key, value):
    style = copy.deepcopy(tokens["icon_style"])
    style[section][key] = value
    with pytest.raises(SystemExit, match=key):
        validate_icon_style(style)


def test_validate_rejects_missing_tables_and_keys(tokens):
    style = copy.deepcopy(tokens["icon_style"])
    del style["clear"]
    with pytest.raises(SystemExit, match="clear"):
        validate_icon_style(style)
    style = copy.deepcopy(tokens["icon_style"])
    del style["tinted"]["glyph_floor"]
    with pytest.raises(SystemExit, match="glyph_floor"):
        validate_icon_style(style)


def test_validate_accepts_the_real_tokens(tokens):
    validate_icon_style(copy.deepcopy(tokens["icon_style"]))


# --- installed tokens (icon-style.json) ----------------------------------------------

def test_installed_json_gives_the_same_style_tokens(tokens, tmp_path, monkeypatch):
    data = tmp_path / "share"
    path = icons_apps.write_style_json(tokens, data / "goldenglass" / STYLE_JSON)
    assert json.loads(path.read_text(encoding="utf-8"))["icon_style"] == tokens["icon_style"]
    monkeypatch.setattr(icons_apps, "REPO_TOKENS", tmp_path / "no-such.toml")
    monkeypatch.setattr(icons_apps, "HERE", tmp_path / "tools")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_DATA_DIRS", str(data))
    icons_apps._default_style_tokens.cache_clear()
    try:
        assert icons_apps.style_tokens_source() == path
        assert icons_apps.style_tokens() == StyleTokens.from_tokens(tokens)
        assert icons_apps.color_scheme_fallback() == icons_apps.color_scheme_fallback(tokens)
    finally:
        icons_apps._default_style_tokens.cache_clear()


# --- contact sheet -------------------------------------------------------------------

def test_preview_draws_a_band_per_style_and_appearance(tmp_path):
    from PyQt6.QtGui import QImage

    path = tmp_path / "sheet.png"
    icons_apps.preview(path, (Style.DEFAULT, *STYLES), cols=8)
    img = QImage(str(path))
    rows = -(-len(icons_apps.APPS) // 8)
    assert (img.width(), img.height()) == (8 * 150, 6 * rows * 150)


def test_toml_has_exactly_the_fields_of_the_style_tokens(tokens):
    assert set(tokens["icon_style"]["tinted"]) == set(TintedTokens.__dataclass_fields__)
    assert set(tokens["icon_style"]["clear"]) == set(ClearTokens.__dataclass_fields__)
