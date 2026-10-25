#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-system: activa o desactiva las partes de GoldenGlass que no
aplica el Global Theme (sonidos, chime, Plymouth; más adelante el login).

Los paquetes solo instalan; esto es lo que las activa. Antes de cambiar un
valor se guarda el anterior y `disable` lo restaura (si no existía, se borra).

  goldenglass-system status [PARTE…] [--json]
  goldenglass-system enable PARTE… [--variant dark|light]
  goldenglass-system disable PARTE…
  goldenglass-system apply [--plymouth dark|light|system] [--login on|off]

`apply` aplica varios cambios del sistema con una sola autenticación (lo usa
el módulo de Ajustes).

Partes del usuario (sin root; no se pueden activar con sudo):
  sounds   tema de sonidos GoldenGlass (kdeglobals) y sonido de Spectacle al
           guardar una captura
  chime    sonido al iniciar sesión en Plasma
Partes del sistema (root: con sudo, o pkexec + polkit si se llama sin él):
  plymouth tema de arranque goldenglass (--variant dark, el de fábrica) o
           goldenglass-light; regenera el initramfs
  login    pantalla de inicio de sesión según el gestor activo: con SDDM, el
           tema GoldenGlass; con Plasma Login Manager (no admite temas), el
           fondo de GoldenGlass y los ajustes de Plasma del usuario que lo
           pide (colores, estilo, fuentes, cursor, teclado). Nunca cambia de
           gestor

Estado guardado: ~/.local/state/goldenglass/system.json (usuario) y
/var/lib/goldenglass/system.json (sistema).
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "goldenglass" / "system.json"
ROOT_STATE = Path("/var/lib/goldenglass/system.json")
UNSET = "__goldenglass_unset__"  # kreadconfig6 lo devuelve si la clave no existe

# pkexec ejecuta este ayudante (acción de polkit org.goldenglass.system) para
# las partes del sistema; lo instala goldenglass-plasma.
HELPER = Path("/usr/lib/goldenglass/system-helper")

PLYMOUTH_DIR = Path("/usr/share/plymouth/themes")
PLYMOUTH_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
PLYMOUTH_THEMES = {"dark": "goldenglass", "light": "goldenglass-light"}


@dataclass(frozen=True)
class Entry:
    """Una clave de configuración de KDE (archivo en ~/.config, grupo, clave)."""
    file: str
    group: str
    key: str
    value: str

    @property
    def id(self) -> str:
        return f"{self.file}/{self.group}/{self.key}"


PARTS: dict[str, tuple[Entry, ...]] = {
    "sounds": (
        Entry("kdeglobals", "Sounds", "Theme", "GoldenGlass"),
        # Spectacle no suena al capturar: como macOS, con el sonido del obturador
        Entry("spectacle.notifyrc", "Event/newScreenshotSaved", "Action", "Popup|Sound"),
        Entry("spectacle.notifyrc", "Event/newScreenshotSaved", "Sound", "screen-capture"),
    ),
    "chime": (
        # Plasma trae el evento de inicio de sesión sin acción
        Entry("plasma_workspace.notifyrc", "Event/startkde", "Action", "Sound"),
    ),
}
SYSTEM_PARTS = ("plymouth", "login")

SDDM_THEME = Path("/usr/share/sddm/themes/GoldenGlass")
SDDM_CONF = Path("/etc/sddm.conf.d/99-goldenglass.conf")
SDDM_MARK = "# goldenglass-system"
CURSORS = Path("/usr/share/icons/GoldenGlass-cursors")
PLM_CONF = Path("/etc/plasmalogin.conf")
PLM_IMAGE = "file:///usr/share/wallpapers/GoldenGlass/"
WALLPAPER = Path("/usr/share/wallpapers/GoldenGlass")
# lo que copia «Aplicar ajustes de Plasma» del módulo de KDE (kcm_plasmalogin)
PLM_FILES = ("kdeglobals", "plasmarc", "kcminputrc", "kxkbrc", "fontconfig/fonts.conf")
MAX_FILE = 1 << 20  # bytes por archivo: sobra para cualquier kdeglobals o fonts.conf
AS_USER_TIMEOUT = 60  # s para leer o escribir esos archivos como otro usuario
# rutas absolutas que el fonts.conf del greeter puede usar (ver _greeter_fonts_conf)
SYSTEM_FONT_DIRS = (Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path("/etc/fonts"))


