#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-icon-style: the icon style of GoldenGlass (macOS 27 «Icon & widget style»).

  goldenglass-icon-style --style default|clear|tinted     # stores the choice and applies it
  goldenglass-icon-style --appearance light|dark|auto     # (both may go together)
  goldenglass-icon-style --apply                          # applies the stored choice
  goldenglass-icon-style --get                            # JSON for the «Estilo de iconos» module
  goldenglass-icon-style --watch                          # daemon, from the login autostart

The choice lives in goldenglassrc [Icons] Style and Appearance; resolve() turns
it and the colour scheme into one of the six GoldenGlass icon themes, which
plasma-changeicons applies. A styled theme needs the third-party icons that
goldenglass-wrap-icons writes per user: they are generated first if missing.

--watch keeps the choice when something else rewrites the icon theme: applying
a GoldenGlass global theme writes the default theme of its variant, and with
Appearance=auto a light/dark colour scheme change asks for the other variant.
It only corrects a theme of the GoldenGlass family (another theme chosen in
System Settings › Icons stays) and only once the user made a choice in the
module. If another tool keeps writing the theme back, the daemon stops
correcting for a minute instead of looping. When the palette changes it
announces it once more (see announce_palette()).

Every write (setters, --apply and each correction of --watch) takes an
exclusive flock in $XDG_RUNTIME_DIR/goldenglass-icon-style.lock: the module and
the daemon may apply at the same time. --get does not wait.

Standard library only (PyQt6 for the D-Bus signals of --watch) and without
ggcommon: it ships in goldenglass-icons next to icons_style.py.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from icons_style import Appearance, Style, family, resolve, theme_id

HERE = Path(__file__).resolve().parent
PROG = "goldenglass-icon-style"

RC = "goldenglassrc"
GROUP = "Icons"
STYLE_KEY = "Style"
APPEARANCE_KEY = "Appearance"
DEFAULT_STYLE = Style.DEFAULT
DEFAULT_APPEARANCE = Appearance.AUTO
# kdeglobals [Icons] Theme when the key is absent (KIconTheme::defaultThemeName)
KDE_DEFAULT_ICON_THEME = "breeze"

# kreadconfig6 cannot tell an absent key from its --default: this one never is a real value
ABSENT = "\x1fgoldenglass-absent"

# a colour scheme is dark when its window background is (Rec. 709 luma, as gtk_sync.py)
LUMA_WEIGHTS = (0.2126, 0.7152, 0.0722)
DARK_LUMA_BELOW = 128

# installed outside PATH by plasma-workspace
CHANGEICONS = "plasma-changeicons"
CHANGEICONS_LIBEXEC = ("/usr/lib/plasma-changeicons", "/usr/libexec/plasma-changeicons",
                       "/usr/lib/x86_64-linux-gnu/libexec/plasma-changeicons")
WRAP_ICONS = HERE / "wrap_icons.py"
WRAPPED_FOLDER = "wrapped"

# app icons the module previews each style with
PREVIEW_APPS = ("dolphin", "konsole", "systemsettings", "kate")

# --watch: a global theme or a colour scheme writes kdeglobals several times in a
# row; the daemon waits for the last write before it looks
SETTLE_MS = 500
# --watch: if another tool writes the theme back right after each correction,
# MAX_CORRECTIONS within CORRECTION_WINDOW_S stop the daemon for BACKOFF_S instead
# of looping. A person changes the global theme or the colour scheme far less often.
MAX_CORRECTIONS = 3
CORRECTION_WINDOW_S = 10.0
BACKOFF_S = 60.0
# KGlobalSettings::ChangeType::PaletteChanged, sent as notifyChange(type, 0)
PALETTE_CHANGED = 0
# kdeglobals keys that tell one palette from another: the accent (which
# plasma-apply-colorscheme --accent-color writes as DecorationFocus of every
# colour group), the selection and the window background
PALETTE_KEYS = (("Colors:View", "DecorationFocus"), ("Colors:Selection", "BackgroundNormal"),
                ("Colors:Window", "BackgroundNormal"))


# --- configuration --------------------------------------------------------------

def kread(file: str, group: str, key: str, default: str = "") -> str:
    r = subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key, "--default", default],
                       capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def kwrite(file: str, group: str, key: str, value: str) -> None:
    subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--notify", value],
                   check=True)


def read_optional(file: str, group: str, key: str) -> str | None:
    value = kread(file, group, key, ABSENT)
    return None if value == ABSENT else value


@dataclass(frozen=True)
class Choice:
    style: Style
    appearance: Appearance
    explicit: bool   # the user stored a style or an appearance; otherwise the factory values


def _parse(enum, value: str | None, default):
    try:
        return enum((value or "").strip().lower())
    except ValueError:
        return default


def read_choice() -> Choice:
    style = read_optional(RC, GROUP, STYLE_KEY)
    appearance = read_optional(RC, GROUP, APPEARANCE_KEY)
    return Choice(_parse(Style, style, DEFAULT_STYLE), _parse(Appearance, appearance, DEFAULT_APPEARANCE),
                  explicit=style is not None or appearance is not None)


