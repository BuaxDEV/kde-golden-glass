# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""App icon styles of GoldenGlass (macOS 27 Appearance › «Icon & widget style»).

- DEFAULT: the app's own colours (GoldenGlass, GoldenGlass-Dark).
- TINTED: monochrome in the system accent (GoldenGlass-Tinted{,-Dark}).
- CLEAR: translucent glass with a white glyph (GoldenGlass-Clear{,-Dark}).

The styled themes carry only apps and inherit everything else from the default
theme of the same appearance. Their glyph is a luminance mask: white where the
glyph is, cut by the background details, fixed colours kept by their lightness.
The accent is the `ColorScheme-Accent` class, which KIconLoader replaces with
the current accent (FollowsColorScheme); the `<style>` colour is only the
fallback, so a fixed accent is a matter of rewriting that colour.

Pure data and naming, with no imports of the other icon modules: the installed
tools (goldenglass-wrap-icons, goldenglass-icon-style) load it on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

THEME_FAMILY = "GoldenGlass"
DARK_SUFFIX = "-Dark"
ACCENT_CLASS = "ColorScheme-Accent"
STYLE_JSON = "icon-style.json"   # [icon_style] for the installed tools; icons.build() writes it
XLINK_NS = "http://www.w3.org/1999/xlink"   # the root <svg> declares it when the body uses xlink:href

Pair = tuple[str, str]


class Style(Enum):
    DEFAULT = "default"
    CLEAR = "clear"
    TINTED = "tinted"


def theme_id(style: Style, dark: bool) -> str:
    """Icon theme folder of a style and appearance: GoldenGlass[-Clear|-Tinted][-Dark]."""
    style_suffix = "" if style is Style.DEFAULT else f"-{style.value.capitalize()}"
    return f"{THEME_FAMILY}{style_suffix}{DARK_SUFFIX if dark else ''}"


def theme_name(style: Style, dark: bool) -> str:
    """Name= of the theme: «GoldenGlass Tinted Dark»."""
    return theme_id(style, dark).replace("-", " ")


@dataclass(frozen=True)
class TintedTokens:
    """[icon_style.tinted]: graphite (dark) or accent-washed (light) tile, glyph in the accent."""

    dark_background: Pair
    dark_wash_alpha: float
    light_background: Pair
    light_wash_alpha: float
    light_glyph_shade: float
    glyph_floor: float


@dataclass(frozen=True)
class ClearTokens:
    """[icon_style.clear]: translucent tile, pronounced rim and specular, white glyph."""

    light_fill: str
    light_fill_alpha: float
    dark_fill: str
    dark_fill_alpha: float
    glyph: str
    glyph_alpha: float
    glyph_floor: float
    glyph_shadow_blur: float
    glyph_shadow_alpha: float
    specular_alpha: float
    rim_width: float
    rim_top: float
    rim_mid: float
    rim_bottom: float


@dataclass(frozen=True)
class StyleTokens:
    tinted: TintedTokens
    clear: ClearTokens

    @classmethod
    def from_tokens(cls, tokens: dict) -> "StyleTokens":
        section = tokens["icon_style"]
        tinted = dict(section["tinted"])
        for key in ("dark_background", "light_background"):
            top, bottom = tinted[key]
            tinted[key] = (top, bottom)
        return cls(TintedTokens(**tinted), ClearTokens(**section["clear"]))

    def glyph_floor(self, style: Style) -> float:
        return {Style.TINTED: self.tinted.glyph_floor, Style.CLEAR: self.clear.glyph_floor}[style]
