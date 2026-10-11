# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema de iconos «GoldenGlass», dibujado por código.

Bloque base: carpetas, lugares y dispositivos.
  - Desde 32 px: carpetas de macOS 27 en el color de acento (dos capas con
    brillo y el símbolo grabado en el frente); papelera y unidades a color.
  - 16/22/24 px: solo el símbolo, en color de acento, como la barra lateral
    de Finder (y en las vistas de lista de Dolphin).
  - `*-symbolic`: el mismo símbolo en el color del texto.

Todo sigue al esquema de colores: el tema declara FollowsColorScheme y los SVG
usan las clases ColorScheme-Accent/-Text, que KIconLoader sustituye por los
colores actuales (también al seleccionar). Los colores dentro de <style> son
solo el valor de reserva (tokens del tema claro).

Salida:
  build/icons/GoldenGlass/        tema claro (Inherits=WhiteSur,breeze,hicolor)
  build/icons/GoldenGlass-Dark/   mismas carpetas (enlaces), hereda las
                                  variantes oscuras (WhiteSur-dark,breeze-dark)

Uso directo para iterar el diseño:
  python3 tools/icons.py --preview build/icons-preview.png
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

THEMES = {
    "GoldenGlass": ("GoldenGlass", "WhiteSur,breeze,hicolor"),
    "GoldenGlass-Dark": ("GoldenGlass Dark", "WhiteSur-dark,breeze-dark,breeze,hicolor"),
}
SMALL = (16, 22, 24)
STROKE = 1.35  # grosor de los símbolos en la cuadrícula de 16


# --- símbolos (cuadrícula de 16, trazos en currentColor) ----------------------
# Cada símbolo es SVG sin pintura de trazo: el grupo que lo contiene pone
# stroke=currentColor. Las partes rellenas llevan fill="currentColor" stroke="none".

def _fill(el: str) -> str:
    return el.replace("/>", ' fill="currentColor" stroke="none"/>', 1)


