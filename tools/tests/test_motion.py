# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Movimiento de los plasmoids (Motion.qml, docs/ARCHITECTURE.md «Movimiento»).

- Guarda estática: toda duración de animación (o overshoot) de
  plasma/plasmoids/**/*.qml que sale de los tokens pasa por Motion, para seguir
  la velocidad de animación global de Plasma; las esperas que no son
  animaciones (WAITS, Timer.interval) no se escalan.
- Los plasmoids que usan Motion reciben Motion.qml, Accessibility.qml, AccessibilityReader.qml y su
  qmldir (SHARED).
- Prueba en ejecución (opcional: se salta sin qml6, sin Kirigami o sin un
  plugin de plataforma de Kirigami que lea kdeglobals): Motion.ms(100) con
  AnimationDurationFactor 0, 0.25, 1 y 2 en un kdeglobals temporal.
- «Reduce motion» at run time: with an AccessibilityReader.qml that reports it on,
  moves take 0 ms, fades motion.reduced_fade_ms and there is no overshoot;
  without the org.goldenglass.glass module it stays off.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import gen_tokens
import plasmoids
import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "plasma" / "plasmoids"
MOTION_SOURCE = SOURCES / "org.goldenglass.launchpad" / "contents" / "ui"

# esperas de interfaz: no son animaciones y no siguen el factor global
WAITS = {"label_delay_ms", "preview_hide_ms", "bar_hide_ms", "glass_update_ms"}

ASSIGN = re.compile(r"\b(?P<prop>duration|easing\.overshoot|interval)\s*[:=](?!=)\s*(?P<rhs>[^;}\n]+)")
MS_NAME = re.compile(r"\b\w*_ms(?:_\w+)?\b")
TOKEN_REF = re.compile(r"\bT\.tokens\.|\.(?:tok|cc)\.")
SCALED = re.compile(r"\bMotion\.(?:ms|moveMs|fadeMs)\(")


def _code_lines(text: str):
    """(número, línea) sin comentarios // ni /* … */."""
    in_block = False
    for number, line in enumerate(text.splitlines(), 1):
        code = ""
        rest = line
        while rest:
            if in_block:
                end = rest.find("*/")
                if end < 0:
                    rest = ""
                    break
                rest = rest[end + 2:]
                in_block = False
            else:
                start = rest.find("/*")
                comment = re.search(r"(^|\s)//", rest)
                if comment and (start < 0 or comment.start() < start):
                    code += rest[:comment.start()]
                    break
                if start < 0:
                    code += rest
                    break
                code += rest[:start]
                rest = rest[start + 2:]
                in_block = True
        yield number, code


def violations(text: str) -> list[str]:
    """Duraciones u overshoots de los tokens sin Motion, y esperas escaladas."""
    found = []
    for number, code in _code_lines(text):
        for match in ASSIGN.finditer(code):
            prop, rhs = match["prop"], match["rhs"].strip()
            names = set(MS_NAME.findall(rhs))
            if prop == "interval":
                if "Motion." in rhs:
                    found.append(f"{number}: espera escalada con Motion: {rhs}")
                continue
            if prop == "duration":
                token = bool(TOKEN_REF.search(rhs) or names)
                waits_only = bool(names) and names <= WAITS
                if token and not waits_only and not SCALED.search(rhs):
                    found.append(f"{number}: duración de los tokens sin Motion.ms/moveMs/fadeMs: {rhs}")
                continue
            token = bool(TOKEN_REF.search(rhs) or re.search(r"\w_overshoot\b", rhs))
            if token and "Motion.overshoot(" not in rhs:
                found.append(f"{number}: overshoot de los tokens sin Motion.overshoot: {rhs}")
    return found


def _qml_files() -> list[Path]:
    return sorted(SOURCES.glob("*/contents/**/*.qml"))


