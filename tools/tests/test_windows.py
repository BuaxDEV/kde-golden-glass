# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-windows: factory values of KWin's window effects and Reduce Motion.

Nothing reaches the session: kread/kwrite/kdelete work on an in-memory
configuration and the D-Bus calls are only recorded. The test against a real
kwinrc uses kreadconfig6/kwriteconfig6 on a temporary XDG_CONFIG_HOME with
D-Bus disabled.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import windows

GOLDENGLASS_THEME = "org.goldenglass.light.desktop"


class Session:
    """In-memory KConfig files and the KWin calls a run made."""

    def __init__(self) -> None:
        self.files: dict[str, dict[str, dict[str, str]]] = {}
        self.calls: list[tuple[str, ...]] = []

    def get(self, file: str, group: str, key: str) -> str | None:
        return self.files.get(file, {}).get(group, {}).get(key)

    def set(self, file: str, group: str, key: str, value: str) -> None:
        self.files.setdefault(file, {}).setdefault(group, {})[key] = value

    def read(self, file: str, group: str, key: str, default: str = "") -> str:
        value = self.get(file, group, key)
        return default if value is None else value

    def delete(self, file: str, group: str, key: str) -> None:
        self.files.get(file, {}).get(group, {}).pop(key, None)

    def effects_call(self, method: str, *args: str) -> str:
        self.calls.append((method, *args))
        return ""

    def snapshot(self) -> dict:
        return json.loads(json.dumps(self.files))


@pytest.fixture
def session(monkeypatch) -> Session:
    s = Session()
    monkeypatch.setattr(windows, "kread", s.read)
    monkeypatch.setattr(windows, "kwrite", s.set)
    monkeypatch.setattr(windows, "kdelete", s.delete)
    monkeypatch.setattr(windows, "effects_call", s.effects_call)
    monkeypatch.setattr(windows, "kwin_reconfigure", lambda: s.calls.append(("reconfigure",)))

    def no_subprocess(*args, **kwargs):
        raise AssertionError(f"unexpected subprocess: {args}")
    monkeypatch.setattr(windows.subprocess, "run", no_subprocess)
    s.set("kdeglobals", "KDE", "LookAndFeelPackage", GOLDENGLASS_THEME)
    return s


def kwinrc(session: Session, group: str) -> dict[str, str]:
    return session.files.get("kwinrc", {}).get(group, {})


def test_clean_install_gets_every_default(session, tokens):
    windows.check(tokens)

    kwin = tokens["kwin"]
    assert kwinrc(session, "Plugins") == {
        "magiclampEnabled": "true", "squashEnabled": "false",
        "scaleEnabled": "true", "fadeEnabled": "false",
        "org.goldenglass.shortcutsEnabled": "true",
    }
    assert kwinrc(session, "Effect-scale") == {
        "InScale": f"{kwin['open_scale']:g}", "OutScale": f"{kwin['close_scale']:g}",
        "Duration": str(kwin["window_anim_ms"]),
    }
    assert kwinrc(session, "Effect-overview") == {"BorderActivate": "9"}
    assert kwinrc(session, "Effect-windowview") == {
        "BorderActivate": "9", "BorderActivateAll": "9", "BorderActivateClass": "9"}
    assert kwinrc(session, "ElectricBorders") == {"TopLeft": "None"}
    assert session.get("goldenglassrc", "Windows", "DefaultsVersion") == str(windows.DEFAULTS_VERSION)

    # live: the disabled effects go first, the script is loaded by reconfigure
    assert session.calls == [
        ("unloadEffect", "fade"), ("unloadEffect", "squash"),
        ("loadEffect", "magiclamp"), ("loadEffect", "scale"),
        ("reconfigureEffect", "overview"), ("reconfigureEffect", "scale"), ("reconfigureEffect", "windowview"),
        ("reconfigure",),
    ]