GLYPHS: dict[str, str] = {
    "folder": ('<path d="M1.8 4.1 Q1.8 2.9 3 2.9 H6.1 L7.6 4.4 H13 Q14.2 4.4 14.2 5.6 V12.3 '
               'Q14.2 13.5 13 13.5 H3 Q1.8 13.5 1.8 12.3 Z"/><path d="M1.8 6.4 H14.2"/>'),
    "home": '<path d="M2.2 7.6 L8 2.6 L13.8 7.6"/><path d="M3.8 6.4 V13.6 H12.2 V6.4"/>'
            '<path d="M6.7 13.6 V10 H9.3 V13.6"/>',
    "desktop": '<rect x="1.6" y="2.4" width="12.8" height="8.6" rx="1.3"/><path d="M8 11 V13.8 M5.6 13.8 H10.4"/>',
    "documents": ('<path d="M3.8 1.9 H9.4 L12.4 4.9 V13.1 Q12.4 14.1 11.4 14.1 H4.8 Q3.8 14.1 3.8 13.1 Z"/>'
                  '<path d="M9.4 1.9 V4.9 H12.4"/><path d="M6.1 8.2 H10.1 M6.1 10.8 H10.1"/>'),
    "downloads": '<circle cx="8" cy="8" r="6.2"/><path d="M8 4.7 V11 M5.4 8.6 L8 11.2 L10.6 8.6"/>',
    "music": ('<path d="M6.3 12 V3.6 L13 2.2 V10.4"/>'
              + _fill('<ellipse cx="4.6" cy="12" rx="1.9" ry="1.6"/>')
              + _fill('<ellipse cx="11.3" cy="10.4" rx="1.9" ry="1.6"/>')),
    "pictures": ('<rect x="1.6" y="2.6" width="12.8" height="10.8" rx="1.6"/>'
                 '<path d="M2.2 12.2 L6 8.4 L9 11.2 L10.9 9.3 L13.8 12.2"/>'
                 + _fill('<circle cx="10.9" cy="5.8" r="1.25"/>')),
    "videos": ('<rect x="1.6" y="3" width="12.8" height="10" rx="1.6"/>'
               + _fill('<path d="M6.5 5.7 L10.9 8 L6.5 10.3 Z"/>')),
    "templates": '<rect x="3.4" y="1.9" width="9.2" height="12.2" rx="1.3" stroke-dasharray="2.1 1.5"/>'
                 '<path d="M6 7 H10 M6 9.6 H10"/>',
    "publicshare": ('<circle cx="6" cy="5" r="2.3"/><path d="M1.8 13.8 Q1.8 9.3 6 9.3 Q10.2 9.3 10.2 13.8"/>'
                    '<path d="M10.4 2.9 A2.1 2.1 0 1 1 10.9 7.1 M12 9.4 Q14.3 10.1 14.3 13.6"/>'),
    "network": ('<circle cx="8" cy="8" r="6.2"/><ellipse cx="8" cy="8" rx="2.6" ry="6.2"/>'
                '<path d="M1.9 8 H14.1"/>'),
    "drive": ('<rect x="1.6" y="4.6" width="12.8" height="7.6" rx="1.8"/><path d="M1.8 9.2 H14.2"/>'
              + _fill('<circle cx="11.9" cy="10.7" r=".75"/>')),
    "removable": ('<rect x="2.6" y="3.4" width="10.8" height="10.6" rx="1.8"/><path d="M5.6 3.4 V1.8 H10.4 V3.4"/>'
                  + _fill('<path d="M8 6 L10.3 8.9 H5.7 Z"/>') + '<path d="M5.8 11.2 H10.2"/>'),
    "optical": '<circle cx="8" cy="8" r="6.2"/><circle cx="8" cy="8" r="1.7"/><path d="M8 3.6 A4.4 4.4 0 0 1 12.4 8" stroke-opacity=".5"/>',
    "computer": '<rect x="2.6" y="3" width="10.8" height="7.6" rx="1.2"/><path d="M1.2 12.9 H14.8"/>',
    "recent": '<circle cx="8" cy="8" r="6.2"/><path d="M8 4.4 V8 L10.6 9.6"/>',
    "cloud": '<path d="M4.6 12.6 H11.6 A2.8 2.8 0 0 0 12.1 7 A4.1 4.1 0 0 0 4.3 6.4 A3.1 3.1 0 0 0 4.6 12.6 Z"/>',
    "trash": ('<path d="M2.4 4.1 H13.6 M6 4.1 V2.4 H10 V4.1"/><path d="M3.8 4.1 L4.6 13.2 Q4.7 14.1 5.6 14.1 '
              'H10.4 Q11.3 14.1 11.4 13.2 L12.2 4.1"/><path d="M6.6 6.6 V11.6 M9.4 6.6 V11.6"/>'),
    "favorites": '<path d="M8 1.9 L9.8 5.8 L14 6.2 L10.8 9 L11.8 13.2 L8 11 L4.2 13.2 L5.2 9 L2 6.2 L6.2 5.8 Z"/>',
    "folder-plus": ('<path d="M1.8 4.1 Q1.8 2.9 3 2.9 H6.1 L7.6 4.4 H13 Q14.2 4.4 14.2 5.6 V12.3 '
                    'Q14.2 13.5 13 13.5 H3 Q1.8 13.5 1.8 12.3 Z"/><path d="M8 6.8 V11.2 M5.8 9 H10.2"/>'),
    "applications": ('<rect x="2" y="2" width="5" height="5" rx="1.4"/><rect x="9" y="2" width="5" height="5" rx="1.4"/>'
                     '<rect x="2" y="9" width="5" height="5" rx="1.4"/><rect x="9" y="9" width="5" height="5" rx="1.4"/>'),
}


# --- iconos -------------------------------------------------------------------

@dataclass(frozen=True)
class Icon:
    names: tuple[str, ...]   # primer nombre: archivo real; resto: enlaces
    glyph: str               # símbolo (pequeño, simbólico y grabado en la carpeta)
    context: str             # places | devices
    large: str = "folder"    # cómo se dibuja desde 32 px: folder | trash | trash-full | drive | ...
    color: str | None = None  # color fijo en vez del acento (carpetas de color de Dolphin)


