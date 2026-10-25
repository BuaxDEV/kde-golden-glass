# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Glass surfaces of the Plasma Style (tools/plasma_theme.py): the edge is a
dark outer line and a light inner one with the alphas of [glass.border]."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import plasma_theme
import pytest

SVG = "{http://www.w3.org/2000/svg}"
SURFACES = ("dialogs/background.svg", "widgets/panel-background.svg", "widgets/tooltip.svg",
            "widgets/background.svg")
SIDES = ("top", "bottom", "left", "right")
CORNERS = ("topleft", "topright", "bottomleft", "bottomright")


def _tiles(svg: str) -> dict[str, ET.Element]:
    root = ET.fromstring(svg)
    return {g.get("id"): g for g in root.iter(f"{SVG}g")}


def _paint(element: ET.Element) -> tuple[str, float]:
    style = dict(part.split(":") for part in element.get("style", "").split(";") if part)
    return style["fill"], float(style["fill-opacity"])


def _edges(tile: ET.Element) -> list[ET.Element]:
    return [child for child in tile if child.get("class") is None]


@pytest.fixture
def surface(tokens: dict) -> dict[str, ET.Element]:
    return _tiles(plasma_theme.glass_surface(tokens, radius=14, margin=10, shadow_size=28, shadow_alpha=0.3,
                                             alpha=0.65))


def test_every_edge_tile_has_a_dark_then_a_light_line(tokens: dict, surface) -> None:
    border = tokens["glass"]["border"]
    for name in (*SIDES, *CORNERS):
        edges = _edges(surface[name])
        assert [_paint(e) for e in edges] == [("#000000", border["shade_alpha"]),
                                             ("#FFFFFF", border["highlight_alpha"])], name
    assert _edges(surface["center"]) == []


def test_lines_are_stacked_from_the_outside_in(tokens: dict, surface) -> None:
    width = tokens["glass"]["border"]["width"]
    top_shade, top_light = (float(e.get("y")) for e in _edges(surface["top"]))
    assert top_light - top_shade == pytest.approx(width)
    for line in _edges(surface["top"]):
        assert float(line.get("height")) == pytest.approx(width)
    bottom_shade, bottom_light = _edges(surface["bottom"])
    assert float(bottom_shade.get("y")) - float(bottom_light.get("y")) == pytest.approx(width)
    # corners: rings of radius 14 → 13 (outer line) and 13 → 12 (inner line)
    radii = [re.findall(r"A ([\d.]+),", e.get("d")) for e in _edges(surface["topleft"])]
    assert radii == [["14", "13"], ["13", "12"]]


def test_the_surface_fill_keeps_the_glass_alpha(surface) -> None:
    fill = next(child for child in surface["center"] if child.get("class") == plasma_theme.BG)
    assert _paint(fill) == ("currentColor", 0.65)


def test_built_theme_uses_the_edge_on_every_glass_surface(tokens: dict, tmp_path: Path) -> None:
    plasma_theme.build({**tokens, "meta": {**tokens["meta"], "version": "0"}}, tmp_path)
    root = tmp_path / "plasma" / "desktoptheme" / plasma_theme.THEME_ID
    for prefix in ("", "translucent/", "opaque/", "solid/"):
        for rel in SURFACES:
            tiles = _tiles((root / prefix / rel).read_text(encoding="utf-8"))
            assert len(_edges(tiles["top"])) == 2, prefix + rel
