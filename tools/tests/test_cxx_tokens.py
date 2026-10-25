# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""cxx_tokens: cabecera C++ con los valores por defecto de los .kcfg."""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

import cxx_tokens


def constant(header: str, name: str) -> str:
    m = re.search(rf"^inline constexpr [a-z ]+ {name}(?:\[\])? = (.+?); //", header, re.M)
    assert m, f"{name} no está en la cabecera"
    return m.group(1)


def test_header_shape(tokens):
    header = cxx_tokens.header(tokens)
    assert header.startswith("// Generado por tools/gen_tokens.py")
    assert "#pragma once" in header
    assert "namespace GoldenGlass::Tokens" in header
    assert constant(header, "WindowRadius") == str(tokens["radius"]["window"])
    assert constant(header, "GlassTitleBar") == str(bool(tokens["decoration"]["glass_titlebar"])).lower()
    assert constant(header, "IntegratedTitleBarApps") == '"' + ",".join(tokens["finder"]["apps"]) + '"'


@pytest.mark.parametrize(("px", "index"), [
    (0, 0), (-5, 0),          # ShadowNone
    (1, 1), (24, 1),          # ShadowSmall
    (25, 2), (40, 2),         # ShadowMedium
    (41, 3), (56, 3),         # ShadowLarge
    (57, 4), (500, 4),        # ShadowVeryLarge
])
def test_shadow_size(tokens, px, index):
    tokens["shadow"]["active"]["size"] = px
    assert constant(cxx_tokens.header(tokens), "ShadowSize") == str(index)


@pytest.mark.parametrize(("alpha", "strength"), [(0.0, 25), (0.5, 128), (1.0, 255), (3.0, 255)])
def test_shadow_strength(tokens, alpha, strength):
    tokens["shadow"]["active"]["strength"] = alpha
    assert constant(cxx_tokens.header(tokens), "ShadowStrength") == str(strength)


def test_shadow_size_table(tokens):
    # una entrada por opción de ShadowSize (salvo ShadowNone), con sus seis valores
    header = cxx_tokens.header(tokens)
    for option, key in (("Small", "small"), ("Medium", "medium"), ("Large", "large"), ("VeryLarge", "very_large")):
        s = tokens["shadow"]["sizes"][key]
        assert constant(header, f"Shadow{option}Offset") == str(s["offset"])
        assert constant(header, f"Shadow{option}Radius") == str(s["radius"])
        assert float(constant(header, f"Shadow{option}Alpha")) == s["alpha"]
        assert constant(header, f"Shadow{option}AmbientOffset") == str(s["ambient_offset"])
        assert constant(header, f"Shadow{option}AmbientRadius") == str(s["ambient_radius"])
        assert float(constant(header, f"Shadow{option}AmbientAlpha")) == s["ambient_alpha"]


def test_colors_are_argb(tokens):
    tokens["traffic_lights"]["close"] = "#FF5F57"
    tokens["traffic_lights"]["zoom"] = "#11223344"
    header = cxx_tokens.header(tokens)
    assert constant(header, "TrafficLightClose") == "0xFFFF5F57u"
    assert constant(header, "TrafficLightZoom") == "0x44112233u"


def test_title_alignment(tokens):
    tokens["decoration"]["title_alignment"] = "AlignRight"
    assert constant(cxx_tokens.header(tokens), "TitleAlignment") == "3"
    tokens["decoration"]["title_alignment"] = "Middle"
    with pytest.raises(SystemExit):
        cxx_tokens.header(tokens)


@pytest.mark.skipif(not shutil.which("c++"), reason="sin compilador de C++")
def test_header_compiles(tokens, tmp_path):
    (tmp_path / "goldenglass_tokens.h").write_text(cxx_tokens.header(tokens))
    src = tmp_path / "main.cpp"
    src.write_text('#include "goldenglass_tokens.h"\nint main() { return GoldenGlass::Tokens::WindowRadius > 0 ? 0 : 1; }\n')
    subprocess.run(["c++", "-std=c++20", "-fsyntax-only", "-Wall", "-Werror", str(src)], check=True)
