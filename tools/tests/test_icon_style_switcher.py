# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-icon-style: the stored choice, --apply, --get and the --watch corrections.

Nothing reaches the session: kreadconfig6, kwriteconfig6, plasma-changeicons and
goldenglass-wrap-icons are stand-ins in tmp_path that work on a JSON store and
log each call; HOME, the XDG directories and the runtime directory are
temporary and the session bus address leads nowhere.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import icon_style_switcher as switcher
from icons_style import Appearance, Style, family

LIGHT_WINDOW = "239,240,241"
DARK_WINDOW = "30,30,32"

STUB_COMMON = r'''
import json, os, sys
store_path = os.environ["GG_ICON_TEST_STORE"]
def load():
    try:
        with open(store_path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
def save(store):
    with open(store_path, "w") as f:
        json.dump(store, f)
def log(*call):
    with open(os.environ["GG_ICON_TEST_LOG"], "a") as f:
        f.write(json.dumps(list(call)) + "\n")
def option(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default
'''

STUBS = {
    "kreadconfig6": STUB_COMMON + r'''
args = sys.argv[1:]
value = load().get(option(args, "--file"), {}).get(option(args, "--group"), {}).get(option(args, "--key"))
print(option(args, "--default", "") if value is None else value)
''',
    "kwriteconfig6": STUB_COMMON + r'''
args = sys.argv[1:]
store = load()
store.setdefault(option(args, "--file"), {}).setdefault(option(args, "--group"), {})[option(args, "--key")] = args[-1]
save(store)
log("kwriteconfig6", option(args, "--file"), option(args, "--group"), option(args, "--key"), args[-1])
''',
    "plasma-changeicons": STUB_COMMON + r'''
store = load()
store.setdefault("kdeglobals", {}).setdefault("Icons", {})["Theme"] = sys.argv[1]
save(store)
log("plasma-changeicons", sys.argv[1])
''',
    "wrap_icons.py": STUB_COMMON + r'''
icons = os.path.join(os.environ["XDG_DATA_HOME"], "icons")
for theme in os.environ["GG_ICON_TEST_FAMILY"].split():
    os.makedirs(os.path.join(icons, theme, "wrapped"), exist_ok=True)
log("wrap-icons", *sys.argv[1:])
''',
}


class Session:
    def __init__(self, root: Path) -> None:
        self.store = root / "store.json"
        self.log = root / "calls.log"

    def files(self) -> dict:
        return json.loads(self.store.read_text()) if self.store.exists() else {}

    def get(self, file: str, group: str, key: str) -> str | None:
        return self.files().get(file, {}).get(group, {}).get(key)

    def set(self, file: str, group: str, key: str, value: str) -> None:
        files = self.files()
        files.setdefault(file, {}).setdefault(group, {})[key] = value
        self.store.write_text(json.dumps(files))

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def changes(self) -> list[str]:
        return [call[1] for call in self.calls() if call[0] == "plasma-changeicons"]

    def forget_calls(self) -> None:
        self.log.unlink(missing_ok=True)

    def scheme(self, dark: bool) -> None:
        self.set("kdeglobals", "Colors:Window", "BackgroundNormal", DARK_WINDOW if dark else LIGHT_WINDOW)

    def theme(self) -> str | None:
        return self.get("kdeglobals", "Icons", "Theme")


@pytest.fixture
def session(tmp_path, monkeypatch) -> Session:
    home = tmp_path / "home"
    dirs = {name: home / name for name in ("config", "data", "cache", "runtime", "bin", "system")}
    for path in dirs.values():
        path.mkdir(parents=True)
    dirs["runtime"].chmod(0o700)
    for name, body in STUBS.items():
        stub = dirs["bin"] / name
        stub.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        stub.chmod(0o755)
    s = Session(tmp_path)
    for key, value in {
        "HOME": home, "XDG_CONFIG_HOME": dirs["config"], "XDG_DATA_HOME": dirs["data"],
        "XDG_CACHE_HOME": dirs["cache"], "XDG_RUNTIME_DIR": dirs["runtime"], "XDG_DATA_DIRS": dirs["system"],
        "XDG_CONFIG_DIRS": home / "no-config-dirs", "DBUS_SESSION_BUS_ADDRESS": f"unix:path={home / 'no-bus'}",
        "PATH": f"{dirs['bin']}{os.pathsep}{os.environ['PATH']}",
        "GG_ICON_TEST_STORE": s.store, "GG_ICON_TEST_LOG": s.log, "GG_ICON_TEST_FAMILY": " ".join(family()),
    }.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setattr(switcher, "CHANGEICONS_LIBEXEC", ())
    monkeypatch.setattr(switcher, "WRAP_ICONS", dirs["bin"] / "wrap_icons.py")
    for theme in (*family(), "breeze"):
        folder = dirs["data"] / "icons" / theme
        (folder / "apps" / "scalable").mkdir(parents=True)
        (folder / "index.theme").write_text(f"[Icon Theme]\nName={theme}\n", encoding="utf-8")
        for name in switcher.PREVIEW_APPS:
            (folder / "apps" / "scalable" / f"{name}.svg").write_text("<svg/>", encoding="utf-8")
    s.scheme(dark=False)
    s.set("kdeglobals", "Icons", "Theme", "GoldenGlass")
    return s