def write_choice(style: Style | None, appearance: Appearance | None) -> None:
    if style is not None:
        kwrite(RC, GROUP, STYLE_KEY, style.value)
    if appearance is not None:
        kwrite(RC, GROUP, APPEARANCE_KEY, appearance.value)


def current_theme() -> str:
    return kread("kdeglobals", "Icons", "Theme", KDE_DEFAULT_ICON_THEME) or KDE_DEFAULT_ICON_THEME


def dark_scheme() -> bool:
    rgb = kread("kdeglobals", "Colors:Window", "BackgroundNormal").split(",")
    try:
        channels = [int(v) for v in rgb[:3]]
    except ValueError:
        return False
    if len(channels) != len(LUMA_WEIGHTS):
        return False
    return sum(w * c for w, c in zip(LUMA_WEIGHTS, channels, strict=True)) < DARK_LUMA_BELOW


def target_theme(choice: Choice) -> str:
    return resolve(choice.style, choice.appearance, dark_scheme())


# --- icon themes ------------------------------------------------------------------

def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


def icon_dirs() -> list[Path]:
    dirs = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    return [data_home() / "icons", *(Path(d) / "icons" for d in dirs if d)]


def theme_dir(theme: str) -> Path | None:
    return next((d / theme for d in icon_dirs() if (d / theme / "index.theme").is_file()), None)


def app_icon(theme: str, name: str) -> Path | None:
    return next((path for d in icon_dirs() if (path := d / theme / "apps" / "scalable" / f"{name}.svg").is_file()),
                None)


def needs_wrapped_icons(theme: str) -> bool:
    """A styled theme without the third-party icons of this user (goldenglass-wrap-icons writes them)."""
    styled = theme in family() and theme not in (theme_id(Style.DEFAULT, dark) for dark in (False, True))
    return styled and not (data_home() / "icons" / theme / WRAPPED_FOLDER).is_dir()


def wrap_icons() -> None:
    r = subprocess.run([sys.executable, str(WRAP_ICONS), "--if-changed"], capture_output=True, text=True,
                       check=False)
    if r.returncode != 0:
        # the styled theme still works: third-party apps keep their parent theme's wrapped icon
        print(f"{PROG}: goldenglass-wrap-icons failed: {r.stderr.strip() or r.returncode}", file=sys.stderr)


def changeicons_program() -> str:
    found = shutil.which(CHANGEICONS) or next((p for p in CHANGEICONS_LIBEXEC if os.access(p, os.X_OK)), None)
    if not found:
        raise SystemExit(f"{PROG}: {CHANGEICONS} was not found (plasma-workspace)")
    return found


def change_icons(theme: str) -> None:
    if theme_dir(theme) is None:
        raise SystemExit(f"{PROG}: the icon theme {theme} is not installed (goldenglass-icons)")
    if needs_wrapped_icons(theme):
        wrap_icons()
    subprocess.run([changeicons_program(), theme], check=True, stdout=subprocess.DEVNULL)


def apply(choice: Choice | None = None) -> str | None:
    """Switches to the theme of the stored choice; the theme it set, or None if it was already in use."""
    theme = target_theme(choice or read_choice())
    if current_theme() == theme:
        return None
    change_icons(theme)
    return theme


# --- module -------------------------------------------------------------------------

def state() -> dict:
    choice = read_choice()
    dark = dark_scheme()
    effective_dark = choice.appearance is Appearance.DARK or (choice.appearance is Appearance.AUTO and dark)
    previews = {}
    for style in Style:
        theme = resolve(style, Appearance.DARK if effective_dark else Appearance.LIGHT, dark)
        previews[style.value] = [str(path) for name in PREVIEW_APPS if (path := app_icon(theme, name))]
    theme = current_theme()
    return {
        "style": choice.style.value,
        "appearance": choice.appearance.value,
        "explicit": choice.explicit,
        "defaultStyle": DEFAULT_STYLE.value,
        "defaultAppearance": DEFAULT_APPEARANCE.value,
        "darkScheme": dark,
        "theme": theme,
        "inFamily": theme in family(),
        "resolved": resolve(choice.style, choice.appearance, dark),
        "previews": previews,
    }


# --- concurrency ------------------------------------------------------------------

def lock_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime and os.path.isdir(runtime):
        return Path(runtime) / "goldenglass-icon-style.lock"
    return Path(tempfile.gettempdir()) / f"goldenglass-icon-style-{os.getuid()}.lock"


@contextlib.contextmanager
def session_lock():
    """Exclusive flock around every write, as goldenglass-glass.

    The file is never removed (two processes could then hold locks on two
    different files); the kernel releases the lock if the process dies. If it
    cannot be opened safely, the write goes on without it.
    """
    path = lock_path()
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    except OSError as e:
        print(f"{PROG}: no lock ({path}: {e.strerror})", file=sys.stderr)
        fd = -1
    if fd >= 0 and os.fstat(fd).st_uid != os.getuid():
        os.close(fd)
        print(f"{PROG}: no lock ({path} belongs to another user)", file=sys.stderr)
        fd = -1
    try:
        if fd >= 0:
            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if fd >= 0:
            os.close(fd)


