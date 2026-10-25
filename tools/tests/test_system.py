# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""system (goldenglass-system): activar y desactivar partes, y restaurar lo
que había antes.

En producción corre como root para Plymouth y el inicio de sesión: aquí todo
pasa en directorios temporales. kreadconfig6, kwriteconfig6 y
plymouth-set-default-theme son sustitutos que guardan su estado en un JSON, y
el PATH solo los contiene a ellos: nada llega a ~/.config, /etc ni /var.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import system

TOOLS = Path(__file__).resolve().parent.parent

# Sustitutos de las herramientas del sistema. Comparten un JSON (FAKE_STORE):
# "config" → {"archivo|grupo/…|clave": valor}, "plymouth" → tema actual,
# "calls" → órdenes recibidas.
FAKE_COMMON = """\
import json, os, sys
STORE = os.environ["FAKE_STORE"]
def load():
    try:
        with open(STORE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"config": {}, "plymouth": "bgrt", "calls": []}
def save(data):
    with open(STORE, "w") as f:
        json.dump(data, f)
def entry(args):
    file, groups, key = None, [], None
    rest = []
    it = iter(args)
    for a in it:
        if a == "--file": file = next(it)
        elif a == "--group": groups.append(next(it))
        elif a == "--key": key = next(it)
        else: rest.append(a)
    return f"{file}|{'/'.join(groups)}|{key}", rest
data = load()
data["calls"].append([os.path.basename(sys.argv[0]), *sys.argv[1:]])
"""

FAKES = {
    "kreadconfig6": """\
key, rest = entry(sys.argv[1:])
default = rest[rest.index("--default") + 1] if "--default" in rest else ""
save(data)
print(data["config"].get(key, default))
""",
    "kwriteconfig6": """\
key, rest = entry(a for a in sys.argv[1:] if a != "--notify")
if rest == ["--delete"]:
    data["config"].pop(key, None)
else:
    (value,) = rest
    data["config"][key] = value
save(data)
""",
    "plymouth-set-default-theme": """\
args = [a for a in sys.argv[1:] if a != "--rebuild-initrd"]
if "--rebuild-initrd" in sys.argv and os.environ.get("FAKE_REBUILD_FAILS"):
    save(data)
    sys.exit(1)
if not args:
    print(data["plymouth"])
elif args == ["--reset"]:
    data["plymouth"] = "bgrt"
else:
    data["plymouth"] = args[0]
save(data)
""",
}


class Fakes:
    def __init__(self, store: Path):
        self.store = store

    @property
    def data(self) -> dict:
        try:
            return json.loads(self.store.read_text())
        except FileNotFoundError:
            return {"config": {}, "plymouth": "bgrt", "calls": []}

    @property
    def config(self) -> dict:
        return self.data["config"]

    def set(self, key: str, value: str) -> None:
        data = self.data
        data["config"][key] = value
        self.store.write_text(json.dumps(data))

    def set_plymouth(self, theme: str) -> None:
        data = self.data
        data["plymouth"] = theme
        self.store.write_text(json.dumps(data))


@pytest.fixture
def fakes(tmp_path, monkeypatch) -> Fakes:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in FAKES.items():
        script = bin_dir / name
        script.write_text(f"#!{sys.executable}\n{FAKE_COMMON}{textwrap.dedent(body)}")
        script.chmod(0o755)
    store = tmp_path / "store.json"
    monkeypatch.setenv("FAKE_STORE", str(store))
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "home" / ".local" / "state"))
    monkeypatch.delenv("FAKE_REBUILD_FAILS", raising=False)
    # rutas del sistema → temporales
    monkeypatch.setattr(system, "STATE", tmp_path / "home" / ".local" / "state" / "goldenglass" / "system.json")
    monkeypatch.setattr(system, "ROOT_STATE", tmp_path / "var" / "system.json")
    monkeypatch.setattr(system, "PLYMOUTH_DIR", tmp_path / "plymouth" / "themes")
    monkeypatch.setattr(system, "HELPER", tmp_path / "no-helper")
    for name in ("SDDM_CONF", "SDDM_THEME", "PLM_CONF", "WALLPAPER", "CURSORS"):
        monkeypatch.setattr(system, name, tmp_path / "etc" / name.lower())
    return Fakes(store)


def key(entry: system.Entry) -> str:
    return f"{entry.file}|{entry.group}|{entry.key}"


# --- partes del usuario (kdeglobals, notifyrc) ------------------------------------

def test_enable_disable_unset_keys(fakes):
    state: dict = {}
    system.enable("sounds", state)
    for e in system.PARTS["sounds"]:
        assert fakes.config[key(e)] == e.value
    assert system.is_enabled("sounds")
    # no existían: se guardan como ausentes y disable las borra
    assert all(v is None for v in state["sounds"].values())

    system.disable("sounds", state)
    assert fakes.config == {}
    assert "sounds" not in state
    assert not system.is_enabled("sounds")


def test_disable_restores_previous_values(fakes):
    theme = system.PARTS["sounds"][0]
    fakes.set(key(theme), "ocean")
    state: dict = {}
    system.enable("sounds", state)
    assert fakes.config[key(theme)] == "GoldenGlass"
    system.disable("sounds", state)
    assert fakes.config == {key(theme): "ocean"}


