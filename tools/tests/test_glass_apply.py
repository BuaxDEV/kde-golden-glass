# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-glass apply(): glass level × «Reduce transparency».

goldenglassrc lives in memory (kread/kwrite replaced), the theme goes to a
temporary XDG_DATA_HOME and D-Bus is never called: nothing reaches the session.
"""

from __future__ import annotations

import configparser
import json
from pathlib import Path

import glass
import plasma_theme
import pytest

STYLE = [("goldenglassrc", "Style", key) for key in glass.STYLE_KEYS]


class Rc:
    """kreadconfig6/kwriteconfig6 over a dict: (file, group, key) → value."""

    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], str] = {}
        self.dbus: list[tuple[str, ...]] = []

    def kread(self, file: str, group: str, key: str, default: str = "") -> str:
        return self.values.get((file, group, key), default)

    def kwrite(self, file: str, group: str, key: str, value) -> None:
        self.values[(file, group, key)] = str(value)


@pytest.fixture
def rc(monkeypatch, tmp_path: Path) -> Rc:
    store = Rc()
    monkeypatch.setattr(glass, "kread", store.kread)
    monkeypatch.setattr(glass, "kwrite", store.kwrite)
    monkeypatch.setattr(glass, "dbus", lambda *args: store.dbus.append(args))
    monkeypatch.setattr(glass, "set_plasma_theme", lambda name: store.kwrite("plasmarc", "Theme", "name", name))
    monkeypatch.setattr(glass, "BOUNCE_DELAY", 0)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return store


@pytest.fixture
def tuned(monkeypatch) -> list[tuple[float, bool]]:
    calls: list[tuple[float, bool]] = []
    monkeypatch.setattr(glass, "write_tuned_theme",
                        lambda tokens, level, reduce_transparency=False: calls.append((level, reduce_transparency)))
    return calls


def _style(rc: Rc) -> set[str]:
    return {rc.values[key] for key in STYLE}


@pytest.mark.parametrize("reduce_transparency", [False, True])
@pytest.mark.parametrize("at_default", [True, False])
def test_level_and_reduce_transparency_matrix(tokens, rc, tuned, at_default, reduce_transparency) -> None:
    level = tokens["glass"]["default_level"] if at_default else 0.2
    rc.kwrite("plasmarc", "Theme", "name", glass.BASE_ID)
    glass.apply(tokens, level=level, reduce_transparency=reduce_transparency)

    package_theme = at_default and not reduce_transparency
    assert tuned == ([] if package_theme else [(level, reduce_transparency)])
    assert rc.kread("plasmarc", "Theme", "name") == (glass.BASE_ID if package_theme else glass.TUNED_ID)
    opacity = 1.0 if reduce_transparency else plasma_theme.glass_alpha(tokens, level)
    assert _style(rc) == {str(round(opacity * 100))}
    assert rc.kread("goldenglassrc", "Accessibility", "ReduceTransparency") == str(reduce_transparency).lower()


def test_reduce_transparency_keeps_the_level_and_off_brings_it_back(tokens, rc, tuned) -> None:
    glass.apply(tokens, level=0.3)
    tuned.clear()

    glass.apply(tokens, reduce_transparency=True)
    assert rc.kread("goldenglassrc", "Glass", "Level") == "0.300"
    assert _style(rc) == {str(round(tokens["accessibility"]["reduce_transparency_alpha"] * 100))}
    assert tuned == [(0.3, True)]

    glass.apply(tokens, reduce_transparency=False)
    assert rc.kread("goldenglassrc", "Glass", "Level") == "0.300"
    assert _style(rc) == {str(round(plasma_theme.glass_alpha(tokens, 0.3) * 100))}
    assert tuned == [(0.3, True), (0.3, False)]


def test_level_changes_under_reduce_transparency_stay_opaque(tokens, rc, tuned) -> None:
    rc.kwrite("goldenglassrc", "Accessibility", "ReduceTransparency", "true")
    glass.apply(tokens, level=tokens["glass"]["default_level"])
    assert tuned == [(tokens["glass"]["default_level"], True)]
    assert _style(rc) == {"100"}


def test_turning_reduce_transparency_off_at_the_factory_level_goes_back_to_the_package_theme(tokens, rc, tuned) -> None:
    rc.kwrite("plasmarc", "Theme", "name", glass.TUNED_ID)
    rc.kwrite("goldenglassrc", "Glass", "Level", str(tokens["glass"]["default_level"]))
    glass.apply(tokens, reduce_transparency=False)
    assert tuned == []
    assert rc.kread("plasmarc", "Theme", "name") == glass.BASE_ID


def test_show_borders_leaves_the_package_theme(tokens, rc, tuned) -> None:
    rc.kwrite("goldenglassrc", "Accessibility", "ShowBorders", "true")
    glass.apply(tokens, level=tokens["glass"]["default_level"])
    assert tuned == [(tokens["glass"]["default_level"], False)]
    glass.apply(tokens, borders=False)
    assert rc.kread("goldenglassrc", "Accessibility", "ShowBorders") == "false"
    assert len(tuned) == 1


def test_tuned_theme_with_reduce_transparency_is_opaque_and_asks_for_no_blur(rc, tmp_path: Path) -> None:
    tokens = glass.load_tokens()
    glass.write_tuned_theme(tokens, 0.2, reduce_transparency=True)
    theme = tmp_path / "data" / "plasma" / "desktoptheme" / glass.TUNED_ID
    plasmarc = configparser.ConfigParser()
    plasmarc.read_string((theme / "plasmarc").read_text(encoding="utf-8"))
    assert plasmarc["BlurBehindEffect"]["enabled"] == "false"
    assert plasmarc["ContrastEffect"]["enabled"] == "false"
    svg = (theme / "translucent" / "dialogs" / "background.svg").read_text(encoding="utf-8")
    assert 'class="ColorScheme-Background" style="fill:currentColor;fill-opacity:1"' in svg
    description = json.loads((theme / "metadata.json").read_text(encoding="utf-8"))["KPlugin"]["Description"]
    assert "reduced transparency" in description

    glass.write_tuned_theme(tokens, 0.2)
    plasmarc.read_string((theme / "plasmarc").read_text(encoding="utf-8"))
    assert plasmarc["BlurBehindEffect"]["enabled"] == "true"


def test_cli_writes_reduce_transparency_and_reads_it_back(tokens, rc, tuned, capsys) -> None:
    assert glass.main(["--get-reduce-transparency"]) == 0
    assert capsys.readouterr().out.strip() == ("on" if tokens["accessibility"]["reduce_transparency"] else "off")
    assert glass.main(["--reduce-transparency", "on"]) == 0
    assert rc.kread("goldenglassrc", "Accessibility", "ReduceTransparency") == "true"
    assert glass.main(["--get-reduce-transparency"]) == 0
    assert capsys.readouterr().out.strip() == "on"
    assert glass.main(["--reduce-transparency", "off", "--no-plasma-reload"]) == 0
    assert rc.kread("goldenglassrc", "Accessibility", "ReduceTransparency") == "false"


def test_apply_asks_the_kwin_effect_to_reread_goldenglassrc(tokens, rc, tuned) -> None:
    glass.apply(tokens, reduce_transparency=True)
    assert ("--type=method_call", "--dest=org.kde.KWin", "/Effects", "org.kde.kwin.Effects.reconfigureEffect",
            f"string:{glass.EFFECT}") in rc.dbus