# Colores que Dolphin ofrece en «Asignar color a carpeta» (colores de macOS).
FOLDER_COLORS = {
    "red": "#FF3B30", "orange": "#FF9500", "yellow": "#FFCC00", "green": "#34C759",
    "cyan": "#32ADE6", "blue": "#007AFF", "violet": "#AF52DE", "magenta": "#FF2D55",
    "brown": "#A2845E", "grey": "#8E8E93", "black": "#3A3A3C",
}

ICONS: tuple[Icon, ...] = (
    Icon(("folder", "inode-directory"), "folder", "places", "folder-plain"),
    # Acciones: sin ellas, KDE recortaría «folder-new» hasta «folder» en este
    # tema antes de mirar los heredados y se perdería el «+».
    Icon(("folder-new", "folder-add"), "folder-plus", "places", "folder"),
    Icon(("folder-open", "folder-blue-open"), "folder", "places", "folder-plain"),
    Icon(("user-home", "folder-home", "folder-blue-home"), "home", "places"),
    Icon(("user-desktop", "folder-desktop"), "desktop", "places"),
    Icon(("folder-documents", "folder-text", "folder-blue-documents"), "documents", "places"),
    Icon(("folder-download", "folder-downloads", "folder-blue-download"), "downloads", "places"),
    Icon(("folder-music", "folder-sound", "folder-blue-music"), "music", "places"),
    Icon(("folder-pictures", "folder-images", "folder-image", "folder-blue-pictures"), "pictures", "places"),
    Icon(("folder-videos", "folder-video", "folder-blue-videos"), "videos", "places"),
    Icon(("folder-templates", "folder-blue-templates"), "templates", "places"),
    Icon(("folder-publicshare", "folder-public", "folder-blue-public"), "publicshare", "places"),
    Icon(("folder-network", "folder-remote", "network-workgroup", "folder-blue-network"), "network", "places"),
    Icon(("folder-root",), "drive", "places"),
    Icon(("folder-cloud", "folder-blue-cloud"), "cloud", "places"),
    Icon(("folder-favorites", "folder-bookmark"), "favorites", "places"),
    Icon(("folder-recent", "folder-open-recent"), "recent", "places"),
    Icon(("folder-applications", "folder-appimage"), "applications", "places"),
    *(Icon((f"folder-{name}",), "folder", "places", "folder-plain", color)
      for name, color in FOLDER_COLORS.items()),
    Icon(("user-trash", "trash-empty"), "trash", "places", "trash"),
    Icon(("user-trash-full", "trash-full"), "trash", "places", "trash-full"),
    Icon(("drive-harddisk", "drive-harddisk-root", "drive-harddisk-solidstate", "drive-multidisk"),
         "drive", "devices", "drive"),
    Icon(("drive-removable-media", "drive-removable-media-usb", "drive-removable-media-usb-pendrive",
          "media-flash"), "removable", "devices", "removable"),
    Icon(("media-optical", "drive-optical", "media-optical-cd", "media-optical-dvd"), "optical", "devices", "optical"),
    Icon(("computer", "computer-laptop"), "computer", "devices", "computer"),
)


def _svg(size: int, body: str, fallback: dict[str, str], canvas: int | None = None) -> str:
    """Envuelve `body` (dibujado en un lienzo `canvas`, por defecto `size`)."""
    style = (f'.ColorScheme-Text{{color:{fallback["text"]};}}'
             f'.ColorScheme-Accent{{color:{fallback["accent"]};}}')
    c = canvas or size
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {c} {c}">'
            f'<defs><style type="text/css" id="current-color-scheme">{style}</style></defs>'
            f"{body}</svg>\n")


def small(icon: Icon, size: int, scheme: str) -> str:
    """Símbolo solo, centrado; a 22/24 se escala desde la cuadrícula de 16."""
    scale = {16: 1.0, 22: 1.25, 24: 1.375}[size]
    offset = (size - 16 * scale) / 2
    glyph, paint = GLYPHS[icon.glyph], f'class="{scheme}" stroke="currentColor"'
    if icon.color and scheme == "ColorScheme-Accent":
        glyph, paint = glyph.replace("currentColor", icon.color), f'stroke="{icon.color}"'
    return (f'<g {paint} fill="none" stroke-width="{STROKE}" '
            f'stroke-linecap="round" stroke-linejoin="round" '
            f'transform="translate({offset:g} {offset:g}) scale({scale:g})">{glyph}</g>')