def test_guard_catches_unscaled_durations() -> None:
    bad = [
        "duration: root.tok.wheel_ms",
        "NumberAnimation { duration: T.tokens.dock.magnification_ms; easing.type: Easing.OutCubic }",
        "duration: panel.cc.close_ms * panel.cc.close_unblur_at",
        "duration: T.tokens.dock.bounce_ms / 2",
        "duration: panel.cc.open_ms_y",
        "easing.overshoot: panel.cc.open_overshoot",
        "wheelAnimation.duration = root.tok.wheel_ms;",
        "interval: Motion.ms(T.tokens.dock.label_delay_ms)",
    ]
    for line in bad:
        assert violations(line), line
    good = [
        "duration: Motion.ms(root.tok.wheel_ms)",
        "duration: Motion.fadeMs(panel.cc.close_ms) * panel.cc.close_unblur_at",
        "NumberAnimation { duration: Motion.moveMs(T.tokens.dock.magnification_ms); easing.type: Easing.OutCubic }",
        "easing.overshoot: Motion.overshoot(panel.cc.open_overshoot)",
        "duration: Kirigami.Units.shortDuration",
        "interval: T.tokens.dock.label_delay_ms",
        "interval: root.tok.bar_hide_ms",
        "item.updateInterval = panel.cc.glass_update_ms;",
        "if (anim.duration === 0) {",
        "// duration: T.tokens.dock.bounce_ms",
        "/* duration: root.tok.wheel_ms */",
    ]
    for line in good:
        assert not violations(line), line


def test_token_durations_go_through_motion() -> None:
    problems = []
    for path in _qml_files():
        problems += [f"{path.relative_to(ROOT)}:{v}" for v in violations(path.read_text(encoding="utf-8"))]
    assert not problems, "\n".join(problems)


def _plugin_id(folder: Path) -> str:
    return json.loads((folder / "metadata.json").read_text(encoding="utf-8"))["KPlugin"]["Id"]


def test_plasmoids_using_motion_get_it() -> None:
    """Quien usa Motion (en sus archivos o en los de SHARED) recibe Motion.qml y qmldir."""
    origin = "org.goldenglass.launchpad"
    for folder in sorted(p for p in SOURCES.iterdir() if p.is_dir()):
        plugin_id = _plugin_id(folder)
        shared = plasmoids.SHARED.get(plugin_id, {})
        files = list((folder / "contents" / "ui").glob("*.qml"))
        files += [SOURCES / src / "contents" / "ui" / name for src, names in shared.items() for name in names
                  if name.endswith(".qml")]
        uses = any("Motion." in f.read_text(encoding="utf-8") for f in files if f.name != "Motion.qml")
        if not uses or plugin_id == origin:
            continue
        assert set(plasmoids.MOTION) <= set(shared.get(origin, [])), plugin_id


def test_motion_source_files() -> None:
    qmldir = (MOTION_SOURCE / "qmldir").read_text(encoding="utf-8")
    assert "singleton Motion 1.0 Motion.qml" in qmldir.splitlines()
    assert (MOTION_SOURCE / "Motion.qml").read_text(encoding="utf-8").count("pragma Singleton") == 1
    assert "singleton Accessibility 1.0 Accessibility.qml" in qmldir.splitlines()
    reader = (MOTION_SOURCE / "AccessibilityReader.qml").read_text(encoding="utf-8")
    assert "import org.goldenglass.glass" in reader and "AccessibilitySettings {" in reader
    assert '"AccessibilityReader.qml"' in (MOTION_SOURCE / "Accessibility.qml").read_text(encoding="utf-8")
    assert "Accessibility.reduceMotion" in (MOTION_SOURCE / "Motion.qml").read_text(encoding="utf-8")


def test_shared_qmldir_is_merged(tmp_path: Path) -> None:
    source = tmp_path / "src" / "qmldir"
    source.parent.mkdir()
    source.write_text("# comentario\nsingleton Motion 1.0 Motion.qml\n", encoding="utf-8")
    target = tmp_path / "qmldir"
    plasmoids.copy_shared(source, target)
    assert target.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")

    target.write_text("singleton Other 1.0 Other.qml\n", encoding="utf-8")
    plasmoids.copy_shared(source, target)
    plasmoids.copy_shared(source, target)  # sin duplicar
    assert target.read_text(encoding="utf-8").splitlines() == [
        "singleton Other 1.0 Other.qml", "singleton Motion 1.0 Motion.qml"]


