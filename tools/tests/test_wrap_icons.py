# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""wrap_icons.py over a made-up machine: every theme gets its wrapped icons, the
Tinted and Clear ones from icons_glyph; nothing outside tmp_path is written."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import icons
import wrap_icons
from icons_style import ACCENT_CLASS, Style

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">{}</svg>'
TILE_WITH_L = ('<rect x="8" y="8" width="112" height="112" rx="26" fill="#0A84FF"/>'
               '<path d="M40 30 H54 V82 H88 V96 H40 Z" fill="#FFFFFF"/>')
DISC = '<circle cx="64" cy="64" r="56" fill="#FF9500"/>'
# icon name → (Name=, drawing): a glyph, a monogram and an app with no letter to draw (skipped)
APPS = {"acme-tool": ("Acme Tool", TILE_WITH_L), "disc-app": ("Disc", DISC), "nameless": ("★", DISC)}
STYLED = [spec for spec in icons.THEME_SPECS if spec.style is not Style.DEFAULT]
# The «L» of acme-tool fills a 36 unit box: its vertical bar spans x 19–26.5 and y 14–50 of the 64 canvas
L_BAR = (22, 32)


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """Applications and their hicolor icons in a private data dir, the rest of XDG in tmp_path."""
    data = tmp_path / "data"
    for name, (label, drawing) in APPS.items():
        desktop = data / "applications" / f"{name}.desktop"
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(f"[Desktop Entry]\nType=Application\nName={label}\nIcon={name}\nExec=true\n",
                           encoding="utf-8")
        icon = data / "icons" / "hicolor" / "scalable" / "apps" / f"{name}.svg"
        icon.parent.mkdir(parents=True, exist_ok=True)
        icon.write_text(SVG.format(drawing), encoding="utf-8")
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        monkeypatch.setenv(key, str(tmp_path / key.lower()))
    monkeypatch.setenv("XDG_DATA_DIRS", str(data))
    monkeypatch.setattr(wrap_icons, "_data_dirs", lambda: [data])
    monkeypatch.setattr(icons, "ICON_BASES", ())   # no installed themes: no guards to look for
    return tmp_path


def run(monkeypatch, icons_dir: Path, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["goldenglass-wrap-icons", "--icons-dir", str(icons_dir), *args])
    assert wrap_icons.main() == 0


def wrapped(icons_dir: Path, theme: str) -> set[str]:
    return {path.stem for path in (icons_dir / theme / "wrapped").glob("*.svg") if not path.is_symlink()}


def test_every_theme_gets_its_wrapped_icons(machine, monkeypatch):
    icons_dir = machine / "icons"
    run(monkeypatch, icons_dir)
    for theme in ("GoldenGlass", "GoldenGlass-Dark"):
        assert wrapped(icons_dir, theme) == set(APPS)
    for spec in STYLED:
        # the skipped app keeps the parent's wrapped icon
        assert wrapped(icons_dir, spec.id) == {"acme-tool", "disc-app"}, spec.id
        svg = (icons_dir / spec.id / "wrapped" / "acme-tool.svg").read_text(encoding="utf-8")
        assert 'id="current-color-scheme"' in svg and 'xmlns:xlink=' in svg
        assert (f'class="{ACCENT_CLASS}"' in svg) == (spec.style is Style.TINTED)


def test_default_icons_do_not_depend_on_the_styles(machine, monkeypatch, tmp_path):
    """The default themes' output is the plain wrap() of each icon, whatever the style tokens say."""
    icons_dir = machine / "icons"
    run(monkeypatch, icons_dir)
    for name in APPS:
        img = wrap_icons._render(machine / "data" / "icons" / "hicolor" / "scalable" / "apps" / f"{name}.svg")
        for theme, dark in (("GoldenGlass", False), ("GoldenGlass-Dark", True)):
            assert (icons_dir / theme / "wrapped" / f"{name}.svg").read_text(encoding="utf-8") == \
                wrap_icons.wrap(img, dark)