# Carpeta de macOS 27 en un lienzo de 64. Las capas parten del acento
# (currentColor) y se aclaran con blanco translúcido.
FOLDER_BACK = ("M5 14.5 Q5 9.5 10 9.5 H22.6 Q25 9.5 26.7 11.2 L28.6 13.1 Q29.4 13.9 30.6 13.9 "
               "H54 Q59 13.9 59 18.9 V48 Q59 53 54 53 H10 Q5 53 5 48 Z")
FOLDER_FRONT = "M5 25 Q5 20.4 9.6 20.4 H54.4 Q59 20.4 59 25 V49.4 Q59 54 54.4 54 H9.6 Q5 54 5 49.4 Z"


def folder(glyph: str | None, color: str | None = None) -> str:
    """Carpeta en el acento, o en `color` fijo."""
    paint = f'fill="{color}"' if color else 'fill="currentColor" class="ColorScheme-Accent"'
    emboss = ""
    if glyph:
        s = 1.25
        body, ink = GLYPHS[glyph], 'stroke="currentColor" class="ColorScheme-Accent"'
        if color:
            body, ink = body.replace("currentColor", color), f'stroke="{color}"'
        emboss = (f'<g transform="translate({32 - 8 * s:g} {37.4 - 8 * s:g}) scale({s})" fill="none" '
                  f'{ink} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{body}</g>'
                  f'<g transform="translate({32 - 8 * s:g} {37.4 - 8 * s:g}) scale({s})" fill="none" '
                  f'stroke="#FFFFFF" stroke-opacity=".22" stroke-width="1.5" stroke-linecap="round" '
                  f'stroke-linejoin="round">{GLYPHS[glyph].replace("currentColor", "#FFFFFF")}</g>')
    return (
        '<defs><linearGradient id="front" x1="0" y1="20" x2="0" y2="54" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".62"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity=".46"/></linearGradient>'
        '<linearGradient id="back" x1="0" y1="9" x2="0" y2="30" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#FFFFFF" stop-opacity=".38"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity=".22"/></linearGradient></defs>'
        # sombra de contacto
        f'<path d="{FOLDER_FRONT}" transform="translate(0 1.2)" fill="#000000" fill-opacity=".14"/>'
        # pestaña y fondo
        f'<path d="{FOLDER_BACK}" {paint}/>'
        f'<path d="{FOLDER_BACK}" fill="url(#back)"/>'
        # papel asomando
        '<rect x="9" y="16.5" width="46" height="10" rx="2" fill="#FFFFFF" fill-opacity=".85"/>'
        # frente
        f'<path d="{FOLDER_FRONT}" {paint}/>'
        f'<path d="{FOLDER_FRONT}" fill="url(#front)"/>'
        # filo de luz superior
        '<path d="M9.6 21.1 H54.4" stroke="#FFFFFF" stroke-opacity=".7" stroke-width=".9" stroke-linecap="round"/>'
        + emboss
    )


def trash(full: bool) -> str:
    """Papelera de malla translúcida, como la del Dock de macOS."""
    papers = ""
    if full:
        papers = ('<path d="M17 16 L22 7 L31 11 L28 18 Z" fill="#FFFFFF" stroke="#C9CDD3" stroke-width=".8"/>'
                  '<path d="M27 15 L35 5.5 L45 10 L41 18 Z" fill="#F4F5F7" stroke="#C9CDD3" stroke-width=".8"/>'
                  '<path d="M38 17 L44 9 L50 14 L46 19 Z" fill="#FFFFFF" stroke="#C9CDD3" stroke-width=".8"/>')
    ribs = "".join(f'<path d="M{x:g} 22 L{x + (x - 32) * 0.08:g} 55"/>' for x in (21, 26.5, 32, 37.5, 43))
    return (
        '<defs><linearGradient id="can" x1="0" y1="16" x2="0" y2="60" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#F7F8FA"/><stop offset="1" stop-color="#D5D9DF"/></linearGradient></defs>'
        '<ellipse cx="32" cy="58.5" rx="17" ry="2.6" fill="#000000" fill-opacity=".12"/>'
        + papers +
        '<path d="M13.5 18 H50.5 L46.4 55.4 Q46 58.4 43 58.4 H21 Q18 58.4 17.6 55.4 Z" fill="url(#can)" '
        'stroke="#AEB4BC" stroke-width="1"/>'
        f'<g stroke="#9AA1AA" stroke-opacity=".55" stroke-width="1.6" stroke-linecap="round">{ribs}</g>'
        '<rect x="11" y="15" width="42" height="5.4" rx="2.7" fill="#F4F5F7" stroke="#AEB4BC" stroke-width="1"/>'
        '<path d="M14 16.4 H50" stroke="#FFFFFF" stroke-width="1" stroke-linecap="round"/>'
    )


