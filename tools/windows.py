#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""goldenglass-windows: GoldenGlass window effects in KWin.

  goldenglass-windows --check                  # at login (autostart): factory values, once
  goldenglass-windows --reduce-motion on|off   # fades instead of zooms, slides and the genie
  goldenglass-windows --get-reduce-motion      # on | off

--check only acts while the global theme is GoldenGlass (org.goldenglass.*)
and only writes the kwinrc keys of FACTORY_DEFAULTS that the user left empty;
goldenglassrc [Windows] DefaultsVersion records that it ran, so an update
with a newer table only fills in what is new.

--reduce-motion writes goldenglassrc [Accessibility] ReduceMotion (the
plasmoids follow it through Motion.qml) and swaps KWin's moving effects for
fades. What it overwrote is kept in goldenglassrc [Windows] ReduceMotionSaved;
"off" puts it back, except the keys the user changed in the meantime.

Every change is applied live: /Effects loadEffect|unloadEffect|reconfigureEffect
and /KWin reconfigure.

Standard library only and without ggcommon: it ships in goldenglass-plasma,
while ggcommon.py belongs to goldenglass-kstyle. The factory values come from
the repository tokens or from the windows.json that gen_tokens writes and the
package installs in /usr/share/goldenglass/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_TOKENS = HERE.parent / "tokens" / "goldenglass.toml"
TOKENS_JSON = "windows.json"

RC = "goldenglassrc"
KWINRC = "kwinrc"
DEFAULTS_VERSION = 1
THEME_PREFIX = "org.goldenglass."

# KWin's ElectricBorder enum
ELECTRIC_TOP_LEFT = "7"
ELECTRIC_NONE = "9"

# effects of KWin's "minimize" exclusive category
MINIMIZE_EFFECTS = ("magiclamp", "squash")
REDUCE_MOTION_MINIMIZE = ("none", *MINIMIZE_EFFECTS)
# EnabledByDefault in the metadata of KWin 6.8.1: what an absent <effect>Enabled means
KWIN_ENABLED_BY_DEFAULT = {
    "scale": True, "fade": False, "slide": True, "fadedesktop": False, "magiclamp": False, "squash": True,
}
# kwinrc [Plugins] entries that are KWin scripts, not effects: /KWin reconfigure loads them
SCRIPTS = ("org.goldenglass.shortcuts",)

# kreadconfig6 cannot tell an absent key from its --default: this one never is a real value
ABSENT = "\x1fgoldenglass-absent"


# --- tokens -------------------------------------------------------------------

def _data_dirs() -> list[Path]:
    home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return [home, *map(Path, (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":"))]


def load_tokens() -> dict:
    """The repository tokens (development), else the installed windows.json."""
    if REPO_TOKENS.is_file():
        with REPO_TOKENS.open("rb") as f:
            return tomllib.load(f)
    for path in (*(d / "goldenglass" / TOKENS_JSON for d in _data_dirs()), HERE.parent / TOKENS_JSON):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise SystemExit(f"goldenglass-windows: neither {REPO_TOKENS} nor an installed {TOKENS_JSON} was found")