def _tool(name: str, package: str = "kconfig") -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"goldenglass-system: falta {name} (paquete {package})")
    return path


def read(entry: Entry) -> str | None:
    out = subprocess.run(
        [_tool("kreadconfig6"), "--file", entry.file, "--group", entry.group,
         "--key", entry.key, "--default", UNSET],
        check=True, capture_output=True, text=True,
    ).stdout.rstrip("\n")
    return None if out == UNSET else out


def write(entry: Entry, value: str | None) -> None:
    args = [_tool("kwriteconfig6"), "--notify", "--file", entry.file,
            "--group", entry.group, "--key", entry.key]
    args += ["--delete"] if value is None else [value]
    subprocess.run(args, check=True)


def load_state(path: Path = STATE) -> dict:
    """Estado guardado: {parte: {clave: valor previo}}. Si está dañado (JSON
    inválido o con otra forma) se avisa y se empieza de cero, para que enable y
    disable sigan funcionando; el siguiente guardado lo reemplaza."""
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except ValueError as exc:  # JSONDecodeError y UnicodeDecodeError lo son
        reason = str(exc)
    else:
        if isinstance(state, dict) and all(isinstance(value, dict) for value in state.values()):
            return state
        reason = "no tiene la forma {parte: {clave: valor}}"
    print(f"goldenglass-system: se ignora {path}, está dañado ({reason})", file=sys.stderr)
    return {}


def write_file(path: Path, text: str, mode: int = 0o644) -> None:
    """Escribe text en path de forma atómica, con permisos fijos y sin seguir
    enlaces: como root, en /var/lib o /etc, no depende del umask de quien llama
    (pkexec no lo cambia) ni de lo que haya dejado otro en el directorio."""
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    st = path.parent.stat()
    if os.geteuid() == 0 and st.st_uid == 0 and st.st_mode & 0o022:
        os.chmod(path.parent, 0o755)  # creado con un umask permisivo por versiones anteriores
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        os.fchmod(f.fileno(), mode)
        f.write(text)
    tmp.replace(path)