def device(kind: str) -> str:
    """Unidades y equipo, plateados como en macOS."""
    defs = ('<defs><linearGradient id="metal" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#F2F3F5"/><stop offset="1" stop-color="#BFC4CB"/></linearGradient>'
            '<linearGradient id="dark" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#5A5F67"/><stop offset="1" stop-color="#2D3035"/></linearGradient></defs>')
    shadow = '<ellipse cx="32" cy="{y}" rx="{rx}" ry="2.4" fill="#000000" fill-opacity=".14"/>'
    if kind == "drive":
        return (defs + shadow.format(y=48.5, rx=26) +
                '<rect x="6" y="18" width="52" height="30" rx="6" fill="url(#metal)" stroke="#9EA4AC"/>'
                '<path d="M7 36 H57" stroke="#9EA4AC" stroke-opacity=".6"/>'
                '<path d="M11 19.6 H53" stroke="#FFFFFF" stroke-linecap="round"/>'
                '<circle cx="50.5" cy="42" r="1.8" fill="#34C759"/>')
    if kind == "removable":
        return (defs + shadow.format(y=56, rx=17) +
                '<rect x="20" y="6" width="24" height="12" rx="2" fill="#D9DCE0" stroke="#9EA4AC"/>'
                '<rect x="25" y="9.5" width="4.5" height="3.5" fill="#6B7079"/><rect x="34.5" y="9.5" width="4.5" '
                'height="3.5" fill="#6B7079"/>'
                '<rect x="15" y="16" width="34" height="40" rx="6" fill="url(#dark)" stroke="#202226"/>'
                '<path d="M20 18 H44" stroke="#FFFFFF" stroke-opacity=".3" stroke-linecap="round"/>'
                '<path d="M32 28 L37.5 35.5 H26.5 Z M26.5 39.5 H37.5" fill="#FFFFFF" fill-opacity=".85" '
                'stroke="#FFFFFF" stroke-opacity=".85" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>')
    if kind == "optical":
        return (defs + shadow.format(y=58, rx=22) +
                '<defs><linearGradient id="sheen" x1="0" y1="0" x2="1" y2="1">'
                '<stop offset="0" stop-color="#B9E3FF"/><stop offset=".3" stop-color="#F6F1FF"/>'
                '<stop offset=".5" stop-color="#FFE3B8"/><stop offset=".7" stop-color="#D8F7E1"/>'
                '<stop offset="1" stop-color="#C9CCFF"/></linearGradient></defs>'
                '<circle cx="32" cy="32" r="25" fill="url(#sheen)" stroke="#A8AEB6"/>'
                '<circle cx="32" cy="32" r="9" fill="#E9EBEE" stroke="#A8AEB6"/>'
                '<circle cx="32" cy="32" r="3.6" fill="#FFFFFF" stroke="#A8AEB6"/>')
    if kind == "computer":
        return (defs + shadow.format(y=56.5, rx=14) +
                '<path d="M26 44 H38 L40 55 H24 Z" fill="url(#metal)" stroke="#9EA4AC"/>'
                '<rect x="5" y="8" width="54" height="38" rx="4.5" fill="url(#metal)" stroke="#9EA4AC"/>'
                '<rect x="8" y="11" width="48" height="27" rx="1.5" fill="url(#dark)"/>'
                '<defs><linearGradient id="screen" x1="0" y1="0" x2="1" y2="1">'
                '<stop offset="0" stop-color="#5B5FA6"/><stop offset=".6" stop-color="#D9788A"/>'
                '<stop offset="1" stop-color="#F5A15C"/></linearGradient></defs>'
                '<rect x="9" y="12" width="46" height="25" rx="1" fill="url(#screen)"/>')
    raise ValueError(kind)


