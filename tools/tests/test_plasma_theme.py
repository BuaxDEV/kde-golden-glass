# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Glass surfaces of the Plasma Style (tools/plasma_theme.py): the edge is a
dark outer line and a light inner one with the alphas of [glass.border]; with
«Show borders» the outer line takes the text colour. The menu bar has its own
panel frame (north-), bound to its own radius instead of the dock's."""

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
TILES = (*CORNERS, *SIDES, "center")
VARIANTS = ("", "translucent/", "opaque/", "solid/")


def _tiles(svg: str) -> dict[str, ET.Element]:
    root = ET.fromstring(svg)
    return {g.get("id"): g for g in root.iter(f"{SVG}g")}


def _paint(element: ET.Element) -> tuple[str, float]:
    style = dict(part.split(":") for part in element.get("style", "").split(";") if part)
    return style["fill"], float(style["fill-opacity"])


def _edges(tile: ET.Element) -> list[ET.Element]:
    return [child for child in tile if child.get("class") != plasma_theme.BG]


def _edge_paint(element: ET.Element) -> tuple[str | None, str, float]:
    return (element.get("class"), *_paint(element))


@pytest.fixture
def surface(tokens: dict) -> dict[str, ET.Element]:
    return _tiles(plasma_theme.glass_surface(tokens, radius=14, margin=10, shadow_size=28, shadow_alpha=0.3,
                                             alpha=0.65))


def test_every_edge_tile_has_a_dark_then_a_light_line(tokens: dict, surface) -> None:
    border = tokens["glass"]["border"]
    for name in (*SIDES, *CORNERS):
        edges = _edges(surface[name])
        assert [_edge_paint(e) for e in edges] == [(None, "#000000", border["shade_alpha"]),
                                                  (None, "#FFFFFF", border["highlight_alpha"])], name
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


def test_show_borders_turns_the_outer_line_into_the_text_colour(tokens: dict) -> None:
    surface = _tiles(plasma_theme.glass_surface(tokens, radius=14, margin=10, shadow_size=28, shadow_alpha=0.3,
                                                alpha=0.65, borders=True))
    outer = (plasma_theme.TEXT, "currentColor", tokens["accessibility"]["borders"]["surface_alpha"])
    inner = (None, "#FFFFFF", tokens["glass"]["border"]["highlight_alpha"])
    for name in (*SIDES, *CORNERS):
        assert [_edge_paint(e) for e in _edges(surface[name])] == [outer, inner], name


def _field_edge(svg: str) -> tuple[str | None, str, float]:
    _fill, edge = _tiles(svg)["base-top"]
    return _edge_paint(edge)


@pytest.mark.parametrize("borders", [False, True])
def test_field_edge_follows_show_borders(tokens: dict, borders: bool) -> None:
    alpha = tokens["accessibility"]["borders"]["field_alpha"] if borders else tokens["plasma"]["field_border_alpha"]
    assert _field_edge(plasma_theme.lineedit_svg(tokens, borders)) == (plasma_theme.TEXT, "currentColor", alpha)


@pytest.mark.parametrize("reduce_transparency", [False, True])
@pytest.mark.parametrize("level", [0.0, 0.5, 1.0])
def test_built_theme_composes_show_borders_with_level_and_reduce_transparency(
        tokens: dict, tmp_path: Path, level: float, reduce_transparency: bool) -> None:
    plasma_theme.build({**tokens, "meta": {**tokens["meta"], "version": "0"}}, tmp_path, level,
                       reduce_transparency=reduce_transparency, borders=True)
    root = tmp_path / "plasma" / "desktoptheme" / plasma_theme.THEME_ID
    alpha = (tokens["accessibility"]["reduce_transparency_alpha"] if reduce_transparency
             else plasma_theme.glass_alpha(tokens, level))
    outer = (plasma_theme.TEXT, "currentColor", tokens["accessibility"]["borders"]["surface_alpha"])
    for rel in SURFACES:
        tiles = _tiles((root / "translucent" / rel).read_text(encoding="utf-8"))
        assert _edge_paint(_edges(tiles["top"])[0]) == outer, rel
        fill = next(child for child in tiles["center"] if child.get("class") == plasma_theme.BG)
        assert _paint(fill) == ("currentColor", pytest.approx(alpha)), rel
    field = _field_edge((root / "widgets" / "lineedit.svg").read_text(encoding="utf-8"))
    assert field == (plasma_theme.TEXT, "currentColor", tokens["accessibility"]["borders"]["field_alpha"])


def _build(tokens: dict, out: Path) -> Path:
    plasma_theme.build({**tokens, "meta": {**tokens["meta"], "version": "0"}}, out)
    return out / "plasma" / "desktoptheme" / plasma_theme.THEME_ID


def _hint_size(svg: str, name: str) -> tuple[float, float]:
    rect = next(r for r in ET.fromstring(svg).iter(f"{SVG}rect") if r.get("id") == name)
    return float(rect.get("width")), float(rect.get("height"))


def _corner_radius(tile: ET.Element) -> float:
    fill = next(child for child in tile if child.get("class") == plasma_theme.BG)
    return float(re.search(r"A ([\d.]+),", fill.get("d")).group(1))


@pytest.mark.parametrize("variant", VARIANTS)
def test_every_panel_variant_has_the_menubar_frame_and_mask(tokens: dict, tmp_path: Path, variant: str) -> None:
    svg = (_build(tokens, tmp_path) / variant / "widgets" / "panel-background.svg").read_text(encoding="utf-8")
    tiles = _tiles(svg)
    for prefix in ("", "mask-", "north-", "mask-north-"):
        assert all(f"{prefix}{name}" in tiles for name in TILES), prefix
    padding = tokens["plasma"]["menubar_padding_v"]
    assert _hint_size(svg, "north-hint-top-margin")[1] == padding
    assert _hint_size(svg, "north-hint-bottom-margin")[1] == padding


def test_the_menubar_and_the_dock_have_their_own_radius(tokens: dict) -> None:
    tokens["radius"].update(menubar=5, dock=20)
    tiles = _tiles(plasma_theme.panel_background(tokens, alpha=0.65))
    assert _corner_radius(tiles["north-topleft"]) == 5
    assert _corner_radius(tiles["topleft"]) == 20


def test_the_menubar_radius_bounds_its_height(tokens: dict, tmp_path: Path) -> None:
    tokens["radius"]["menubar"] = tokens["plasma"]["menubar_height"] / 2 + 1
    with pytest.raises(SystemExit, match="radius.menubar"):
        _build(tokens, tmp_path)


def test_the_dock_radius_no_longer_bounds_the_menubar(tokens: dict, tmp_path: Path) -> None:
    tokens["radius"]["dock"] = tokens["plasma"]["menubar_height"]
    assert (_build(tokens, tmp_path) / "widgets" / "panel-background.svg").is_file()


def test_square_menubar_tiles_hold_both_edge_lines(tokens: dict) -> None:
    tokens["radius"]["menubar"] = 0
    tiles = _tiles(plasma_theme.panel_background(tokens, alpha=0.65))
    for name in ("bottom", "bottomleft"):
        tile = tiles[f"north-{name}"]
        fill = next(child for child in tile if child.get("class") == plasma_theme.BG)
        top, bottom = float(fill.get("y")), float(fill.get("y")) + float(fill.get("height"))
        for line in _edges(tile):
            y = float(line.get("y"))
            assert top <= y and y + float(line.get("height")) <= bottom, name