def test_rerun_refreshes_the_style_themes(machine, monkeypatch):
    icons_dir = machine / "icons"
    run(monkeypatch, icons_dir)
    stamp = machine / "xdg_cache_home" / "goldenglass" / "wrap-icons.stamp"
    assert stamp.is_file()
    tinted = icons_dir / "GoldenGlass-Tinted" / "wrapped"
    marker = tinted / "acme-tool.svg"
    marker.write_text("stale", encoding="utf-8")
    run(monkeypatch, icons_dir, "--if-changed")
    assert marker.read_text(encoding="utf-8") == "stale"          # nothing changed: nothing redone
    shutil.rmtree(tinted)
    run(monkeypatch, icons_dir, "--if-changed")                   # a theme without its folder is redone
    assert marker.read_text(encoding="utf-8") != "stale"
    run(monkeypatch, icons_dir, "--clean")
    assert not any((icons_dir / spec.id / "wrapped").exists() for spec in icons.THEME_SPECS)


def test_sheet_writes_no_theme(machine, monkeypatch, capsys):
    from PyQt6.QtGui import QImage

    icons_dir, sheet = machine / "icons", machine / "sheet.png"
    run(monkeypatch, icons_dir, "--sheet", str(sheet))
    assert not QImage(str(sheet)).isNull() and not icons_dir.exists()
    assert "glyph 1, silhouette 0, monogram 1, skip 1" in capsys.readouterr().out


@pytest.mark.parametrize("spec", STYLED, ids=lambda spec: spec.id)
def test_styled_guards_use_the_parent_inheritance(spec):
    assert wrap_icons._guard_inherits(spec) == icons.THEMES[spec.base_theme].inherits


def test_icon_lookup_finds_the_styled_wrapped_icons(machine, monkeypatch, _tokens):
    """Plain Qt lookup over the built themes plus the wrapped folders."""
    import os

    import icons_mime
    from PyQt6.QtGui import QIcon

    if os.environ.get("QT_QPA_PLATFORMTHEME"):
        pytest.skip("a platform theme would replace Qt's own icon lookup")
    icons_dir = machine / "icons"
    monkeypatch.setattr(icons, "_family", lambda tokens: "Inter")
    icons.build(_tokens, machine)
    run(monkeypatch, icons_dir)
    icons_mime._app()
    paths, name = QIcon.themeSearchPaths(), QIcon.themeName()
    QIcon.setThemeSearchPaths([str(icons_dir)])
    try:
        def image(theme: str, icon: str):
            QIcon.setThemeName(theme)
            return QIcon.fromTheme(icon).pixmap(64, 64).toImage()

        glyph = image("GoldenGlass-Tinted-Dark", "acme-tool").pixelColor(*L_BAR).name()
        assert glyph == _tokens["light"]["accent"].lower()       # the <style> fallback of the accent
        assert image("GoldenGlass-Tinted-Dark", "nameless") == image("GoldenGlass-Dark", "nameless")
        assert image("GoldenGlass-Clear", "acme-tool") != image("GoldenGlass", "acme-tool")
    finally:
        QIcon.setThemeSearchPaths(paths)
        QIcon.setThemeName(name)


KDE_PROBE = """
import sys
from PyQt6.QtGui import QGuiApplication, QIcon, QPalette
app = QGuiApplication(sys.argv[:1])
img = QIcon.fromTheme("acme-tool").pixmap(64, 64).toImage()
print(QIcon.themeName(), app.palette().color(QPalette.ColorRole.Accent).name(), img.pixelColor(%d, %d).name())
""" % L_BAR


def test_kde_icon_engine_paints_the_extracted_glyph_in_the_palette_accent(machine, monkeypatch, _tokens):
    """KIconLoader rewrites the colour scheme <style> of the wrapped SVG; the PNG mask survives it."""
    import os
    import subprocess

    if not Path("/usr/lib/qt6/plugins/platformthemes/KDEPlasmaPlatformTheme6.so").exists():
        pytest.skip("no KDE platform theme (plasma-integration)")
    home = machine / "kde"
    icons_dir = home / "data" / "icons"
    monkeypatch.setattr(icons, "_family", lambda tokens: "Inter")
    icons.build(_tokens, home / "data")
    run(monkeypatch, icons_dir)
    (home / "config").mkdir(parents=True)
    (home / "config" / "kdeglobals").write_text("[Icons]\nTheme=GoldenGlass-Tinted-Dark\n", encoding="utf-8")
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