def large(icon: Icon) -> str:
    if icon.large == "folder":
        return folder(icon.glyph, icon.color)
    if icon.large == "folder-plain":
        return folder(None, icon.color)
    if icon.large in ("trash", "trash-full"):
        return trash(icon.large == "trash-full")
    return device(icon.large)


# --- paquete ------------------------------------------------------------------

def _directories(subdirs: set[str]) -> list[tuple[str, dict[str, str]]]:
    """Entradas de index.theme para las carpetas «contexto/tamaño» usadas."""
    dirs = []
    for d in sorted(subdirs, key=lambda d: (d.split("/")[0], d.split("/")[1].isdigit() is False, d)):
        ctx, sub = d.split("/")
        label = {"mimetypes": "MimeTypes", "apps": "Applications"}.get(ctx, ctx.capitalize())  # especificación
        if sub.isdigit():
            keys = {"Size": sub, "Type": "Fixed"}
        elif sub == "symbolic":
            keys = {"Size": "16", "MinSize": "8", "MaxSize": "512", "Type": "Scalable"}
        else:  # scalable: desde 32 si hay tamaños pequeños dibujados aparte
            has_small = any(o.startswith(f"{ctx}/") and o.split("/")[1].isdigit() for o in subdirs)
            keys = {"Size": "64", "MinSize": "32" if has_small else "8", "MaxSize": "512", "Type": "Scalable"}
        dirs.append((d, {**keys, "Context": label}))
    return dirs


def _index(name: str, inherits: str, dirs) -> str:
    lines = ["[Icon Theme]", f"Name={name}", "Comment=macOS-inspired icons for GoldenGlass",
             f"Inherits={inherits}", "FollowsColorScheme=true", "Example=folder",
             f"Directories={','.join(d for d, _ in dirs)}", ""]
    for d, keys in dirs:
        lines.append(f"[{d}]")
        lines += [f"{k}={v}" for k, v in keys.items()]
        lines.append("")
    return "\n".join(lines)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _link(target: str, link: Path) -> None:
    if not (link.exists() or link.is_symlink()):
        link.symlink_to(target)


def _family(tokens: dict) -> str:
    """Fuente real de las etiquetas: el alias del tema resuelto por fontconfig."""
    import subprocess
    try:
        return subprocess.run(["fc-match", "-f", "%{family[0]}", f"{tokens['font']['sans']}:bold"],
                              capture_output=True, text=True, check=True).stdout or "Inter"
    except (OSError, subprocess.CalledProcessError):
        return "Inter"


# --- protección contra el recorte de nombres -----------------------------------
# KIconLoader, dentro de cada tema y antes de pasar a los heredados, recorta el
# nombre que no encuentra («preferences-system-bluetooth» → «preferences-system»).
# Con nuestras apps eso se quedaría con iconos ajenos (categorías de
# Preferencias, iconos de bandeja «kdeconnect-tray», «klipper-symbolic»…). Para
# cada uno se añade un enlace al archivo del primer tema heredado que lo tiene,
# así el nombre exacto se encuentra aquí. Si ese tema desaparece, el enlace
# queda roto y KDE sigue buscando como siempre.

MEDIA_TYPES = {"text", "application", "image", "audio", "inode", "video", "message", "model", "multipart",
               "x-content", "x-epoc"}
# Al generar para un paquete del sistema (GOLDENGLASS_SYSTEM=1) solo cuentan los
# temas de /usr: los enlaces no pueden apuntar al /home de quien compila.
ICON_BASES = ((Path("/usr/share/icons"),) if os.environ.get("GOLDENGLASS_SYSTEM") else
              (Path.home() / ".local/share/icons", Path("/usr/local/share/icons"), Path("/usr/share/icons")))