def test_motion_tokens_are_validated(tokens: dict) -> None:
    gen_tokens.validate(tokens)
    for key, value in (("kirigami_long_ms", 0), ("kirigami_long_ms", "200"), ("reduced_fade_ms", -1),
                       ("reduced_fade_ms", True), ("reduced_fade_ms", float("nan"))):
        broken = {**tokens, "motion": {**tokens["motion"], key: value}}
        with pytest.raises(SystemExit, match=rf"\[motion\]\.{key}"):
            gen_tokens.validate(broken)


# --- en ejecución -----------------------------------------------------------

PROBE = """\
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    // un archivo del directorio que no está en el qmldir: se sigue resolviendo
    Probe { id: probe }
    Component.onCompleted: {
        probe.close.restart();
        console.warn("MOTION " + JSON.stringify({
            long: Kirigami.Units.longDuration,
            factor: Motion.factor,
            animated: Motion.animated,
            reduced: Motion.reduced,
            reduceTransparency: Accessibility.reduceTransparency,
            ms: Motion.ms(100),
            moveMs: Motion.moveMs(100),
            fadeMs: Motion.fadeMs(100),
            overshoot: Motion.overshoot(1.5),
            closedSync: probe.closed,
        }));
        Qt.quit();
    }
}
"""

# como el cierre de los paneles: con duración 0 termina dentro de restart()
PROBE_ITEM = """\
import QtQuick

Item {
    id: item
    property bool closed: false
    property alias close: close
    ParallelAnimation {
        id: close
        NumberAnimation { target: item; property: "opacity"; to: 0; duration: Motion.fadeMs(100) }
        SequentialAnimation {
            PauseAnimation { duration: Motion.fadeMs(100) * 0.5 }
            ScriptAction { script: item.opacity = 0 }
        }
        onFinished: item.closed = true
    }
}
"""


def _qml_binary() -> str | None:
    found = shutil.which("qml6")
    if found:
        return found
    fallback = Path("/usr/lib/qt6/bin/qml")
    return str(fallback) if fallback.exists() else None


def _run_probe(qml: str, folder: Path, home: Path, factor: float, extra_env: dict | None = None) -> dict:
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".config" / "kdeglobals").write_text(f"[KDE]\nAnimationDurationFactor={factor}\n", encoding="utf-8")
    runtime = home / "runtime"
    runtime.mkdir(mode=0o700, exist_ok=True)
    env = {
        **os.environ,
        # nada de la sesión real: configuración y bus de D-Bus propios
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CONFIG_DIRS": str(home / "none"),
        "XDG_RUNTIME_DIR": str(runtime),
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={home / 'no-bus'}",
        "QT_QPA_PLATFORM": "offscreen",
        "QT_FORCE_STDERR_LOGGING": "1",
        # el plugin de plataforma de Kirigami que usa plasmashell (KirigamiPlasmaStyle)
        "QT_QUICK_CONTROLS_STYLE": "Plasma",
        **(extra_env or {}),
    }
    result = subprocess.run([qml, str(folder / "main.qml")], env=env, capture_output=True, text=True,
                            timeout=60, check=False)
    output = result.stdout + result.stderr
    if 'module "org.kde.kirigami" is not installed' in output:
        pytest.skip("sin Kirigami")
    match = re.search(r"MOTION (\{.*\})", output)
    assert match, output
    return json.loads(match[1])


# stands in for AccessibilitySettings with «Reduce motion» on
REDUCE_ON = """\
import QtQuick

QtObject {
    readonly property bool reduceMotion: true
    readonly property bool reduceTransparency: false
    readonly property bool showBorders: false
}
"""

# what AccessibilityReader.qml does without goldenglass-kstyle
MODULE_MISSING = """\
import org.goldenglass.missing

AccessibilitySettings {}
"""


def _probe_folder(tmp_path: Path, tokens: dict, motion_reduce: str | None = None) -> Path:
    folder = tmp_path / "ui"
    folder.mkdir()
    for name in plasmoids.MOTION:
        shutil.copy2(MOTION_SOURCE / name, folder / name)
    if motion_reduce is not None:
        (folder / "AccessibilityReader.qml").write_text(motion_reduce, encoding="utf-8")
    plasmoids.write_tokens_js(folder / "tokens.js", tokens)
    (folder / "main.qml").write_text(PROBE, encoding="utf-8")
    (folder / "Probe.qml").write_text(PROBE_ITEM, encoding="utf-8")
    return folder


