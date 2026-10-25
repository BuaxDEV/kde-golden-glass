# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema GTK «GoldenGlass» sobre adw-gtk3, desde los tokens.

  build/gtk/GoldenGlass/gtk-3.0/gtk.css       claro (GTK3); gtk-dark.css para
                                              apps que piden la variante oscura
  build/gtk/GoldenGlass-Dark/gtk-3.0/gtk.css  oscuro: tools/gtk_sync.py cambia
                                              entre los dos temas al cambiar el
                                              esquema de KDE (GTK3 en Wayland
                                              no sigue «prefer-dark» de
                                              settings.ini)
  …/gtk-4.0/                                  lo mismo para apps GTK4 sin
                                              libadwaita
  build/gtk/libadwaita.css                    apps libadwaita: no admiten
                                              temas; tools/gtk_sync.py lo copia
                                              a ~/.config/gtk-4.0/gtk.css (con
                                              claro y oscuro por media query)

Cada archivo importa el de adw-gtk3 (forma y widgets de libadwaita en GTK3) y
encima redefine la paleta con la de GoldenGlass, los radios de macOS y los
semáforos de las ventanas con decoración propia (CSD).
"""

from __future__ import annotations

import os
from pathlib import Path

from ggcommon import Color

THEME_ID = "GoldenGlass"
ADW_CANDIDATES = (Path.home() / ".local/share/themes", Path.home() / ".themes", Path("/usr/share/themes"))
HEADER = "/* Generado por tools/gen_tokens.py desde tokens/goldenglass.toml — NO EDITAR */\n"


def _adw_dir() -> Path:
    """adw-gtk3 instalado (con GOLDENGLASS_SYSTEM=1, siempre el de /usr)."""
    if os.environ.get("GOLDENGLASS_SYSTEM"):
        return Path("/usr/share/themes/adw-gtk3")
    for base in ADW_CANDIDATES:
        if (base / "adw-gtk3" / "gtk-3.0" / "gtk.css").exists():
            return base / "adw-gtk3"
    return Path("/usr/share/themes/adw-gtk3")


def _css_color(value: str) -> str:
    """#RRGGBB o #RRGGBBAA → color CSS de GTK."""
    c = Color.parse(value)
    if len(value.lstrip("#")) == 8:
        return f"rgba({c.r}, {c.g}, {c.b}, {c.a:.3f})"
    return c.hex()


def _palette(pal: dict) -> dict[str, str]:
    """Nombres de color de libadwaita/adw-gtk3 → valor."""
    c = {k: _css_color(v) for k, v in pal.items() if isinstance(v, str)}
    return {
        "accent_color": c["accent"], "accent_bg_color": c["accent"], "accent_fg_color": c["accent_fg"],
        "destructive_color": c["negative"], "destructive_bg_color": c["negative"], "destructive_fg_color": c["negative_fg"],
        "success_color": c["positive"], "success_bg_color": c["positive"], "success_fg_color": c["positive_fg"],
        "warning_color": c["neutral"], "warning_bg_color": c["neutral"], "warning_fg_color": c["neutral_fg"],
        "error_color": c["negative"], "error_bg_color": c["negative"], "error_fg_color": c["negative_fg"],
        "window_bg_color": c["window"], "window_fg_color": c["label"],
        "view_bg_color": c["view"], "view_fg_color": c["label"],
        "headerbar_bg_color": c["header"], "headerbar_fg_color": c["label"],
        "headerbar_border_color": c["separator"], "headerbar_backdrop_color": c["header_inactive"],
        "headerbar_shade_color": c["separator"], "headerbar_darker_shade_color": c["separator"],
        "sidebar_bg_color": c["sidebar"], "sidebar_fg_color": c["label"],
        "sidebar_backdrop_color": c["sidebar"], "sidebar_border_color": c["separator"],
        "sidebar_shade_color": c["separator"],
        "card_bg_color": c["view"], "card_fg_color": c["label"], "card_shade_color": c["separator"],
        "dialog_bg_color": c["window"], "dialog_fg_color": c["label"],
        "popover_bg_color": c["view"], "popover_fg_color": c["label"],
        "popover_shade_color": c["separator"],
        "thumbnail_bg_color": c["view"], "thumbnail_fg_color": c["label"],
        "shade_color": c["separator"], "scrollbar_outline_color": c["separator"],
        "theme_selected_bg_color": c["accent"], "theme_selected_fg_color": c["accent_fg"],
        "theme_unfocused_selected_bg_color": c["selection_inactive"],
        "theme_unfocused_selected_fg_color": c["label"],
    }


def _defines(colors: dict[str, str]) -> str:
    return "".join(f"@define-color {k} {v};\n" for k, v in colors.items())


def _variables(colors: dict[str, str], indent: str = "  ") -> str:
    """Las mismas como variables CSS de libadwaita ≥ 1.6 (--window-bg-color…)."""
    return "".join(f"{indent}--{k.replace('_', '-')}: {v};\n" for k, v in colors.items())