def _resolves_to(name: str, ours: set[str]) -> str | None:
    """Nombre propio al que KIconLoader recortaría `name` dentro de este tema."""
    symbolic, generic, cur = name.endswith("-symbolic"), name.endswith("-x-generic"), name
    while cur:
        if cur in ours:
            return cur
        if generic:
            return None
        if symbolic:
            cur = cur[: -len("-symbolic")]
            if cur in ours:
                return cur
        i = cur.rfind("-")
        if i > 1:
            cur = cur[:i]
            if cur.endswith("-x"):
                cur = cur[:-2]
            if symbolic:
                cur += "-symbolic"
        elif cur in MEDIA_TYPES:
            cur, generic = cur + "-x-generic", True
        else:
            return None
    return None


def _theme_index(theme: str) -> dict[str, Path]:
    """nombre → mejor archivo (SVG escalable o el mayor) de un tema instalado."""
    best: dict[str, tuple[int, Path]] = {}
    for base in ICON_BASES:
        root = base / theme
        if not root.is_dir() or root.name.startswith("GoldenGlass"):
            continue
        for dirpath, _, filenames in os.walk(root, followlinks=True):
            parts = Path(dirpath).relative_to(root).parts
            size = next((int(p.split("@")[0].split("x")[0]) for p in parts if p.split("@")[0].split("x")[0].isdigit()), 0)
            for f in filenames:
                stem, ext = os.path.splitext(f)
                if ext not in (".svg", ".png"):
                    continue
                score = (2000 if "scalable" in parts or "symbolic" in parts else size) + (1000 if ext == ".svg" else 0)
                if stem not in best or score > best[stem][0]:
                    best[stem] = (score, Path(dirpath) / f)
        break  # el primero que tenga el tema gana, como en KDE
    return {k: v for k, (_, v) in best.items()}


def _guards(theme_root: Path, inherits: str, protect: set[str], ours: set[str], folder: str = "inherited") -> int:
    """Enlaces en <tema>/<folder>/ para los nombres heredados que se recortarían
    hasta uno de `protect`. Devuelve cuántos."""
    targets: dict[str, Path] = {}
    for theme in inherits.split(","):
        for name, path in _theme_index(theme).items():
            if name not in ours and name not in targets and _resolves_to(name, ours) in protect:
                targets[name] = path
    out = theme_root / folder
    out.mkdir(parents=True, exist_ok=True)
    for name, path in sorted(targets.items()):
        _link(str(path), out / f"{name}{path.suffix}")
    return len(targets)