def save_state(state: dict, path: Path = STATE) -> None:
    write_file(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def is_enabled(part: str) -> bool:
    return all(read(e) == e.value for e in PARTS[part])


def enable(part: str, state: dict) -> None:
    saved = state.setdefault(part, {})
    for entry in PARTS[part]:
        current = read(entry)
        if current == entry.value:
            continue
        # el valor previo se guarda una sola vez: un segundo enable no lo pisa
        saved.setdefault(entry.id, current)
        write(entry, entry.value)


def disable(part: str, state: dict) -> None:
    saved = state.pop(part, {})
    for entry in PARTS[part]:
        if read(entry) != entry.value:
            continue  # lo cambió el usuario después: se respeta
        write(entry, saved.get(entry.id))


# --- Plymouth (root) ----------------------------------------------------------

def plymouth_theme() -> str:
    return subprocess.run([_tool("plymouth-set-default-theme", "plymouth")],
                          check=True, capture_output=True, text=True).stdout.strip()


def plymouth_installed(theme: str) -> bool:
    return PLYMOUTH_NAME.fullmatch(theme) is not None and (PLYMOUTH_DIR / theme / f"{theme}.plymouth").is_file()


def plymouth_warnings() -> list[str]:
    """Lo que impediría ver el tema; se avisa, no se corrige (ver ARCHITECTURE 4.9)."""
    warnings = []
    try:
        if "splash" not in Path("/proc/cmdline").read_text().split():
            warnings.append("no-splash")
    except OSError:
        pass
    confs = [Path("/etc/mkinitcpio.conf"), *sorted(Path("/etc/mkinitcpio.conf.d").glob("*.conf"))]
    hooks = [line for conf in confs if conf.is_file()
             for line in conf.read_text(errors="replace").splitlines()
             if line.lstrip().startswith("HOOKS")]
    if hooks and not any(re.search(r"\bplymouth\b", line) for line in hooks):
        warnings.append("no-hook")
    return warnings


WARNING_TEXT = {
    "no-splash": "falta «splash» en la línea de comandos del kernel: Plymouth no se mostrará",
    "no-hook": "falta el hook «plymouth» en HOOKS de mkinitcpio: Plymouth no se mostrará",
    "sddm-overridden": "/etc/sddm.conf fija [Theme] Current: el tema de GoldenGlass no se verá",
    "unsupported-manager": "el gestor de inicio de sesión no es SDDM ni Plasma Login Manager",
}


def plymouth_status() -> dict:
    theme = plymouth_theme()
    variant = next((v for v, t in PLYMOUTH_THEMES.items() if t == theme), None)
    try:
        previous = load_state(ROOT_STATE).get("plymouth", {}).get("previous")
    except (OSError, ValueError):
        previous = None
    return {
        "enabled": variant is not None,
        "variant": variant,
        "theme": theme,
        # el que vuelve con disable (si no se guardó, el de la distribución)
        "system_theme": theme if variant is None else previous,
        "installed": all(plymouth_installed(t) for t in PLYMOUTH_THEMES.values()),
        "warnings": plymouth_warnings(),
    }


def _set_plymouth(theme: str | None) -> None:
    """Fija el tema (None = el de la distribución) y regenera el initramfs; si
    falla, deja el tema anterior sin regenerar (el initramfs sigue con él)."""
    previous = plymouth_theme()
    args = [_tool("plymouth-set-default-theme", "plymouth")]
    args += ["--reset"] if theme is None else [theme]
    try:
        subprocess.run([*args, "--rebuild-initrd"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run([args[0], previous], check=False)
        raise SystemExit("goldenglass-system: no se pudo regenerar el initramfs; "
                         f"se mantiene el tema de Plymouth {previous}")


def enable_plymouth(variant: str, state: dict) -> None:
    theme = PLYMOUTH_THEMES[variant]
    if not plymouth_installed(theme):
        raise SystemExit(f"goldenglass-system: el tema de Plymouth {theme} no está instalado "
                         "(paquete goldenglass-plymouth)")
    for code in plymouth_warnings():
        print(f"goldenglass-system: aviso: {WARNING_TEXT[code]}", file=sys.stderr)
    current = plymouth_theme()
    if current == theme:
        return
    if current not in PLYMOUTH_THEMES.values():
        # el tema previo se guarda una sola vez: cambiar de variante no lo pisa
        state.setdefault("plymouth", {}).setdefault("previous", current)
    _set_plymouth(theme)


def disable_plymouth(state: dict) -> None:
    previous = state.pop("plymouth", {}).get("previous")
    if plymouth_theme() not in PLYMOUTH_THEMES.values():
        return  # lo cambió el administrador después: se respeta
    _set_plymouth(previous if previous and plymouth_installed(previous) else None)


# --- inicio de sesión (root) --------------------------------------------------

def display_manager() -> str | None:
    """Servicio del gestor activo sin «.service» (sddm, plasmalogin…)."""
    try:
        target = os.readlink("/etc/systemd/system/display-manager.service")
    except OSError:
        return None
    return Path(target).name.removesuffix(".service")


def _sddm_overridden() -> bool:
    """/etc/sddm.conf manda sobre sddm.conf.d: si fija el tema, el nuestro no se ve."""
    try:
        text = Path("/etc/sddm.conf").read_text(errors="replace")
    except OSError:
        return False
    return re.search(r"^\s*\[Theme\][^\[]*^\s*Current\s*=", text, re.M | re.S) is not None


def _plm_entry(key: str) -> list[str]:
    if key == "WallpaperPluginId":
        return ["--group", "Greeter", "--key", key]
    return ["--group", "Greeter", "--group", "Wallpaper", "--group", "org.kde.image",
            "--group", "General", "--key", key]


def _plm_read(key: str) -> str | None:
    if not PLM_CONF.exists():
        return None
    out = subprocess.run([_tool("kreadconfig6"), "--file", str(PLM_CONF), *_plm_entry(key),
                          "--default", UNSET], check=True, capture_output=True, text=True).stdout.rstrip("\n")
    return None if out == UNSET else out


def _plm_write(key: str, value: str | None) -> None:
    args = [_tool("kwriteconfig6"), "--file", str(PLM_CONF), *_plm_entry(key)]
    subprocess.run(args + (["--delete"] if value is None else [value]), check=True)


def login_status() -> dict:
    manager = display_manager()
    warnings = []
    if manager == "sddm":
        enabled = SDDM_CONF.is_file()
        installed = SDDM_THEME.is_dir()
        if enabled and _sddm_overridden():
            warnings.append("sddm-overridden")
    elif manager == "plasmalogin":
        try:
            enabled = _plm_read("Image") == PLM_IMAGE
        except (OSError, subprocess.CalledProcessError):
            enabled = False
        installed = WALLPAPER.is_dir()
    else:
        enabled, installed = False, False
        warnings.append("unsupported-manager")
    return {"manager": manager, "enabled": enabled, "installed": installed, "warnings": warnings}


def _invoking_user():
    """Quien pidió el cambio (pkexec o sudo); sus ajustes de Plasma se copian."""
    import pwd
    uid = os.environ.get("PKEXEC_UID") or os.environ.get("SUDO_UID")
    return pwd.getpwuid(int(uid)) if uid and uid != "0" else None


def _as_user(pw, fn):
    """Ejecuta fn() en un proceso hijo con la identidad de pw (sin privilegios de
    root) y devuelve su resultado (JSON). Así root nunca sigue enlaces del
    usuario ni escribe en un home ajeno con privilegios."""
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        code = 1
        try:
            os.close(read_fd)
            os.setgroups([])
            os.setgid(pw.pw_gid)
            os.setuid(pw.pw_uid)
            os.chdir(pw.pw_dir)
            payload = json.dumps(fn()).encode()
            with os.fdopen(write_fd, "wb") as out:
                out.write(payload)
            code = 0
        except BaseException as error:  # noqa: BLE001 — se informa por stderr y código
            print(f"goldenglass-system: {error}", file=sys.stderr)
        finally:
            os._exit(code)
    os.close(write_fd)

    def abort(reason: str):
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        raise SystemExit(f"goldenglass-system: {reason} (operación como {pw.pw_name})")

    # con límite de tiempo y de tamaño: root no se queda esperando a un home
    # colgado (NFS…) ni acumula lo que el hijo devuelva
    payload = bytearray()
    deadline = time.monotonic() + AS_USER_TIMEOUT
    with os.fdopen(read_fd, "rb", buffering=0) as data:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([data], [], [], remaining)[0]:
                abort("tardó demasiado")
            chunk = data.read(1 << 16)
            if not chunk:
                break
            payload += chunk
            if len(payload) > 8 * MAX_FILE * len(PLM_FILES):
                abort("devolvió demasiados datos")
    _, status = os.waitpid(pid, 0)
    if os.waitstatus_to_exitcode(status) != 0:
        raise SystemExit(f"goldenglass-system: falló una operación como {pw.pw_name}")
    return json.loads(payload)


def _read_file(path: Path) -> str | None:
    """Texto de path, o None si no existe. Solo archivos regulares de hasta
    MAX_FILE: un FIFO, un dispositivo o un archivo enorme no bloquean el
    proceso ni agotan la memoria."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    except (FileNotFoundError, NotADirectoryError):
        return None
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "no es un archivo regular")
        data = f.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise OSError(errno.EFBIG, f"ocupa más de {MAX_FILE >> 10} KiB")
    return data.decode("utf-8", errors="replace")


def _read_files(base: Path) -> dict:
    """Contenido de PLM_FILES bajo base (None si no existe; si no se puede
    leer, falta y no se toca). Se lee con la identidad del dueño (_as_user):
    seguir sus enlaces (stow, chezmoi…) no da acceso a nada que no pueda leer ya."""
    files = {}
    for name in PLM_FILES:
        try:
            files[name] = _read_file(base / name)
        except OSError as error:  # ilegible, no regular o demasiado grande
            print(f"goldenglass-system: aviso: se omite {base / name}: {error.strerror}", file=sys.stderr)
    return files


def _greeter_path_ok(element) -> bool:
    """Si una ruta de fonts.conf (<dir>, <include>, <cachedir>) se queda en el
    sistema o en el home del greeter: absoluta solo bajo SYSTEM_FONT_DIRS;
    relativa solo con «~», prefix="xdg" o prefix="relative" (las demás dependen
    del directorio de trabajo); nunca con «..»."""
    text = (element.text or "").strip()
    path = Path(text)
    if not text or ".." in path.parts:
        return False
    if path.is_absolute():
        return any(path.is_relative_to(d) for d in SYSTEM_FONT_DIRS)
    return text.startswith("~") or element.get("prefix") in ("xdg", "relative")


def _greeter_fonts_conf(text: str) -> str | None:
    """fonts.conf del usuario para el greeter, que ve todo el mundo: sin rutas
    que carguen fuentes o configuración de un home (ver _greeter_path_ok).
    None si no es XML válido."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    if root.tag != "fontconfig":
        return None
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag in ("dir", "include", "cachedir") and not _greeter_path_ok(child):
                print(f"goldenglass-system: aviso: fonts.conf: se omite <{child.tag}>"
                      f"{(child.text or '').strip()}</{child.tag}> en el greeter", file=sys.stderr)
                parent.remove(child)
    return ('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            + ET.tostring(root, encoding="unicode") + "\n")


def _write_files(base: Path, files: dict) -> None:
    """Escribe (o borra si es None) PLM_FILES bajo base y vacía la caché."""
    shutil.rmtree(base.parent / ".cache", ignore_errors=True)
    for name in PLM_FILES:
        if name not in files:
            continue
        content = files[name]
        path = base / name
        if content is None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)


def enable_login(state: dict) -> None:
    manager = display_manager()
    saved = state.setdefault("login", {})
    if manager == "sddm":
        if not SDDM_THEME.is_dir():
            raise SystemExit("goldenglass-system: el tema de SDDM GoldenGlass no está instalado "
                             "(paquete goldenglass-login)")
        lines = [f"{SDDM_MARK}: se borra con «goldenglass-system disable login»",
                 "[Theme]", "Current=GoldenGlass"]
        if CURSORS.is_dir():
            lines.append("CursorTheme=GoldenGlass-cursors")
        write_file(SDDM_CONF, "\n".join(lines) + "\n")
        if _sddm_overridden():
            print("goldenglass-system: aviso: /etc/sddm.conf fija [Theme] Current y manda sobre "
                  f"{SDDM_CONF.name}", file=sys.stderr)
    elif manager == "plasmalogin":
        import pwd
        if not WALLPAPER.is_dir():
            raise SystemExit("goldenglass-system: el fondo GoldenGlass no está instalado "
                             "(paquete goldenglass-wallpapers)")
        plm = saved.setdefault("plasmalogin", {})
        # valores previos: una sola vez, como en las demás partes
        if "conf" not in plm:
            plm["conf"] = {key: _plm_read(key) for key in ("WallpaperPluginId", "Image")}
        _plm_write("WallpaperPluginId", "org.kde.image")
        _plm_write("Image", PLM_IMAGE)
        user = _invoking_user()
        if user is None:
            print("goldenglass-system: aviso: sin usuario que lo pida (sudo o pkexec), "
                  "no se copian ajustes de Plasma", file=sys.stderr)
            return
        greeter = pwd.getpwnam("plasmalogin")
        config = Path(greeter.pw_dir) / ".config"
        files = _as_user(user, lambda: _read_files(Path(user.pw_dir) / ".config"))
        if files.get("fontconfig/fonts.conf") is not None:
            fonts = _greeter_fonts_conf(files["fontconfig/fonts.conf"])
            if fonts is None:
                print("goldenglass-system: aviso: fonts.conf no es XML de fontconfig válido, "
                      "no se copia", file=sys.stderr)
                del files["fontconfig/fonts.conf"]
            else:
                files["fontconfig/fonts.conf"] = fonts
        previous = _as_user(greeter, lambda: _read_files(config))
        plm.setdefault("files", previous)
        _as_user(greeter, lambda: _write_files(config, files))
    else:
        raise SystemExit(f"goldenglass-system: gestor de inicio de sesión no admitido: {manager or 'ninguno'} "
                         "(solo SDDM y Plasma Login Manager)")


def disable_login(state: dict) -> None:
    saved = state.pop("login", {})
    if SDDM_CONF.is_file() and SDDM_CONF.read_text(errors="replace").startswith(SDDM_MARK):
        SDDM_CONF.unlink()
    plm = saved.get("plasmalogin")
    if plm and PLM_CONF.exists():
        import pwd
        if _plm_read("Image") == PLM_IMAGE:  # si lo cambió el administrador, se respeta
            for key, value in plm.get("conf", {}).items():
                _plm_write(key, value)
        if "files" in plm:
            greeter = pwd.getpwnam("plasmalogin")
            _as_user(greeter, lambda: _write_files(Path(greeter.pw_dir) / ".config", plm["files"]))


def run_system(actions: list[tuple[str, str, str]]) -> None:
    """Aplica (orden, parte, variante) como root, en ese orden."""
    os.umask(0o022)  # pkexec conserva el de quien llama
    state = load_state(ROOT_STATE)
    try:
        for command, part, variant in actions:
            if part == "plymouth":
                (enable_plymouth(variant, state) if command == "enable" else disable_plymouth(state))
            else:
                (enable_login(state) if command == "enable" else disable_login(state))
    finally:
        save_state(state, ROOT_STATE)


def escalate(argv: list[str]) -> int:
    """Vuelve a ejecutar la orden como root con pkexec (una sola autenticación)."""
    pkexec = shutil.which("pkexec")
    if not pkexec or not HELPER.exists():
        raise SystemExit("goldenglass-system: las partes del sistema necesitan root: "
                         f"sudo goldenglass-system {' '.join(argv)}")
    return subprocess.run([pkexec, str(HELPER), *argv]).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="goldenglass-system", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="muestra qué partes están activas")
    st.add_argument("parts", nargs="*", metavar="PARTE")
    st.add_argument("--json", action="store_true", help="salida JSON (la usa el módulo de Ajustes)")
    for name in ("enable", "disable"):
        p = sub.add_parser(name, help=f"{name} de las partes indicadas")
        p.add_argument("parts", nargs="+", metavar="PARTE")
        if name == "enable":
            p.add_argument("--variant", choices=list(PLYMOUTH_THEMES), default="dark",
                           help="tema de Plymouth: dark (negro, de fábrica) o light (gris claro)")
    ap_apply = sub.add_parser("apply", help="aplica varios cambios del sistema con una sola autenticación")
    ap_apply.add_argument("--plymouth", choices=[*PLYMOUTH_THEMES, "system"],
                          help="tema de arranque: dark, light o system (el de la distribución)")
    ap_apply.add_argument("--login", choices=["on", "off"], help="pantalla de inicio de sesión")
    args = ap.parse_args(argv)

    if args.command == "apply":
        actions = []
        if args.plymouth:
            actions.append(("disable", "plymouth", "dark") if args.plymouth == "system"
                           else ("enable", "plymouth", args.plymouth))
        if args.login:
            actions.append(("enable" if args.login == "on" else "disable", "login", "dark"))
        if not actions:
            ap.error("apply: indica --plymouth, --login o ambos")
        if os.geteuid() != 0:
            return escalate(["apply", *[f"--{k}={v}" for k, v in
                                        (("plymouth", args.plymouth), ("login", args.login)) if v]])
        run_system(actions)
        return 0

    known = [*PARTS, *SYSTEM_PARTS]
    unknown = [p for p in args.parts if p not in known]
    if unknown:
        ap.error(f"partes desconocidas: {', '.join(unknown)} (hay: {', '.join(known)})")

    if args.command == "status":
        status: dict = {}
        for part in args.parts or known:
            if part == "plymouth":
                status[part] = plymouth_status()
            elif part == "login":
                status[part] = login_status()
            else:
                status[part] = is_enabled(part)
        if args.json:
            print(json.dumps(status))
        else:
            for part, value in status.items():
                if part == "plymouth":
                    state = f"enabled ({value['variant']})" if value["enabled"] else f"disabled ({value['theme']})"
                    print(f"plymouth: {state}")
                    for code in value["warnings"]:
                        print(f"  aviso: {WARNING_TEXT[code]}")
                elif part == "login":
                    print(f"login: {'enabled' if value['enabled'] else 'disabled'} ({value['manager']})")
                    for code in value["warnings"]:
                        print(f"  aviso: {WARNING_TEXT[code]}")
                else:
                    print(f"{part}: {'enabled' if value else 'disabled'}")
        return 0

    user_parts = [p for p in args.parts if p in PARTS]
    system_parts = [p for p in args.parts if p in SYSTEM_PARTS]
    root = os.geteuid() == 0
    if user_parts and root:
        ap.error(f"{', '.join(user_parts)} es del usuario: ejecutar sin sudo")

    if user_parts:
        state = load_state()
        try:
            for part in user_parts:
                (enable if args.command == "enable" else disable)(part, state)
        finally:
            save_state(state)

    if system_parts:
        variant = getattr(args, "variant", "dark")
        if not root:
            return escalate([args.command, *system_parts,
                             *(["--variant", variant] if args.command == "enable" else [])])
        run_system([(args.command, part, variant) for part in system_parts])
    return 0


if __name__ == "__main__":
    sys.exit(main())