def write_json(tokens: dict, path: Path) -> Path:
    """The tokens this tool needs, for the installed copy (gen_tokens)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"kwin": tokens["kwin"], "accessibility": {"reduce_motion": tokens["accessibility"]["reduce_motion"]}}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


# --- configuration and KWin -------------------------------------------------------

def kread(file: str, group: str, key: str, default: str = "") -> str:
    r = subprocess.run(["kreadconfig6", "--file", file, "--group", group, "--key", key, "--default", default],
                       capture_output=True, text=True, check=True)
    return r.stdout.rstrip("\n")


def kwrite(file: str, group: str, key: str, value: str) -> None:
    subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--notify", value],
                   check=True)


def kdelete(file: str, group: str, key: str) -> None:
    subprocess.run(["kwriteconfig6", "--file", file, "--group", group, "--key", key, "--notify", "--delete"],
                   check=True)


def effects_call(method: str, *args: str) -> str:
    r = subprocess.run(["dbus-send", "--session", "--print-reply", "--dest=org.kde.KWin", "/Effects",
                        f"org.kde.kwin.Effects.{method}", *(f"string:{a}" for a in args)],
                       capture_output=True, text=True, check=False)
    return r.stdout if r.returncode == 0 else ""


def kwin_reconfigure() -> None:
    subprocess.run(["dbus-send", "--session", "--type=method_call", "--dest=org.kde.KWin", "/KWin",
                    "org.kde.KWin.reconfigure"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def read_optional(file: str, group: str, key: str) -> str | None:
    value = kread(file, group, key, ABSENT)
    return None if value == ABSENT else value


def is_true(value: str) -> bool:
    return value.strip().lower() in ("true", "1", "on", "yes")


def effect_enabled(effect: str) -> bool:
    value = read_optional(KWINRC, "Plugins", f"{effect}Enabled")
    if value is None or not value.strip():
        return KWIN_ENABLED_BY_DEFAULT.get(effect, False)
    return is_true(value)


def plugin_key(effect: str) -> str:
    return f"{effect}Enabled"


def effect_of(key: str) -> str | None:
    """The effect a kwinrc [Plugins] key enables, or None for scripts and other keys."""
    name = key.removesuffix("Enabled")
    return name if name != key and name not in SCRIPTS else None


@dataclass(frozen=True)
class Write:
    file: str
    group: str
    key: str
    value: str | None  # None deletes the key


def apply_live(writes: Iterable[Write]) -> None:
    """Loads and unloads the touched effects as kwinrc now says, then reconfigures KWin."""
    writes = list(writes)
    if not writes:
        return
    effects = sorted({e for w in writes if w.file == KWINRC and w.group == "Plugins" and (e := effect_of(w.key))})
    wanted = {effect: effect_enabled(effect) for effect in effects}
    # unload first: two effects of one exclusive category must never run together
    for effect in (e for e, on in wanted.items() if not on):
        effects_call("unloadEffect", effect)
    for effect in (e for e, on in wanted.items() if on):
        effects_call("loadEffect", effect)
    configured = sorted({w.group.removeprefix("Effect-") for w in writes
                         if w.file == KWINRC and w.group.startswith("Effect-")})
    for effect in configured:
        effects_call("reconfigureEffect", effect)
    kwin_reconfigure()


def write_all(writes: Iterable[Write]) -> list[Write]:
    done = []
    for w in writes:
        if w.value is None:
            kdelete(w.file, w.group, w.key)
        else:
            kwrite(w.file, w.group, w.key, w.value)
        done.append(w)
    return done


# --- factory values ---------------------------------------------------------------

@dataclass(frozen=True)
class Default:
    """kwinrc values GoldenGlass ships with.

    together: the keys are one choice (two effects of an exclusive category)
    and are only written if all of them are empty. Otherwise each key is
    written on its own if empty or if it still holds one of `stale`.
    """
    group: str
    values: dict[str, str]
    together: bool = False
    stale: tuple[str, ...] = ()


def _number(value: float) -> str:
    return f"{value:g}"


def factory_defaults(tokens: dict) -> list[Default]:
    kwin = tokens["kwin"]
    no_hot_corner = {key: ELECTRIC_NONE for key in ("BorderActivate", "BorderActivateAll", "BorderActivateClass")}
    return [
        Default("Plugins", {plugin_key("magiclamp"): "true", plugin_key("squash"): "false"}, together=True),
        Default("Plugins", {plugin_key("scale"): "true", plugin_key("fade"): "false"}, together=True),
        Default("Effect-scale", {"InScale": _number(kwin["open_scale"]), "OutScale": _number(kwin["close_scale"]),
                                 "Duration": str(kwin["window_anim_ms"])}),
        Default("Effect-overview", {"BorderActivate": ELECTRIC_NONE}, stale=(ELECTRIC_TOP_LEFT,)),
        Default("Effect-windowview", no_hot_corner, stale=(ELECTRIC_TOP_LEFT,)),
        Default("ElectricBorders", {"TopLeft": "None"}),
        Default("Plugins", {plugin_key("org.goldenglass.shortcuts"): "true"}),
    ]


def _empty(value: str | None) -> bool:
    return value is None or not value.strip()


def pending_defaults(defaults: Iterable[Default]) -> list[Write]:
    writes = []
    for default in defaults:
        current = {key: read_optional(KWINRC, default.group, key) for key in default.values}
        if default.together:
            if all(_empty(v) for v in current.values()):
                writes += [Write(KWINRC, default.group, k, v) for k, v in default.values.items()]
            continue
        writes += [Write(KWINRC, default.group, k, v) for k, v in default.values.items()
                   if _empty(current[k]) or current[k].strip() in default.stale]
    return writes


def goldenglass_theme_active() -> bool:
    return kread("kdeglobals", "KDE", "LookAndFeelPackage", "").startswith(THEME_PREFIX)


def defaults_version() -> int:
    try:
        return int(kread(RC, "Windows", "DefaultsVersion", "0") or 0)
    except ValueError:
        return 0


def check(tokens: dict) -> list[Write]:
    """Factory values for whatever the user left empty, once per DefaultsVersion."""
    if not goldenglass_theme_active() or defaults_version() >= DEFAULTS_VERSION:
        return []
    writes = write_all(pending_defaults(factory_defaults(tokens)))
    kwrite(RC, "Windows", "DefaultsVersion", str(DEFAULTS_VERSION))
    apply_live(writes)
    return writes


# --- Reduce Motion ----------------------------------------------------------------

def reduce_motion_plugins(tokens: dict) -> dict[str, str]:
    """kwinrc [Plugins] while Reduce Motion is on: fade instead of scale and slide, no genie."""
    minimize = tokens["kwin"]["reduce_motion_minimize"]
    values = {
        plugin_key("scale"): "false", plugin_key("fade"): "true",
        plugin_key("slide"): "false", plugin_key("fadedesktop"): "true",
    }
    values.update({plugin_key(e): "true" if e == minimize else "false" for e in MINIMIZE_EFFECTS})
    return values


def get_reduce_motion(tokens: dict) -> bool:
    default = "true" if tokens["accessibility"]["reduce_motion"] else "false"
    return is_true(kread(RC, "Accessibility", "ReduceMotion", default))


def _saved() -> dict[str, dict]:
    """{kwinrc [Plugins] key: {"before": value or None if absent, "set": value Reduce Motion wrote}}."""
    try:
        saved = json.loads(kread(RC, "Windows", "ReduceMotionSaved", "") or "{}")
    except json.JSONDecodeError:
        return {}
    return saved if isinstance(saved, dict) else {}


def set_reduce_motion(tokens: dict, on: bool) -> list[Write]:
    kwrite(RC, "Accessibility", "ReduceMotion", "true" if on else "false")
    saved = _saved()
    if on:
        writes = []
        for key, value in reduce_motion_plugins(tokens).items():
            # a second "on" keeps what was there before the first one
            saved.setdefault(key, {"before": read_optional(KWINRC, "Plugins", key), "set": value})
            saved[key]["set"] = value
            writes.append(Write(KWINRC, "Plugins", key, value))
        kwrite(RC, "Windows", "ReduceMotionSaved", json.dumps(saved, sort_keys=True))
    else:
        writes = [Write(KWINRC, "Plugins", key, entry.get("before")) for key, entry in sorted(saved.items())
                  if read_optional(KWINRC, "Plugins", key) == entry.get("set")]
        if saved:
            kdelete(RC, "Windows", "ReduceMotionSaved")
    written = write_all(writes)
    apply_live(written)
    return written


# --- command line -------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="goldenglass-windows", description="GoldenGlass window effects in KWin")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="at login: factory values for the keys the user left empty")
    group.add_argument("--reduce-motion", choices=["on", "off"], help="fades instead of zooms, slides and the genie")
    group.add_argument("--get-reduce-motion", action="store_true", help="on or off")
    args = ap.parse_args(argv)

    tokens = load_tokens()
    if args.get_reduce_motion:
        print("on" if get_reduce_motion(tokens) else "off")
    elif args.reduce_motion:
        set_reduce_motion(tokens, args.reduce_motion == "on")
    else:
        check(tokens)
    return 0


if __name__ == "__main__":
    sys.exit(main())
