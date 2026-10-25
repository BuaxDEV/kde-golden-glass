#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-glass: cambia en vivo el nivel de vidrio de GoldenGlass.

  goldenglass-glass --level 0.8     # 0 = más transparente, 1 = más opaco
  goldenglass-glass --get           # nivel actual
  goldenglass-glass --refraction on|off   # efecto de KWin goldenglass_glass
  goldenglass-glass --get-refraction      # on | off | unavailable
  goldenglass-glass --menubar-background on|off   # franja de vidrio tras la barra de menús
  goldenglass-glass --get-menubar-background      # on | off
  goldenglass-glass --check         # al iniciar sesión (autostart), ver abajo

Lo que hace con un nivel:
  1. Escribe goldenglassrc: [Glass] Level y la opacidad de menús, toolbars y
     barra lateral de Dolphin (las leen el estilo de apps y la decoración).
  2. Plasma Style: el nivel por defecto usa el tema "GoldenGlass" del paquete;
     cualquier otro genera "GoldenGlassTuned" en ~/.local/share con ese nivel.
     Si GoldenGlass o GoldenGlassTuned está activo, cambia a la variante
     correcta (Plasma no relee un tema que cambia en disco; ver
     docs/ARCHITECTURE.md §4.4). El tema del paquete nunca se sobrescribe.
  3. Avisa a las apps (D-Bus org.goldenglass.Style) y reconfigura KWin (el
     efecto de refracción relee el nivel).

Refracción: el efecto goldenglass_glass sustituye al Blur de KWin (los dos a la
vez difuminarían dos veces). --check, al iniciar sesión: la primera vez lo
activa (es el valor de fábrica); si está pedido pero KWin no lo cargó (KWin
actualizado sin recompilar goldenglass-kstyle) vuelve a cargar el Blur; si sí
lo cargó, se asegura de que el Blur no esté cargado.

Concurrencia: toda operación que escribe (--level, --refraction,
--menubar-background, --check) toma un flock exclusivo en
$XDG_RUNTIME_DIR/goldenglass-glass.lock (sin esa variable, en
/tmp/goldenglass-glass-UID.lock); la segunda espera a la primera. --get* no
esperan. GoldenGlassTuned se escribe en un directorio hermano y se cambia de
golpe, así Plasma nunca lo ve a medias.

Fondo de la barra de menús: solo escribe goldenglassrc [Plasma]
MenubarBackground (con aviso de cambio); el Panel.qml del shell lo lee en vivo
con MenuBarSettings (módulo QML org.goldenglass.glass). No toca el Plasma Style.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import fcntl
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import plasma_theme  # noqa: E402
from ggcommon import load_tokens  # noqa: E402

BASE_ID = plasma_theme.THEME_ID
TUNED_ID = BASE_ID + "Tuned"
TUNED_NAME = "GoldenGlass (vidrio ajustado)"
RC = "goldenglassrc"
STYLE_KEYS = ("MenuOpacity", "ToolBarOpacity", "DolphinSidebarOpacity")
# libplasma agrupa los avisos de cambio de tema con un temporizador de 100 ms
# (ThemePrivate::updateNotificationTimer): en el rebote hay que dejar que el
# tema intermedio llegue a los paneles antes de volver, o no se repintan.
BOUNCE_DELAY = 0.35


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")


def kread(file: str, group: str, key: str, default: str = "") -> str:
    r = subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key, "--default", default],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def kwrite(file: str, group: str, key: str, value) -> None:
    subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--notify", str(value)],
                   check=True)


