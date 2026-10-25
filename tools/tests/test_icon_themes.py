# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""icons.build(): every theme comes from its ThemeSpec, and the default themes keep their layout."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

import icons

DEFAULT_DIRECTORIES = (
    "apps/scalable,devices/16,devices/22,devices/24,devices/scalable,devices/symbolic,mimetypes/16,"
    "mimetypes/22,mimetypes/24,mimetypes/scalable,places/16,places/22,places/24,places/scalable,"
    "places/symbolic,inherited,wrapped")


@pytest.fixture(scope="module")
def built(tmp_path_factory, _tokens) -> Path:
    """The icon themes, built without the machine's installed themes or fonts."""
    out = tmp_path_factory.mktemp("out")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(icons, "ICON_BASES", ())
        mp.setattr(icons, "_family", lambda tokens: "Inter")
        icons.build(_tokens, out)
    return out / "icons"


def index(built: Path, theme: str) -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(built / theme / "index.theme", encoding="utf-8")
    return parser["Icon Theme"]


def test_theme_ids_are_unique():
    assert len(icons.THEMES) == len(icons.THEME_SPECS)


@pytest.mark.parametrize("spec", icons.THEME_SPECS, ids=lambda spec: spec.id)
def test_linked_and_inherited_themes_name_an_existing_base(spec):
    if spec.base is icons.Base.DRAWN:
        assert spec.base_theme is None
    else:
        assert icons.THEMES[spec.base_theme].base is icons.Base.DRAWN


@pytest.mark.parametrize("theme, name, inherits", [
    ("GoldenGlass", "GoldenGlass", "WhiteSur,breeze,hicolor"),
    ("GoldenGlass-Dark", "GoldenGlass Dark", "WhiteSur-dark,breeze-dark,breeze,hicolor"),
])
def test_default_themes_keep_their_index(built, theme, name, inherits):
    entry = index(built, theme)
    assert entry["Name"] == name
    assert entry["Inherits"] == inherits
    assert entry["FollowsColorScheme"] == "true"
    assert entry["Directories"] == DEFAULT_DIRECTORIES
    assert "Hidden" not in entry


def test_dark_theme_links_the_light_icons_and_draws_its_apps(built):
    dark = built / "GoldenGlass-Dark"
    for ctx in ("places", "devices", "mimetypes"):
        assert (dark / ctx).is_symlink() and str((dark / ctx).readlink()) == f"../GoldenGlass/{ctx}"
    assert not (dark / "apps").is_symlink()
    light_app = (built / "GoldenGlass/apps/scalable/org.kde.dolphin.svg").read_text(encoding="utf-8")
    assert (dark / "apps/scalable/org.kde.dolphin.svg").read_text(encoding="utf-8") != light_app