def test_user_choices_are_kept(session, tokens):
    session.set("kwinrc", "Plugins", "squashEnabled", "true")     # minimize: the user's choice
    session.set("kwinrc", "Plugins", "glideEnabled", "true")
    session.set("kwinrc", "Plugins", "fadeEnabled", "true")       # open/close: one key is enough
    session.set("kwinrc", "Effect-scale", "InScale", "0.7")
    session.set("kwinrc", "Effect-overview", "BorderActivate", "3")
    session.set("kwinrc", "Effect-windowview", "BorderActivateAll", "7,3")
    session.set("kwinrc", "ElectricBorders", "TopLeft", "ShowDesktop")
    session.set("kwinrc", "Plugins", "org.goldenglass.shortcutsEnabled", "false")

    windows.check(tokens)

    plugins = kwinrc(session, "Plugins")
    assert plugins == {"squashEnabled": "true", "glideEnabled": "true", "fadeEnabled": "true",
                       "org.goldenglass.shortcutsEnabled": "false"}
    assert kwinrc(session, "Effect-scale")["InScale"] == "0.7"
    assert set(kwinrc(session, "Effect-scale")) == {"InScale", "OutScale", "Duration"}
    assert kwinrc(session, "Effect-overview") == {"BorderActivate": "3"}
    assert kwinrc(session, "Effect-windowview") == {
        "BorderActivate": "9", "BorderActivateAll": "7,3", "BorderActivateClass": "9"}
    assert kwinrc(session, "ElectricBorders") == {"TopLeft": "ShowDesktop"}
    assert not [c for c in session.calls if c[0] in ("loadEffect", "unloadEffect")]


def test_hot_corner_top_left_becomes_none(session, tokens):
    session.set("kwinrc", "Effect-overview", "BorderActivate", "7")
    session.set("kwinrc", "Effect-windowview", "BorderActivateClass", "7")
    windows.check(tokens)
    assert kwinrc(session, "Effect-overview")["BorderActivate"] == "9"
    assert kwinrc(session, "Effect-windowview")["BorderActivateClass"] == "9"


def test_second_run_does_nothing(session, tokens):
    windows.check(tokens)
    session.calls = []
    # the user changes something afterwards: it stays
    session.set("kwinrc", "Plugins", "magiclampEnabled", "false")
    session.delete("kwinrc", "Effect-scale", "Duration")
    before = session.snapshot()

    assert windows.check(tokens) == []
    assert session.snapshot() == before
    assert session.calls == []


def test_other_global_theme_does_nothing(session, tokens):
    session.set("kdeglobals", "KDE", "LookAndFeelPackage", "org.kde.breeze.desktop")
    before = session.snapshot()
    assert windows.check(tokens) == []
    assert session.snapshot() == before
    assert session.calls == []


def test_unreadable_marker_counts_as_not_run(session, tokens):
    session.set("goldenglassrc", "Windows", "DefaultsVersion", "x")
    assert windows.check(tokens)


# --- Reduce Motion ------------------------------------------------------------------

REDUCED = {
    "scaleEnabled": "false", "fadeEnabled": "true", "slideEnabled": "false", "fadedesktopEnabled": "true",
    "magiclampEnabled": "false", "squashEnabled": "false",
}


def test_reduce_motion_on_swaps_effects_for_fades(session, tokens):
    windows.check(tokens)
    session.calls = []
    assert windows.get_reduce_motion(tokens) is tokens["accessibility"]["reduce_motion"]

    windows.set_reduce_motion(tokens, True)

    assert session.get("goldenglassrc", "Accessibility", "ReduceMotion") == "true"
    assert windows.get_reduce_motion(tokens) is True
    assert {k: v for k, v in kwinrc(session, "Plugins").items() if k in REDUCED} == REDUCED
    assert kwinrc(session, "Plugins")["org.goldenglass.shortcutsEnabled"] == "true"
    unloaded = {c[1] for c in session.calls if c[0] == "unloadEffect"}
    loaded = {c[1] for c in session.calls if c[0] == "loadEffect"}
    assert unloaded == {"scale", "slide", "magiclamp", "squash"}
    assert loaded == {"fade", "fadedesktop"}
    assert session.calls.index(("unloadEffect", "scale")) < session.calls.index(("loadEffect", "fade"))
    assert session.calls[-1] == ("reconfigure",)