def wrap(session: Session) -> None:
    for theme in family():
        (Path(os.environ["XDG_DATA_HOME"]) / "icons" / theme / "wrapped").mkdir(parents=True, exist_ok=True)


# --- choice and --get -------------------------------------------------------------

def test_factory_choice_is_default_and_auto(session):
    state = switcher.state()
    assert (state["style"], state["appearance"], state["explicit"]) == ("default", "auto", False)
    assert (state["defaultStyle"], state["defaultAppearance"]) == ("default", "auto")
    assert (state["theme"], state["resolved"], state["darkScheme"]) == ("GoldenGlass", "GoldenGlass", False)


def test_get_previews_each_style_in_the_effective_appearance(session):
    session.set("goldenglassrc", "Icons", "Appearance", "dark")
    previews = switcher.state()["previews"]
    data = Path(os.environ["XDG_DATA_HOME"])
    assert set(previews) == {"default", "clear", "tinted"}
    assert previews["tinted"] == [str(data / "icons" / "GoldenGlass-Tinted-Dark" / "apps" / "scalable" / f"{name}.svg")
                                  for name in switcher.PREVIEW_APPS]
    assert previews["default"][0].endswith("/GoldenGlass-Dark/apps/scalable/dolphin.svg")


def test_get_prints_json(session, capsys):
    assert switcher.main(["--get"]) == 0
    assert json.loads(capsys.readouterr().out)["resolved"] == "GoldenGlass"
    assert session.calls() == []


@pytest.mark.parametrize("stored, expected", [
    ({"Style": "Tinted", "Appearance": "DARK"}, (Style.TINTED, Appearance.DARK)),
    ({"Style": "glass", "Appearance": ""}, (Style.DEFAULT, Appearance.AUTO)),
])
def test_stored_values_are_read_leniently(session, stored, expected):
    for key, value in stored.items():
        session.set("goldenglassrc", "Icons", key, value)
    choice = switcher.read_choice()
    assert (choice.style, choice.appearance, choice.explicit) == (*expected, True)


# --- setters and --apply ----------------------------------------------------------

def test_style_generates_the_wrapped_icons_first(session):
    assert switcher.main(["--style", "tinted"]) == 0
    assert session.get("goldenglassrc", "Icons", "Style") == "tinted"
    assert [call[0] for call in session.calls()] == ["kwriteconfig6", "wrap-icons", "plasma-changeicons"]
    assert session.calls()[1] == ["wrap-icons", "--if-changed"]
    assert session.theme() == "GoldenGlass-Tinted"


def test_wrapped_icons_already_there(session):
    wrap(session)
    switcher.main(["--style", "clear", "--appearance", "dark"])
    assert [call[0] for call in session.calls()] == ["kwriteconfig6", "kwriteconfig6", "plasma-changeicons"]
    assert session.theme() == "GoldenGlass-Clear-Dark"


def test_default_style_needs_no_wrapped_icons(session):
    switcher.main(["--appearance", "dark"])
    assert session.changes() == ["GoldenGlass-Dark"]
    assert "wrap-icons" not in [call[0] for call in session.calls()]


@pytest.mark.parametrize("dark, expected", [(False, "GoldenGlass-Tinted"), (True, "GoldenGlass-Tinted-Dark")])
def test_auto_follows_the_colour_scheme(session, dark, expected):
    wrap(session)
    session.scheme(dark)
    switcher.main(["--style", "tinted", "--appearance", "auto"])
    assert session.theme() == expected


def test_apply_does_nothing_when_the_theme_is_in_use(session):
    session.set("goldenglassrc", "Icons", "Style", "default")
    assert switcher.apply() is None
    assert session.changes() == []


def test_apply_leaves_another_family(session):
    """An explicit request switches even from another theme (the user asked for it)."""
    wrap(session)
    session.set("kdeglobals", "Icons", "Theme", "breeze")
    session.set("goldenglassrc", "Icons", "Style", "tinted")
    switcher.main(["--apply"])
    assert session.changes() == ["GoldenGlass-Tinted"]