# --- daemon -------------------------------------------------------------------------

class Corrector:
    """What --watch does each time kdeglobals or the icon theme settle."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._recent: deque[float] = deque()
        self._backoff_until = float("-inf")
        self._palette: tuple[str, ...] | None = None

    def _allowed(self, current: str, theme: str) -> bool:
        now = self._clock()
        if now < self._backoff_until:
            return False
        while self._recent and now - self._recent[0] > CORRECTION_WINDOW_S:
            self._recent.popleft()
        if len(self._recent) < MAX_CORRECTIONS:
            return True
        self._recent.clear()
        self._backoff_until = now + BACKOFF_S
        print(f"{PROG}: the icon theme keeps changing to {current}; not correcting it to {theme} "
              f"for {BACKOFF_S:g} s", file=sys.stderr)
        return False

    def reconcile(self) -> str | None:
        """Puts back the chosen theme over another GoldenGlass one; the theme it set, if any."""
        choice = read_choice()
        if not choice.explicit:
            return None
        current = current_theme()
        if current not in family():
            return None
        theme = target_theme(choice)
        if current == theme or not self._allowed(current, theme):
            return None
        self._recent.append(self._clock())
        change_icons(theme)
        return theme

    def palette_changed(self) -> bool:
        """The palette differs from the one of the previous call (the first call only remembers it)."""
        palette = tuple(kread("kdeglobals", group, key) for group, key in PALETTE_KEYS)
        changed = self._palette is not None and palette != self._palette
        self._palette = palette
        return changed


def announce_palette() -> None:
    """notifyChange(PaletteChanged) again, now that kdeglobals holds the new palette.

    plasma-apply-colorscheme --accent-color announces the change before
    kdeglobals has it, so every app keeps the previous palette, and the Tinted
    icons the previous accent, until the next change (SP-10a, SP-10e). The
    daemon hears its own announcement, but the palette it remembers is already
    this one.
    """
    subprocess.run(["dbus-send", "--session", "--type=signal", "/KGlobalSettings",
                    "org.kde.KGlobalSettings.notifyChange", f"int32:{PALETTE_CHANGED}", "int32:0"], check=False)


def watch() -> int:
    from PyQt6.QtCore import QCoreApplication, QObject, QTimer, pyqtSlot
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage

    app = QCoreApplication(sys.argv[:1])
    corrector = Corrector()
    corrector.palette_changed()

    def settle() -> None:
        try:
            if corrector.palette_changed():
                announce_palette()
            with session_lock():
                theme = corrector.reconcile()
        except (subprocess.SubprocessError, OSError, SystemExit) as exc:
            # a failed correction must not end the daemon: the next change tries again
            print(f"{PROG}: could not correct the icon theme: {exc}", file=sys.stderr)
            return
        if theme:
            print(f"{PROG}: icon theme set to {theme}", file=sys.stderr)

    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(SETTLE_MS)
    timer.timeout.connect(settle)

    class Listener(QObject):
        @pyqtSlot(QDBusMessage)
        def changed(self, _msg: QDBusMessage) -> None:
            timer.start()

    listener = Listener()
    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        print(f"{PROG}: no session bus", file=sys.stderr)
        return 1
    # kdeglobals writes with notification (colour scheme, global theme), the
    # icon theme switch of KIconLoader and KGlobalSettings' palette and icon changes
    for path, interface, member in (("/kdeglobals", "org.kde.kconfig.notify", "ConfigChanged"),
                                    ("/KIconLoader", "org.kde.KIconLoader", "iconChanged"),
                                    ("/KGlobalSettings", "org.kde.KGlobalSettings", "notifyChange")):
        bus.connect("", path, interface, member, listener.changed)
    timer.start()
    return app.exec()


# --- command line -------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog=PROG, description="Icon style of GoldenGlass")
    ap.add_argument("--style", choices=[s.value for s in Style], help="default, clear (Clear) or tinted (Tinted)")
    ap.add_argument("--appearance", choices=[a.value for a in Appearance],
                    help="light or dark icons; auto follows the colour scheme")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="applies the stored style and appearance")
    mode.add_argument("--get", action="store_true", help="the stored choice and the theme in use, as JSON")
    mode.add_argument("--watch", action="store_true",
                      help="keeps the chosen theme when a global theme or the colour scheme change it")
    args = ap.parse_args(argv)
    setting = args.style is not None or args.appearance is not None
    if setting and (args.get or args.watch):
        ap.error("--style and --appearance go alone or with --apply")
    if not setting and not (args.apply or args.get or args.watch):
        ap.error("one of --style, --appearance, --apply, --get or --watch is required")

    if args.get:
        print(json.dumps(state(), sort_keys=True))
        return 0
    if args.watch:
        return watch()
    with session_lock():
        if setting:
            write_choice(Style(args.style) if args.style else None,
                         Appearance(args.appearance) if args.appearance else None)
        apply()
    return 0


if __name__ == "__main__":
    sys.exit(main())