def test_reduce_motion_off_restores_the_previous_state(session, tokens):
    windows.check(tokens)
    before = kwinrc(session, "Plugins").copy()   # slide and fadedesktop absent: KWin's defaults

    windows.set_reduce_motion(tokens, True)
    session.calls = []
    windows.set_reduce_motion(tokens, False)

    assert kwinrc(session, "Plugins") == before
    assert session.get("goldenglassrc", "Accessibility", "ReduceMotion") == "false"
    assert session.get("goldenglassrc", "Windows", "ReduceMotionSaved") is None
    loaded = {c[1] for c in session.calls if c[0] == "loadEffect"}
    unloaded = {c[1] for c in session.calls if c[0] == "unloadEffect"}
    # slide is on by default in KWin: deleting slideEnabled loads it again
    assert loaded == {"scale", "slide", "magiclamp"}
    assert unloaded == {"fade", "fadedesktop", "squash"}


def test_reduce_motion_off_keeps_what_the_user_changed_meanwhile(session, tokens):
    windows.check(tokens)
    windows.set_reduce_motion(tokens, True)
    session.set("kwinrc", "Plugins", "glideEnabled", "true")      # open/close: glide instead of fade
    session.set("kwinrc", "Plugins", "fadeEnabled", "false")
    session.set("kwinrc", "Plugins", "squashEnabled", "true")

    windows.set_reduce_motion(tokens, False)

    plugins = kwinrc(session, "Plugins")
    assert plugins["fadeEnabled"] == "false" and plugins["squashEnabled"] == "true"
    assert plugins["glideEnabled"] == "true"
    # untouched ones go back
    assert plugins["scaleEnabled"] == "true" and plugins["magiclampEnabled"] == "true"
    assert "slideEnabled" not in plugins and "fadedesktopEnabled" not in plugins


def test_reduce_motion_twice_keeps_the_first_saved_state(session, tokens):
    windows.check(tokens)
    before = kwinrc(session, "Plugins").copy()
    windows.set_reduce_motion(tokens, True)
    windows.set_reduce_motion(tokens, True)
    windows.set_reduce_motion(tokens, False)
    assert kwinrc(session, "Plugins") == before


def test_reduce_motion_off_without_on_only_writes_the_key(session, tokens):
    before = session.snapshot()
    windows.set_reduce_motion(tokens, False)
    after = session.snapshot()
    assert after.pop("goldenglassrc") == {"Accessibility": {"ReduceMotion": "false"}}
    assert after == before
    assert session.calls == []


def test_reduce_motion_minimize_token(session, tokens):
    tokens["kwin"]["reduce_motion_minimize"] = "squash"
    windows.set_reduce_motion(tokens, True)
    assert kwinrc(session, "Plugins")["squashEnabled"] == "true"
    assert kwinrc(session, "Plugins")["magiclampEnabled"] == "false"


def test_main_get_reduce_motion(session, tokens, capsys, monkeypatch):
    monkeypatch.setattr(windows, "load_tokens", lambda: tokens)
    assert windows.main(["--reduce-motion", "on"]) == 0
    assert windows.main(["--get-reduce-motion"]) == 0
    assert capsys.readouterr().out == "on\n"


def test_kwin_tokens_are_validated(tokens):
    import gen_tokens

    gen_tokens.validate(tokens)
    for key, value in (("open_scale", 0), ("close_scale", 1.2), ("window_anim_ms", 0), ("window_anim_ms", 1.5),
                       ("reduce_motion_minimize", "genie")):
        broken = {**tokens, "kwin": {**tokens["kwin"], key: value}}
        with pytest.raises(SystemExit, match=rf"\[kwin\]\.{key}"):
            gen_tokens.validate(broken)