def test_missing_theme_fails_before_switching(session):
    import shutil
    shutil.rmtree(Path(os.environ["XDG_DATA_HOME"]) / "icons" / "GoldenGlass-Clear")
    with pytest.raises(SystemExit, match="GoldenGlass-Clear is not installed"):
        switcher.main(["--style", "clear"])
    assert session.changes() == []


def test_missing_plasma_changeicons(session, monkeypatch):
    monkeypatch.setattr(switcher.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="plasma-changeicons was not found"):
        switcher.main(["--appearance", "dark"])


@pytest.mark.parametrize("argv", [["--style", "tinted", "--get"], ["--appearance", "dark", "--watch"], [],
                                  ["--style", "glass"], ["--get", "--apply"]])
def test_bad_command_lines(session, argv):
    with pytest.raises(SystemExit) as exc:
        switcher.main(argv)
    assert exc.value.code == 2
    assert session.calls() == []


def test_writes_take_the_lock(session):
    switcher.main(["--appearance", "dark"])
    assert switcher.lock_path() == Path(os.environ["XDG_RUNTIME_DIR"]) / "goldenglass-icon-style.lock"
    assert switcher.lock_path().exists()


def test_launcher_runs_the_tool(session):
    """The installed command line, as the module runs it."""
    wrap(session)
    tool = Path(switcher.__file__)
    subprocess.run([sys.executable, str(tool), "--style", "tinted"], check=True, timeout=60)
    out = subprocess.run([sys.executable, str(tool), "--get"], check=True, timeout=60, capture_output=True, text=True)
    assert json.loads(out.stdout)["theme"] == "GoldenGlass-Tinted"


# --- --watch ------------------------------------------------------------------------

class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_watch_waits_for_a_choice(session):
    session.scheme(dark=True)
    assert switcher.Corrector().reconcile() is None
    assert session.changes() == []


def test_watch_keeps_the_style_over_a_global_theme(session):
    wrap(session)
    switcher.main(["--style", "tinted"])
    session.forget_calls()
    # what applying the GoldenGlass dark global theme writes
    session.set("kdeglobals", "Icons", "Theme", "GoldenGlass-Dark")
    session.scheme(dark=True)
    assert switcher.Corrector().reconcile() == "GoldenGlass-Tinted-Dark"
    assert session.changes() == ["GoldenGlass-Tinted-Dark"]


def test_watch_follows_auto_appearance(session):
    wrap(session)
    switcher.main(["--style", "clear"])
    corrector = switcher.Corrector()
    session.scheme(dark=True)
    assert corrector.reconcile() == "GoldenGlass-Clear-Dark"
    session.scheme(dark=False)
    assert corrector.reconcile() == "GoldenGlass-Clear"
    assert corrector.reconcile() is None


def test_watch_respects_another_theme(session):
    session.set("goldenglassrc", "Icons", "Style", "tinted")
    session.set("kdeglobals", "Icons", "Theme", "breeze")
    assert switcher.Corrector().reconcile() is None
    assert session.changes() == []


def test_watch_gives_up_on_a_theme_that_keeps_coming_back(session, capsys):
    wrap(session)
    session.set("goldenglassrc", "Icons", "Style", "tinted")
    clock = Clock()
    corrector = switcher.Corrector(clock)
    for _ in range(switcher.MAX_CORRECTIONS + 3):
        session.set("kdeglobals", "Icons", "Theme", "GoldenGlass")
        corrector.reconcile()
        clock.now += 1
    assert len(session.changes()) == switcher.MAX_CORRECTIONS
    assert "keeps changing" in capsys.readouterr().err
    clock.now += switcher.CORRECTION_WINDOW_S
    assert corrector.reconcile() == "GoldenGlass-Tinted"


def test_watch_does_not_loop_on_its_own_change(session):
    """SP-10e at the logic level: every write notifies the daemon, as kdeglobals does."""
    wrap(session)
    session.set("goldenglassrc", "Icons", "Style", "tinted")
    corrector = switcher.Corrector()
    # applying the dark global theme: icon theme, colour scheme, then more keys
    for key, value in (("Icons/Theme", "GoldenGlass-Dark"), ("Colors:Window/BackgroundNormal", DARK_WINDOW),
                       ("KDE/LookAndFeelPackage", "org.goldenglass.dark.desktop")):
        group, name = key.split("/")
        session.set("kdeglobals", group, name, value)
    pending = 1
    rounds = 0
    while pending and rounds < 10:
        rounds += 1
        before = len(session.calls())
        corrector.reconcile()
        pending = len(session.calls()) - before    # each write notifies once more
    assert rounds == 2
    assert session.changes() == ["GoldenGlass-Tinted-Dark"]
    assert session.theme() == "GoldenGlass-Tinted-Dark"