def build(tokens: dict, out: Path) -> list[Path]:
    import icons_apps
    import icons_mime

    fallback = {"accent": tokens["light"]["accent"], "text": tokens["light"]["label"][:7]}
    base = out / "icons"
    for theme in THEMES:
        if (base / theme).exists():
            shutil.rmtree(base / theme)
    root = base / "GoldenGlass"

    # (ruta relativa, svg, alias) del tema claro; lo que no esté en el oscuro
    # se comparte por enlace (sigue al esquema de colores)
    entries: list[tuple[str, str, tuple[str, ...]]] = []
    dark_entries: list[tuple[str, str, tuple[str, ...]]] = []
    for icon in ICONS:
        main, aliases = icon.names[0], icon.names[1:]
        entries.append((f"{icon.context}/scalable/{main}.svg", _svg(64, large(icon), fallback), aliases))
        entries.append((f"{icon.context}/symbolic/{main}-symbolic.svg",
                        _svg(16, small(icon, 16, "ColorScheme-Text"), fallback), aliases))
        for size in SMALL:
            entries.append((f"{icon.context}/{size}/{main}.svg",
                            _svg(size, small(icon, size, "ColorScheme-Accent"), fallback), aliases))
    for rel, (canvas, body), aliases in icons_mime.files(_family(tokens)):
        size = int(rel.split("/")[1]) if rel.split("/")[1].isdigit() else canvas
        entries.append((rel, _svg(size, body, fallback, canvas), aliases))
    # Apps: dibujo distinto en claro y oscuro
    for theme, rel, body, aliases in icons_apps.files():
        (entries if theme == "GoldenGlass" else dark_entries).append((rel, _svg(64, body, fallback), aliases))

    for theme_root, items in ((root, entries), (base / "GoldenGlass-Dark", dark_entries)):
        for rel, text, aliases in items:
            path = theme_root / rel
            _write(path, text)
            for alias in aliases:
                suffix = "-symbolic.svg" if rel.endswith("-symbolic.svg") else ".svg"
                _link(path.name, path.parent / f"{alias}{suffix}")

    # Protección: solo para los nombres de apps (las carpetas y documentos que
    # absorben variantes, p. ej. «folder-android» → «folder», son deseables).
    app_names = {Path(rel).stem for rel, _, _ in entries if rel.startswith("apps/")}
    app_names |= {a for rel, _, aliases in entries if rel.startswith("apps/") for a in aliases}
    shared = {Path(rel).stem for rel, _, _ in entries if not rel.startswith("apps/")}
    shared |= {a for rel, _, aliases in entries if not rel.startswith("apps/") for a in aliases}
    for theme, (_, inherits) in THEMES.items():
        own = dark_entries if theme == "GoldenGlass-Dark" else entries
        ours = shared | {Path(rel).stem for rel, _, _ in own} | {a for _, _, aliases in own for a in aliases}
        _guards(base / theme, inherits, app_names, ours)

    subdirs = {rel.rsplit("/", 1)[0] for rel, _, _ in entries}
    for theme, (name, inherits) in THEMES.items():
        # «wrapped»: apps de terceros encerradas en squircle por wrap_icons.py
        # en el equipo del usuario (puede estar vacía o solo en ~/.local).
        extra = ({"inherited"} if (base / theme / "inherited").exists() else set()) | {"wrapped"}
        _write(base / theme / "index.theme", _index(name, inherits, _directories(subdirs) + [
            (d, {"Size": "64", "MinSize": "8", "MaxSize": "512", "Type": "Scalable", "Context": "Applications"})
            for d in sorted(extra)]))
    # El tema oscuro comparte los demás iconos (siguen al esquema de colores):
    # solo cambian las apps y la herencia.
    own = {rel.split("/")[0] for rel, _, _ in dark_entries}
    for ctx in sorted({rel.split("/")[0] for rel, _, _ in entries} - own):
        _link(f"../GoldenGlass/{ctx}", base / "GoldenGlass-Dark" / ctx)
    return [base / theme for theme in THEMES]


def preview(tokens: dict, path: Path, dark: bool = False) -> None:
    """Hoja con cada icono a 16, 24, 32, 64 y 128 px, con los colores de los tokens."""
    from PyQt6.QtCore import QByteArray, QRectF
    from PyQt6.QtGui import QColor, QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    sheets = []
    for variant in ("light", "dark"):
        pal = tokens[variant]
        colors = {"accent": pal["accent"], "text": pal["label"][:7]}
        sizes = (16, 24, 32, 64, 128)
        row_h, col_w = 140, 16 + 24 + 32 + 64 + 128 + 60
        cols = 4
        rows = -(-len(ICONS) // cols)
        img = QImage(cols * col_w, rows * row_h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(pal["window"]))
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i, icon in enumerate(ICONS):
            x = (i % cols) * col_w + 6
            y = (i // cols) * row_h + 6
            for size in sizes:
                if size in SMALL:
                    text = _svg(size, small(icon, size, "ColorScheme-Accent"), colors)
                else:
                    text = _svg(64, large(icon), colors)
                QSvgRenderer(QByteArray(text.encode())).render(p, QRectF(x, y + 128 - size, size, size))
                x += size + 10
        p.end()
        sheets.append(img)
    out = QImage(sheets[0].width(), sheets[0].height() * 2, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.drawImage(0, 0, sheets[0])
    p.drawImage(0, sheets[0].height(), sheets[1])
    p.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(path))


if __name__ == "__main__":
    import argparse
    import tomllib

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", type=Path, required=True, help="PNG con todos los iconos (claro arriba, oscuro abajo)")
    args = ap.parse_args()
    toks = tomllib.loads((Path(__file__).resolve().parent.parent / "tokens" / "goldenglass.toml").read_text())
    preview(toks, args.preview)
    print(args.preview)