def test_installed_json_is_used_without_the_repository(tokens, tmp_path, monkeypatch):
    path = windows.write_json(tokens, tmp_path / "goldenglass" / windows.TOKENS_JSON)
    monkeypatch.setattr(windows, "REPO_TOKENS", tmp_path / "missing.toml")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    loaded = windows.load_tokens()
    assert loaded["kwin"] == tokens["kwin"]
    assert loaded["accessibility"]["reduce_motion"] == tokens["accessibility"]["reduce_motion"]
    path.unlink()
    monkeypatch.setenv("XDG_DATA_DIRS", str(tmp_path / "none"))
    with pytest.raises(SystemExit):
        windows.load_tokens()


# --- with the real KConfig tools ------------------------------------------------------

# kwinrc of an existing GoldenGlass install (layout script, glass, user tweaks)
PREVIOUS_KWINRC = """\
[Effect-overview]
BorderActivate=7

[Effect-slidingpopups]
SlideInTime=180
SlideOutTime=150

[Plugins]
blurEnabled=false
goldenglass_glassEnabled=true
org.goldenglass.shortcutsEnabled=true
squashEnabled=false
virtualdesktopsonlyonprimaryEnabled=false

[Windows]
PerOutputVirtualDesktops=true

[org.kde.kdecoration2]
ButtonsOnLeft=XIA
library=org.goldenglass.decoration
"""


@pytest.mark.skipif(not (shutil.which("kreadconfig6") and shutil.which("kwriteconfig6")),
                    reason="without kreadconfig6/kwriteconfig6")
def test_update_with_a_previous_kwinrc(tokens, tmp_path, monkeypatch):
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
    monkeypatch.setenv("XDG_CONFIG_DIRS", str(tmp_path / "none"))
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "disabled:")
    calls = []
    monkeypatch.setattr(windows, "effects_call", lambda *a: calls.append(a) or "")
    monkeypatch.setattr(windows, "kwin_reconfigure", lambda: calls.append(("reconfigure",)))
    (config / "kwinrc").write_text(PREVIOUS_KWINRC, encoding="utf-8")
    subprocess.run(["kwriteconfig6", "--file", "kdeglobals", "--group", "KDE", "--key", "LookAndFeelPackage",
                    GOLDENGLASS_THEME], check=True)

    windows.check(tokens)

    def read(group: str, key: str) -> str | None:
        return windows.read_optional("kwinrc", group, key)

    # squash was the user's choice (or an older layout): the genie is not forced
    assert read("Plugins", "squashEnabled") == "false"
    assert read("Plugins", "magiclampEnabled") is None
    assert read("Plugins", "scaleEnabled") == "true" and read("Plugins", "fadeEnabled") == "false"
    assert read("Effect-overview", "BorderActivate") == "9"
    assert read("Effect-scale", "Duration") == str(tokens["kwin"]["window_anim_ms"])
    # everything else as it was
    for group, key, value in (("Plugins", "blurEnabled", "false"), ("Plugins", "goldenglass_glassEnabled", "true"),
                              ("Effect-slidingpopups", "SlideInTime", "180"),
                              ("Windows", "PerOutputVirtualDesktops", "true"),
                              ("org.kde.kdecoration2", "library", "org.goldenglass.decoration")):
        assert read(group, key) == value, (group, key)
    assert windows.defaults_version() == windows.DEFAULTS_VERSION

    windows.set_reduce_motion(tokens, True)
    assert read("Plugins", "slideEnabled") == "false"
    windows.set_reduce_motion(tokens, False)
    assert read("Plugins", "slideEnabled") is None
    assert read("Plugins", "squashEnabled") == "false"
    assert read("Plugins", "magiclampEnabled") is None
    assert windows.kread("goldenglassrc", "Windows", "ReduceMotionSaved", "") == ""
    assert Path(config / "kwinrc").read_text(encoding="utf-8").count("[Plugins]") == 1
