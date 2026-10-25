# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""gen_tokens: colores de los tokens y esquemas de color de KDE (.colors)."""

from __future__ import annotations

import configparser
import re

import pytest

from gen_tokens import VARIANTS, Color, build_colors


def rgb(c: Color) -> tuple[int, int, int]:
    return (c.r, c.g, c.b)


# --- Color --------------------------------------------------------------------

def test_parse_rgb():
    c = Color.parse("#FF8000")
    assert rgb(c) == (255, 128, 0)
    assert c.a == 1.0


def test_parse_rgba_and_without_hash():
    c = Color.parse("0a141e80")
    assert rgb(c) == (10, 20, 30)
    assert c.a == pytest.approx(128 / 255)


@pytest.mark.parametrize("value", ["", "#FFF", "#FFFFF", "#FFFFFFF", "#GG0000", "#FFFFFFFFFF"])
def test_parse_invalid(value):
    with pytest.raises(ValueError):
        Color.parse(value)


def test_over_flattens_alpha():
    white_half = Color.parse("#FFFFFF80")
    assert rgb(white_half.over(Color.parse("#000000"))) == (128, 128, 128)
    # opaco: queda igual; transparente: el fondo
    assert rgb(Color.parse("#123456").over(Color.parse("#FFFFFF"))) == (0x12, 0x34, 0x56)
    assert rgb(Color.parse("#12345600").over(Color.parse("#ABCDEF"))) == (0xAB, 0xCD, 0xEF)


def test_mix():
    black, white = Color.parse("#000000"), Color.parse("#FFFFFF")
    assert rgb(black.mix(white, 0)) == (0, 0, 0)
    assert rgb(black.mix(white, 1)) == (255, 255, 255)
    assert rgb(black.mix(white, 0.25)) == (64, 64, 64)


def test_kde():
    assert Color.parse("#FF8000").kde() == "255,128,0"
    # el formato r,g,b de KDE no lleva alfa
    assert Color.parse("#FF800010").kde() == "255,128,0"


# --- build_colors ---------------------------------------------------------------

def parse_scheme(text: str) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(interpolation=None, strict=True)
    cp.optionxform = str  # las claves de KDE distinguen mayúsculas
    cp.read_string(text)
    return cp


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_build_colors_structure(tokens, variant):
    scheme = parse_scheme(build_colors(tokens, variant))
    scheme_id, name = VARIANTS[variant]
    assert scheme["General"]["ColorScheme"] == scheme_id
    assert scheme["General"]["Name"] == name
    for section in ("Colors:Button", "Colors:Complementary", "Colors:Header", "Colors:Header][Inactive",
                    "Colors:Selection", "Colors:Tooltip", "Colors:View", "Colors:Window", "WM"):
        assert section in scheme, section
    # todos los colores son r,g,b de 0 a 255
    for section in scheme.sections():
        if not section.startswith("Colors:") and section != "WM":
            continue
        for key, value in scheme[section].items():
            assert re.fullmatch(r"\d{1,3},\d{1,3},\d{1,3}", value), (section, key, value)
            assert all(0 <= int(v) <= 255 for v in value.split(",")), (section, key, value)


@pytest.mark.parametrize("variant", list(VARIANTS))
def test_build_colors_uses_tokens(tokens, variant):
    p = tokens[variant]
    scheme = parse_scheme(build_colors(tokens, variant))
    assert scheme["Colors:Window"]["BackgroundNormal"] == Color.parse(p["window"]).kde()
    assert scheme["Colors:View"]["BackgroundNormal"] == Color.parse(p["view"]).kde()
    assert scheme["Colors:Selection"]["BackgroundNormal"] == Color.parse(p["accent"]).kde()
    assert scheme["Colors:Selection"]["ForegroundNormal"] == Color.parse(p["accent_fg"]).kde()
    assert scheme["WM"]["activeBackground"] == Color.parse(p["header"]).kde()
    # el texto (con alfa) se aplana sobre su fondo
    window = Color.parse(p["window"])
    assert scheme["Colors:Window"]["ForegroundNormal"] == Color.parse(p["label"]).over(window).kde()


def test_build_colors_follows_token_changes(tokens):
    tokens["light"]["accent"] = "#123456"
    scheme = parse_scheme(build_colors(tokens, "light"))
    assert scheme["Colors:Selection"]["BackgroundNormal"] == "18,52,86"
    assert scheme["Colors:Window"]["DecorationFocus"] == "18,52,86"