def test_second_enable_keeps_first_saved_value(fakes):
    theme = system.PARTS["sounds"][0]
    fakes.set(key(theme), "ocean")
    state: dict = {}
    system.enable("sounds", state)
    system.enable("sounds", state)
    system.disable("sounds", state)
    assert fakes.config[key(theme)] == "ocean"


def test_disable_respects_later_user_changes(fakes):
    theme, *rest = system.PARTS["sounds"]
    state: dict = {}
    system.enable("sounds", state)
    fakes.set(key(theme), "freedesktop")  # el usuario lo cambió después
    system.disable("sounds", state)
    assert fakes.config == {key(theme): "freedesktop"}


def test_cli_enable_status_disable(fakes, tmp_path):
    """La orden completa, en otro proceso con HOME y XDG_STATE_HOME temporales."""
    if os.geteuid() == 0:
        pytest.skip("las partes del usuario no se activan como root")
    env = dict(os.environ)

    def run(*args: str) -> str:
        return subprocess.run([sys.executable, str(TOOLS / "system.py"), *args], env=env,
                              check=True, capture_output=True, text=True).stdout

    run("enable", "sounds", "chime")
    assert json.loads(run("status", "sounds", "chime", "--json")) == {"sounds": True, "chime": True}
    state_file = tmp_path / "home" / ".local" / "state" / "goldenglass" / "system.json"
    assert set(json.loads(state_file.read_text())) == {"sounds", "chime"}

    run("disable", "sounds")
    assert json.loads(run("status", "--json", "sounds", "chime")) == {"sounds": False, "chime": True}
    run("disable", "chime")
    assert fakes.config == {}
    assert json.loads(state_file.read_text()) == {}


def test_cli_rejects_unknown_part(fakes):
    result = subprocess.run([sys.executable, str(TOOLS / "system.py"), "enable", "wallpaper"],
                            env=dict(os.environ), capture_output=True, text=True)
    assert result.returncode != 0
    assert "wallpaper" in result.stderr
    assert fakes.config == {}


# --- Plymouth (root en producción) -----------------------------------------------

@pytest.fixture
def plymouth(fakes, monkeypatch):
    for theme in (*system.PLYMOUTH_THEMES.values(), "bgrt", "spinner"):
        folder = system.PLYMOUTH_DIR / theme
        folder.mkdir(parents=True)
        (folder / f"{theme}.plymouth").write_text("[Plymouth Theme]\n")
    # sin leer /proc/cmdline ni /etc/mkinitcpio.conf
    monkeypatch.setattr(system, "plymouth_warnings", lambda: [])
    umask = os.umask(0o022)  # run_system fija el umask del proceso
    yield fakes
    os.umask(umask)


def plymouth_state() -> dict:
    return json.loads(system.ROOT_STATE.read_text())


def test_plymouth_enable_and_disable(plymouth):
    plymouth.set_plymouth("spinner")
    system.run_system([("enable", "plymouth", "dark")])
    assert plymouth.data["plymouth"] == "goldenglass"
    assert ["plymouth-set-default-theme", "goldenglass", "--rebuild-initrd"] in plymouth.data["calls"]
    assert plymouth_state() == {"plymouth": {"previous": "spinner"}}

    # cambiar de variante no pisa el tema guardado
    system.run_system([("enable", "plymouth", "light")])
    assert plymouth.data["plymouth"] == "goldenglass-light"
    assert plymouth_state() == {"plymouth": {"previous": "spinner"}}

    system.run_system([("disable", "plymouth", "dark")])
    assert plymouth.data["plymouth"] == "spinner"
    assert plymouth_state() == {}


def test_plymouth_disable_resets_when_previous_is_gone(plymouth):
    plymouth.set_plymouth("spinner")
    system.run_system([("enable", "plymouth", "dark")])
    (system.PLYMOUTH_DIR / "spinner" / "spinner.plymouth").unlink()
    system.run_system([("disable", "plymouth", "dark")])
    assert ["plymouth-set-default-theme", "--reset", "--rebuild-initrd"] in plymouth.data["calls"]
    assert plymouth.data["plymouth"] == "bgrt"


def test_plymouth_disable_respects_admin_changes(plymouth):
    system.run_system([("enable", "plymouth", "dark")])
    plymouth.set_plymouth("spinner")  # el administrador eligió otro
    system.run_system([("disable", "plymouth", "dark")])
    assert plymouth.data["plymouth"] == "spinner"


def test_plymouth_rebuild_failure_keeps_previous_theme(plymouth, monkeypatch):
    plymouth.set_plymouth("spinner")
    monkeypatch.setenv("FAKE_REBUILD_FAILS", "1")
    with pytest.raises(SystemExit):
        system.run_system([("enable", "plymouth", "dark")])
    assert plymouth.data["plymouth"] == "spinner"


def test_plymouth_theme_not_installed(plymouth):
    (system.PLYMOUTH_DIR / "goldenglass" / "goldenglass.plymouth").unlink()
    with pytest.raises(SystemExit):
        system.run_system([("enable", "plymouth", "dark")])
    assert plymouth.data["plymouth"] == "bgrt"