@pytest.mark.skipif(_qml_binary() is None, reason="sin qml6")
def test_motion_follows_global_animation_speed(tmp_path: Path, tokens: dict) -> None:
    folder = _probe_folder(tmp_path, tokens)
    qml = _qml_binary()
    assert qml

    results = {f: _run_probe(qml, folder, tmp_path / f"home-{f}", f) for f in (0, 0.25, 1, 2)}
    for factor, values in results.items():
        print(f"AnimationDurationFactor={factor}: {values}")
    if results[2]["long"] == results[1]["long"]:
        pytest.skip("el plugin de plataforma de Kirigami no lee AnimationDurationFactor")

    base = tokens["motion"]["kirigami_long_ms"]
    assert results[1]["long"] == base
    expected = {0: 0, 0.25: 25, 1: 100, 2: 200}
    for factor, values in results.items():
        assert values["ms"] == pytest.approx(expected[factor]), factor
        assert values["moveMs"] == values["ms"] and values["fadeMs"] == values["ms"], factor
        assert values["overshoot"] == 1.5, factor
        assert values["animated"] is (factor > 0), factor
        assert values["reduced"] is False, factor
    # con factor 0 la animación de cierre termina dentro de restart()
    assert results[0]["closedSync"] is True
    assert results[1]["closedSync"] is False


@pytest.mark.skipif(_qml_binary() is None, reason="sin qml6")
def test_reduce_motion_turns_moves_into_fades(tmp_path: Path, tokens: dict) -> None:
    qml = _qml_binary()
    assert qml
    folder = _probe_folder(tmp_path, tokens, REDUCE_ON)
    results = {f: _run_probe(qml, folder, tmp_path / f"home-{f}", f) for f in (0, 1)}
    fade = tokens["motion"]["reduced_fade_ms"]
    reduced = results[1]
    assert reduced["reduced"] is True
    assert reduced["moveMs"] == 0
    assert reduced["overshoot"] == 0
    if reduced["long"] != tokens["motion"]["kirigami_long_ms"]:
        pytest.skip("el plugin de plataforma de Kirigami no lee AnimationDurationFactor")
    assert reduced["ms"] == pytest.approx(100)
    assert reduced["fadeMs"] == pytest.approx(fade)
    # without animations nothing moves or fades, and closing still ends at once
    assert results[0]["fadeMs"] == 0 and results[0]["closedSync"] is True


@pytest.mark.skipif(_qml_binary() is None, reason="sin qml6")
def test_reduce_motion_is_off_without_the_glass_module(tmp_path: Path, tokens: dict) -> None:
    qml = _qml_binary()
    assert qml
    folder = _probe_folder(tmp_path, tokens, MODULE_MISSING)
    values = _run_probe(qml, folder, tmp_path / "home", 1)
    assert values["reduced"] is False
    assert values["reduceTransparency"] is False
    assert values["overshoot"] == 1.5


BUILT_GLASS_MODULE = ROOT / "build" / "cmake" / "bin"


@pytest.mark.skipif(_qml_binary() is None, reason="sin qml6")
@pytest.mark.skipif(not (BUILT_GLASS_MODULE / "org" / "goldenglass" / "glass" / "qmldir").is_file(),
                    reason="org.goldenglass.glass not built in build/cmake")
def test_reduce_motion_follows_goldenglassrc(tmp_path: Path, tokens: dict) -> None:
    qml = _qml_binary()
    assert qml
    folder = _probe_folder(tmp_path, tokens)
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    (home / ".config" / "goldenglassrc").write_text("[Accessibility]\nReduceMotion=true\nReduceTransparency=true\n",
                                                    encoding="utf-8")
    values = _run_probe(qml, folder, home, 1, {"QML_IMPORT_PATH": str(BUILT_GLASS_MODULE)})
    assert values["reduced"] is True
    assert values["reduceTransparency"] is True
    assert values["moveMs"] == 0
