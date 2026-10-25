# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""icons.build(): every theme comes from its ThemeSpec, and the default themes keep their layout."""

from __future__ import annotations

import configparser
from pathlib import Path

import pytest

import icons
from icons_style import Style

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
        base = icons.THEMES[spec.base_theme]
        assert base.base is not icons.Base.INHERITED and base.style is Style.DEFAULT
        if spec.base is icons.Base.INHERITED:
            assert base.dark == spec.dark and spec.inherits == (base.id,)


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


# --- the apps-only styled themes ---------------------------------------------------

STYLED = [spec for spec in icons.THEME_SPECS if spec.style is not Style.DEFAULT]


def test_there_is_a_styled_theme_per_style_and_appearance():
    assert {(spec.style, spec.dark) for spec in STYLED} == {
        (style, dark) for style in (Style.CLEAR, Style.TINTED) for dark in (False, True)}
    assert {spec.id for spec in STYLED} == {"GoldenGlass-Clear", "GoldenGlass-Clear-Dark",
                                           "GoldenGlass-Tinted", "GoldenGlass-Tinted-Dark"}


@pytest.mark.parametrize("spec", STYLED, ids=lambda spec: spec.id)
def test_styled_theme_carries_only_apps_and_inherits_its_default(built, spec):
    root = built / spec.id
    assert sorted(p.name for p in root.iterdir()) == ["apps", "index.theme", "inherited"]
    assert (root / "inherited").is_symlink() and str((root / "inherited").readlink()) == f"../{spec.base_theme}/inherited"
    entry = index(built, spec.id)
    assert entry["Inherits"] == ("GoldenGlass-Dark" if spec.dark else "GoldenGlass")
    assert entry["Hidden"] == "true"
    assert entry["Directories"] == "apps/scalable,inherited,wrapped"
    own = {p.name for p in (root / "apps/scalable").iterdir()}
    assert own == {p.name for p in (built / spec.base_theme / "apps/scalable").iterdir()}


def test_adding_the_styled_themes_leaves_the_default_ones_byte_identical(built, tmp_path, _tokens, monkeypatch):
    defaults = tuple(spec for spec in icons.THEME_SPECS if spec.style is Style.DEFAULT)
    monkeypatch.setattr(icons, "THEME_SPECS", defaults)
    monkeypatch.setattr(icons, "ICON_BASES", ())
    monkeypatch.setattr(icons, "_family", lambda tokens: "Inter")
    icons.build(_tokens, tmp_path)
    for spec in defaults:
        assert tree(tmp_path / "icons" / spec.id) == tree(built / spec.id), spec.id


def tree(root: Path) -> dict[str, bytes]:
    """Relative path → file content, or the target of a symbolic link."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if path.is_symlink():
            out[rel] = b"-> " + str(path.readlink()).encode()
        elif path.is_file():
            out[rel] = path.read_bytes()
    return out


def test_build_writes_the_style_json(built, _tokens):
    import json

    path = built / "icon-style.json"
    light = {key: _tokens["light"][key] for key in ("accent", "label")}
    assert json.loads(path.read_text(encoding="utf-8")) == {"icon_style": _tokens["icon_style"], "light": light}


# --- resolution with QIcon.fromTheme ----------------------------------------------

def _glyph_and_tile(icon) -> tuple[str, str]:
    """Colours at the middle of the Dolphin glyph and at the top of its tile, at 64 px."""
    img = icon.pixmap(64, 64).toImage()
    return img.pixelColor(32, 32).name(), img.pixelColor(32, 12).name()


@pytest.fixture
def theme_search(built):
    """Plain Qt icon lookup (no KDE engine) over the built themes only."""
    import os

    import icons_mime
    from PyQt6.QtGui import QIcon

    if os.environ.get("QT_QPA_PLATFORMTHEME"):
        pytest.skip("a platform theme would replace Qt's own icon lookup")
    icons_mime._app()
    paths, name = QIcon.themeSearchPaths(), QIcon.themeName()
    QIcon.setThemeSearchPaths([str(built)])
    yield QIcon
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(name)


@pytest.mark.parametrize("spec", STYLED, ids=lambda spec: spec.id)
def test_styled_theme_resolves_its_apps_and_inherits_the_rest(theme_search, spec):
    QIcon = theme_search
    QIcon.setThemeName(spec.base_theme)
    default_app = _glyph_and_tile(QIcon.fromTheme("org.kde.dolphin"))
    default_folder = QIcon.fromTheme("folder").pixmap(64, 64).toImage()
    QIcon.setThemeName(spec.id)
    assert _glyph_and_tile(QIcon.fromTheme("org.kde.dolphin")) != default_app
    assert _glyph_and_tile(QIcon.fromTheme("system-file-manager")) == _glyph_and_tile(QIcon.fromTheme("org.kde.dolphin"))
    for inherited in ("folder", "user-trash", "drive-harddisk", "text-plain"):
        assert not QIcon.fromTheme(inherited).isNull(), inherited
    assert QIcon.fromTheme("folder").pixmap(64, 64).toImage() == default_folder


def test_tinted_theme_paints_the_glyph_with_the_fallback_accent(theme_search, _tokens):
    QIcon = theme_search
    QIcon.setThemeName("GoldenGlass-Tinted-Dark")
    glyph, _ = _glyph_and_tile(QIcon.fromTheme("org.kde.dolphin"))
    assert glyph == _tokens["light"]["accent"].lower()   # the <style> fallback of every theme


KDE_PROBE = """
import sys
from PyQt6.QtGui import QGuiApplication, QIcon, QPalette
app = QGuiApplication(sys.argv[:1])
img = QIcon.fromTheme("org.kde.dolphin").pixmap(64, 64).toImage()
print(QIcon.themeName(), app.palette().color(QPalette.ColorRole.Accent).name(), img.pixelColor(32, 32).name())
"""


def test_kde_icon_engine_paints_tinted_glyphs_in_the_palette_accent(built, tmp_path, _tokens):
    """With the KDE platform theme, KIconLoader replaces ColorScheme-Accent with the current accent."""
    import os
    import subprocess
    import sys

    plugin = Path("/usr/lib/qt6/plugins/platformthemes/KDEPlasmaPlatformTheme6.so")
    if not plugin.exists():
        pytest.skip("no KDE platform theme (plasma-integration)")
    home = tmp_path / "home"
    (home / "config").mkdir(parents=True)
    (home / "config" / "kdeglobals").write_text("[Icons]\nTheme=GoldenGlass-Tinted-Dark\n", encoding="utf-8")
    (home / "data").mkdir()
    (home / "data" / "icons").symlink_to(built)
    env = {key: value for key, value in os.environ.items()
           if key not in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS")}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), XDG_DATA_HOME=str(home / "data"),
               XDG_CACHE_HOME=str(home / "cache"), XDG_STATE_HOME=str(home / "state"),
               XDG_CONFIG_DIRS=str(home / "no-config-dirs"), XDG_DATA_DIRS="/usr/share",
               DBUS_SESSION_BUS_ADDRESS=f"unix:path={home / 'no-bus'}",
               QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="kde")
    out = subprocess.run([sys.executable, "-c", KDE_PROBE], env=env, capture_output=True, text=True,
                         timeout=60, check=True).stdout.split()
    theme, accent, glyph = out[-3:]
    assert theme == "GoldenGlass-Tinted-Dark"
    assert accent != _tokens["light"]["accent"].lower()
    assert glyph == accent