def _shape(tokens: dict, gtk4: bool, inactive: str = "@traffic_light_inactive") -> str:
    """Radios de macOS y semáforos en las ventanas CSD (`inactive`: color de
    los semáforos en ventanas sin foco)."""
    r, tl = tokens["radius"], tokens["traffic_lights"]
    d, gap = tl["diameter"], tl["gap"]
    controls = "windowcontrols > button" if gtk4 else "headerbar button.titlebutton, .titlebar button.titlebutton"
    lights = []
    for cls, key in (("close", "close"), ("minimize", "minimize"), ("maximize", "zoom")):
        sel = ", ".join(f"{s.strip()}.{cls}" for s in controls.split(","))
        glyph_sel = ", ".join(f"{x.strip()} image" for x in sel.split(","))
        lights.append(
            f"{sel} {{ background-color: {tl[key]}; "
            f"box-shadow: inset 0 0 0 0.5px {tl[key + '_border']}, 0 0.5px 1px rgba(0, 0, 0, {tl['gtk_shadow_alpha']}); }}\n"
            f"{glyph_sel} {{ color: {tl[key + '_glyph']}; }}\n")
    backdrop = ", ".join(f"{s.strip()}:backdrop" for s in controls.split(","))
    hover_img = ", ".join(f"{s.strip()}:hover image" for s in controls.split(","))
    all_img = ", ".join(f"{s.strip()} image" for s in controls.split(","))
    # Ventanas sin foco: en color (token inactive_colored) o en gris como macOS
    backdrop_rule = "" if tl["inactive_colored"] else (
        f"{backdrop} {{ background-color: {inactive}; background-image: none; "
        f"box-shadow: inset 0 0 0 0.5px rgba(0, 0, 0, {tl['gtk_inactive_border_alpha']}); }}\n")
    return f"""
/* Forma de macOS */
button, combobox button, dropdown > button, spinbutton {{ border-radius: {r['control']}px; }}
entry, spinbutton, searchbar entry {{ border-radius: {r['control']}px; }}
checkbutton check, check {{ border-radius: {r['control_small']}px; }}
menu, .menu, .context-menu {{ border-radius: {r['menu']}px; }}
popover > contents, popover.background > contents, popover.menu > contents {{ border-radius: {r['menu']}px; }}
tooltip, tooltip.background {{ border-radius: {r['tooltip']}px; }}
{"window.csd, window.csd > .titlebar" if gtk4 else "window.csd decoration"} {{ border-radius: {r['window']}px; }}
.titlebar, headerbar {{ border-top-left-radius: {r['window']}px; border-top-right-radius: {r['window']}px; }}
window.maximized .titlebar, window.maximized headerbar, window.tiled headerbar {{ border-radius: 0; }}

/* Semáforos (ventanas con decoración propia) */
{controls} {{
  min-width: {d}px; min-height: {d}px; padding: 0; margin: 0 {gap / 2:g}px;
  border-radius: 9999px; border: none;
  /* vidrio de macOS 27: brillo arriba y brillo abajo */
  background-image: linear-gradient(to bottom, rgba(255, 255, 255, {tl['gtk_highlight_top']}), rgba(255, 255, 255, 0) 48%),
                    radial-gradient(ellipse at 50% 100%, rgba(255, 255, 255, {tl['gtk_highlight_bottom']}), rgba(255, 255, 255, 0) 60%);
}}
{"".join(lights)}{backdrop_rule}
{all_img} {{ opacity: 0; -gtk-icon-transform: scale({tl['gtk_glyph_scale']}); }}
{hover_img} {{ opacity: 1; }}
"""


def _variant_css(tokens: dict, variant: str, gtk: str) -> str:
    adw = _adw_dir()
    source = adw / gtk / ("gtk-dark.css" if variant == "dark" else "gtk.css")
    colors = _palette(tokens[variant])
    extra = f"@define-color traffic_light_inactive {_css_color(tokens[variant]['traffic_light_inactive'])};\n"
    return (HEADER + f'@import url("file://{source}");\n\n' + _defines(colors) + extra
            + _shape(tokens, gtk4=gtk == "gtk-4.0"))


def libadwaita_css(tokens: dict) -> str:
    """CSS de usuario para libadwaita: claro y oscuro con media query."""
    light, dark = _palette(tokens["light"]), _palette(tokens["dark"])
    # El acento lo da el sistema (portal de KDE); no se fuerza aquí.
    for pal in (light, dark):
        for k in ("accent_color", "accent_bg_color", "accent_fg_color"):
            pal.pop(k)
    shape = _shape(tokens, gtk4=True, inactive="var(--gg-traffic-inactive)")
    return (HEADER.replace("NO EDITAR", "lo gestiona goldenglass-gtk-sync; borrar esta línea para que no lo toque")
            + ":root {\n" + _variables(light)
            + f"  --gg-traffic-inactive: {_css_color(tokens['light']['traffic_light_inactive'])};\n}}\n"
            + "@media (prefers-color-scheme: dark) {\n  :root {\n" + _variables(dark, "    ")
            + f"    --gg-traffic-inactive: {_css_color(tokens['dark']['traffic_light_inactive'])};\n  }}\n}}\n"
            + shape)


def build(tokens: dict, out: Path) -> list[Path]:
    written = []
    files = {out / "gtk" / "libadwaita.css": libadwaita_css(tokens)}
    for theme, variants in ((THEME_ID, ("light", "dark")), (f"{THEME_ID}-Dark", ("dark", "dark"))):
        root = out / "gtk" / theme
        name = theme.replace("-", " ")
        files[root / "index.theme"] = (
            f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={name}\n"
            "Comment=macOS-inspired GTK theme for GoldenGlass (based on adw-gtk3)\n"
            f"Encoding=UTF-8\n\n[X-GNOME-Metatheme]\nGtkTheme={theme}\n")
        for gtk in ("gtk-3.0", "gtk-4.0"):
            files[root / gtk / "gtk.css"] = _variant_css(tokens, variants[0], gtk)
            files[root / gtk / "gtk-dark.css"] = _variant_css(tokens, variants[1], gtk)
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
