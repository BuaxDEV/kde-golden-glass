#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-gtk-sync: aplica el tema GTK de GoldenGlass mientras el Global
Theme de Plasma sea GoldenGlass (el Global Theme no puede fijar GTK).

  - GTK3 y GTK4 sin libadwaita: pone «GoldenGlass» o «GoldenGlass-Dark» según
    el esquema de colores de KDE, con la API de kde-gtk-config
    (org.kde.GtkConfig). En Wayland GTK3 no sigue «prefer-dark» de
    settings.ini, así que se cambia el tema entero, como Breeze/Breeze-Dark.
  - libadwaita: copia los colores y la forma a ~/.config/gtk-4.0/gtk.css (con
    claro y oscuro por media query), solo si no existe o ya es nuestro.
  - Al cambiar a otro Global Theme, deja GTK como estaba.

Se queda escuchando los cambios de kdeglobals (señal de KConfig por D-Bus);
con --once solo comprueba una vez y con --restore deshace lo aplicado (al
desinstalar). Lo arranca el autostart de la sesión.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

THEME = "GoldenGlass"
THEMES = (THEME, f"{THEME}-Dark")
FALLBACK = "Breeze"
MARKER = "lo gestiona goldenglass-gtk-sync"  # primera línea del CSS que instalamos

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DATA_DIRS = [Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")),
             *map(Path, os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":"))]


def _read(file: str, group: str, key: str) -> str:
    try:
        return subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key],
                              capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        return ""


def _write(file: str, group: str, key: str, value: str) -> None:
    subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, value], check=False)


def _dark() -> bool:
    """Esquema oscuro: fondo de ventana con luminancia baja."""
    rgb = _read("kdeglobals", "Colors:Window", "BackgroundNormal").split(",")
    try:
        r, g, b = (int(v) for v in rgb[:3])
    except ValueError:
        return False
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 128


def _gtk_config():
    from PyQt6.QtDBus import QDBusConnection, QDBusInterface
    iface = QDBusInterface("org.kde.kded6", "/modules/gtkconfig", "org.kde.GtkConfig", QDBusConnection.sessionBus())
    return iface if iface.isValid() else None


def _libadwaita_source() -> Path | None:
    for base in DATA_DIRS:
        path = base / "goldenglass" / "gtk" / "libadwaita.css"
        if path.is_file():
            return path
    return None


def _ours(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as f:
            return MARKER in f.readline()
    except OSError:
        return False


def sync(restore: bool = False) -> None:
    active = not restore and _read("kdeglobals", "KDE", "LookAndFeelPackage").startswith("org.goldenglass.")
    gtk = _gtk_config()
    current = str(gtk.call("gtkTheme").arguments()[0]) if gtk else ""
    user_css = CONFIG / "gtk-4.0" / "gtk.css"

    if active:
        wanted = THEMES[1] if _dark() else THEMES[0]
        if gtk and current != wanted:
            if current not in THEMES:
                _write("goldenglassrc", "Gtk", "PreviousTheme", current or FALLBACK)
            gtk.call("setGtkTheme", wanted)
        source = _libadwaita_source()
        if source and (not user_css.exists() or _ours(user_css)):
            user_css.parent.mkdir(parents=True, exist_ok=True)
            user_css.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        elif source:
            print(f"goldenglass-gtk-sync: {user_css} es de otra herramienta; no se toca", file=sys.stderr)
    else:
        if gtk and current in THEMES:
            gtk.call("setGtkTheme", _read("goldenglassrc", "Gtk", "PreviousTheme") or FALLBACK)
        if _ours(user_css):
            user_css.unlink()


def main() -> int:
    from PyQt6.QtCore import QCoreApplication, QObject, pyqtSlot
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage

    app = QCoreApplication(sys.argv)
    sync(restore="--restore" in sys.argv)
    if "--once" in sys.argv or "--restore" in sys.argv:
        return 0

    class Watcher(QObject):
        @pyqtSlot(QDBusMessage)
        def changed(self, _msg: QDBusMessage) -> None:
            sync()

    watcher = Watcher()
    # KConfig avisa de cada escritura con notificación en /<archivo>
    QDBusConnection.sessionBus().connect("", "/kdeglobals", "org.kde.kconfig.notify", "ConfigChanged",
                                         watcher.changed)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