def dbus(*args: str) -> None:
    subprocess.run(["dbus-send", "--session", *args], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def set_plasma_theme(name: str) -> None:
    """Cambia el Plasma Style activo.

    Primero, directamente en plasmashell (script `theme = …`, que también
    escribe plasmarc): no depende de que llegue la notificación de
    configuración, que el spike vio perderse alguna vez. --print-reply hace la
    llamada síncrona, así dos cambios seguidos se aplican en orden. Si
    plasmashell no está en marcha, solo se escribe plasmarc.
    """
    r = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.kde.plasmashell", "/PlasmaShell",
                        "org.kde.PlasmaShell.evaluateScript", f"string:theme = {json.dumps(name)}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode != 0:
        kwrite("plasmarc", "Theme", "name", name)


def lock_path() -> Path:
    """Archivo del cerrojo: en $XDG_RUNTIME_DIR (de cada usuario, se vacía al cerrar la sesión); sin él, en /tmp."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and os.path.isdir(runtime):
        return Path(runtime) / "goldenglass-glass.lock"
    return Path(tempfile.gettempdir()) / f"goldenglass-glass-{os.getuid()}.lock"


@contextlib.contextmanager
def session_lock():
    """Serializa las operaciones que escriben (flock exclusivo).

    El módulo de Ajustes y el slider del Centro de control pueden lanzar dos
    goldenglass-glass a la vez; sin cerrojo se pisarían al regenerar
    GoldenGlassTuned y al escribir goldenglassrc. El segundo espera a que
    termine el primero. El archivo no se borra nunca (borrarlo permitiría que
    dos procesos tuvieran cerrojos de archivos distintos); el kernel suelta el
    cerrojo si el proceso muere. Las lecturas (--get*) no lo toman.
    Si el archivo no se puede abrir de forma segura, sigue sin cerrojo.
    """
    path = lock_path()
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError as e:
        print(f"goldenglass-glass: sin cerrojo ({path}: {e.strerror})", file=sys.stderr)
        fd = -1
    if fd >= 0 and os.fstat(fd).st_uid != os.getuid():
        # /tmp compartido: otro usuario creó el archivo
        os.close(fd)
        print(f"goldenglass-glass: sin cerrojo ({path} es de otro usuario)", file=sys.stderr)
        fd = -1
    try:
        if fd >= 0:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fd >= 0:
            os.close(fd)  # suelta el cerrojo


def _exchange(a: Path, b: Path) -> bool:
    """Intercambia dos rutas de forma atómica (renameat2 con RENAME_EXCHANGE, Linux 3.15 o posterior)."""
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError):
        return False
    at_fdcwd, rename_exchange = -100, 2
    return renameat2(at_fdcwd, os.fsencode(a), at_fdcwd, os.fsencode(b), rename_exchange) == 0


def _swap_dir(new: Path, dst: Path, stage: Path) -> None:
    """Deja `new` en `dst` sin que se vea un `dst` a medias; el tema anterior queda en `stage`."""
    if not dst.exists():
        new.rename(dst)
    elif not _exchange(new, dst):
        # sin renameat2: dos renombrados; solo falta `dst` un instante
        dst.rename(stage / "old")
        new.rename(dst)
    # con el intercambio, `new` pasa a ser el tema anterior y `stage` se borra con él


def write_tuned_theme(tokens: dict, level: float) -> None:
    """Genera GoldenGlassTuned al nivel dado en ~/.local/share/plasma/desktoptheme.

    Se escribe en un directorio hermano y se cambia de golpe por el tema
    anterior: Plasma nunca ve un tema a medias.
    """
    with tempfile.TemporaryDirectory(prefix="goldenglass-glass.") as tmp:
        plasma_theme.build(tokens, Path(tmp), level)
        src = Path(tmp) / "plasma" / "desktoptheme" / BASE_ID
        meta_path = src / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["KPlugin"]["Id"] = TUNED_ID
        meta["KPlugin"]["Name"] = TUNED_NAME
        meta["KPlugin"]["Description"] = f"GoldenGlass at glass level {level:.2f} (generated by goldenglass-glass)"
        meta_path.write_text(json.dumps(meta, indent=4) + "\n", encoding="utf-8")

        dst = data_home() / "plasma" / "desktoptheme" / TUNED_ID
        dst.parent.mkdir(parents=True, exist_ok=True)
        # oculto (con punto) y en el mismo directorio: el renombrado es atómico
        stage = Path(tempfile.mkdtemp(prefix=f".{TUNED_ID}.", dir=dst.parent))
        try:
            new = stage / "new"
            shutil.copytree(src, new)
            # KSvg solo descarta la caché de imágenes del tema si metadata.json
            # es más nuevo, comparando segundos: dos niveles aplicados en el
            # mismo segundo reutilizarían las imágenes del anterior. Se borra la
            # caché para que la próxima carga renderice los SVG nuevos.
            (new / "metadata.json").touch()
            _swap_dir(new, dst, stage)
            (cache_home() / f"plasma_theme_{TUNED_ID}.kcache").unlink(missing_ok=True)
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def set_level(level: float, reload_plasma: bool = True) -> None:
    tokens = load_tokens()
    if not math.isfinite(level):
        # nan pasaría por min/max y se escribiría tal cual
        raise ValueError(f"nivel de vidrio no válido: {level}")
    level = min(max(level, 0.0), 1.0)
    percent = round(plasma_theme.glass_alpha(tokens, level) * 100)

    # 1. Estilo de apps y decoración.
    kwrite(RC, "Glass", "Level", f"{level:.3f}")
    for key in STYLE_KEYS:
        kwrite(RC, "Style", key, percent)

    # 2. Plasma Style.
    is_default = abs(level - tokens["glass"]["default_level"]) < 0.005
    target = BASE_ID if is_default else TUNED_ID
    if not is_default:
        write_tuned_theme(tokens, level)
    current = kread("plasmarc", "Theme", "name", "default")
    if reload_plasma and current in (BASE_ID, TUNED_ID):
        if current == TUNED_ID and target == TUNED_ID:
            # Mismo id con archivos nuevos: pasar un instante por el tema base
            # (solo cambia la opacidad; nunca se ve otro tema).
            set_plasma_theme(BASE_ID)
            time.sleep(BOUNCE_DELAY)
        if current != target or target == TUNED_ID:
            set_plasma_theme(target)

    # 3. Apps (QStyle) y KWin (decoración).
    dbus("--type=signal", "/GoldenGlassStyle", "org.goldenglass.Style.reparseConfiguration")
    dbus("--type=method_call", "--dest=org.kde.KWin", "/KWin", "org.kde.KWin.reconfigure")


# --- refracción (efecto de KWin goldenglass_glass) -----------------------------

EFFECT = "goldenglass_glass"


def effects_call(method: str, *args: str) -> str:
    r = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.kde.KWin", "/Effects",
                        f"org.kde.kwin.Effects.{method}", *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def effect_available() -> bool:
    # listOfEffects es una propiedad, no un método
    r = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.kde.KWin", "/Effects",
                        "org.freedesktop.DBus.Properties.Get", "string:org.kde.kwin.Effects", "string:listOfEffects"],
                       capture_output=True, text=True)
    return f'"{EFFECT}"' in r.stdout


def effect_loaded(name: str) -> bool:
    return "boolean true" in effects_call("isEffectLoaded", f"string:{name}")


def use_glass_effect(on: bool) -> None:
    """One or the other: goldenglass_glass or KWin's Blur, live and in kwinrc.

    The live swap goes first, unloading before loading: KWin withdraws the
    blur capability (ext-background-effect) a moment after a blur provider
    unloads, so the old one must go before the new one comes. Writing kwinrc
    first lets KWin reload both from the notification in the other order and
    leaves Plasma without blur until KWin restarts.
    """
    old, new = ("blur", EFFECT) if on else (EFFECT, "blur")
    effects_call("unloadEffect", f"string:{old}")
    effects_call("loadEffect", f"string:{new}")
    kwrite("kwinrc", "Plugins", f"{EFFECT}Enabled", "true" if on else "false")
    kwrite("kwinrc", "Plugins", "blurEnabled", "false" if on else "true")


def get_refraction() -> str:
    if not effect_available():
        return "unavailable"
    return "on" if kread("kwinrc", "Plugins", f"{EFFECT}Enabled", "false") == "true" else "off"


def set_refraction(on: bool) -> None:
    if on and not effect_available():
        raise SystemExit(f"goldenglass-glass: KWin no encuentra el efecto {EFFECT} "
                         "(¿goldenglass-kstyle compilado para esta versión de KWin?)")
    use_glass_effect(on)


def check() -> None:
    wanted = kread("kwinrc", "Plugins", f"{EFFECT}Enabled", "")
    if wanted == "":
        # primera vez: de fábrica activada, si KWin la tiene
        if effect_available():
            use_glass_effect(True)
        return
    if wanted != "true":
        return
    if effect_loaded(EFFECT):
        if effect_loaded("blur"):
            effects_call("unloadEffect", "string:blur")
        kwrite("kwinrc", "Plugins", "blurEnabled", "false")
    elif not effect_loaded("blur"):
        # pedido pero no cargó: que al menos haya blur (se deja pedido para
        # cuando vuelva a cargar, tras recompilar)
        kwrite("kwinrc", "Plugins", "blurEnabled", "true")
        effects_call("loadEffect", "string:blur")


# --- fondo de la barra de menús ------------------------------------------------

def get_menubar_background() -> bool:
    default = "true" if load_tokens()["plasma"]["menubar_background"] else "false"
    return kread(RC, "Plasma", "MenubarBackground", default) == "true"


def set_menubar_background(on: bool) -> None:
    kwrite(RC, "Plasma", "MenubarBackground", "true" if on else "false")


def get_level() -> float:
    default = float(load_tokens()["glass"]["default_level"])
    # un valor ilegible (editado a mano, nan…) vale como el de fábrica
    try:
        level = float(kread(RC, "Glass", "Level", str(default)))
    except ValueError:
        return default
    return level if math.isfinite(level) else default


def _level_arg(text: str) -> float:
    """--level: un número finito (float() acepta nan e inf)."""
    try:
        level = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"no es un número: {text}") from None
    if not math.isfinite(level):
        raise argparse.ArgumentTypeError(f"no es un número finito: {text}")
    return level


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="goldenglass-glass", description="Nivel de vidrio de GoldenGlass")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--level", type=_level_arg, metavar="0..1", help="0 = más transparente, 1 = más opaco")
    group.add_argument("--get", action="store_true", help="muestra el nivel actual")
    group.add_argument("--refraction", choices=["on", "off"], help="efecto de refracción de KWin")
    group.add_argument("--get-refraction", action="store_true", help="on, off o unavailable")
    group.add_argument("--menubar-background", choices=["on", "off"],
                       help="franja de vidrio translúcido tras la barra de menús")
    group.add_argument("--get-menubar-background", action="store_true", help="on u off")
    group.add_argument("--check", action="store_true", help="al iniciar sesión: Blur o refracción, nunca ninguno")
    ap.add_argument("--no-plasma-reload", action="store_true",
                    help="no cambiar el Plasma Style activo (solo generar y configurar)")
    args = ap.parse_args(argv)

    if args.get:
        print(f"{get_level():.3f}")
        return 0
    if args.get_refraction:
        print(get_refraction())
        return 0
    if args.refraction:
        with session_lock():
            set_refraction(args.refraction == "on")
        return 0
    if args.get_menubar_background:
        print("on" if get_menubar_background() else "off")
        return 0
    if args.menubar_background:
        with session_lock():
            set_menubar_background(args.menubar_background == "on")
        return 0
    if args.check:
        with session_lock():
            check()
        return 0
    with session_lock():
        set_level(args.level, reload_plasma=not args.no_plasma_reload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
