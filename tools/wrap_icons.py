#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Encierra en un squircle de GoldenGlass los iconos de las apps que el tema no
dibuja (Chrome, VS Code, Steam y sus juegos…), como hace macOS 26/27 con los
iconos que no siguen su forma.

Se ejecuta en el equipo del usuario, porque parte de los iconos que hay
instalados: para cada app visible (archivos .desktop del sistema, del usuario
y de Flatpak) toma el icono original de la app (hicolor o pixmaps, no la
versión de otro tema) y lo compone sobre el squircle claro y el oscuro:
  - si el original ya es un cuadrado lleno, se recorta al squircle;
  - si no, va centrado al 68 % sobre el squircle de vidrio.
El resultado va a ~/.local/share/icons/<tema>/wrapped/, carpeta que los temas
GoldenGlass declaran siempre (también vale con el tema instalado en /usr).

The Tinted and Clear themes get the same apps as a glyph on their own tile:
icons_glyph.py extracts it from the original icon, or falls back to its
silhouette or a monogram; an app it skips keeps the parent theme's wrapped icon.

Uso:
  goldenglass-wrap-icons            (o python3 tools/wrap_icons.py)
  goldenglass-wrap-icons --list     solo enseña qué haría
  goldenglass-wrap-icons --clean    borra los iconos encerrados
  goldenglass-wrap-icons --if-changed   solo si cambiaron las apps (autostart)
  goldenglass-wrap-icons --sheet hoja.png   hoja de revisión de Tintado y Transparente, sin escribir temas

Las apps con Icon= como ruta absoluta no se pueden sustituir desde un tema y
se dejan como están. Al instalar apps nuevas, volver a ejecutarlo.
"""

from __future__ import annotations

import argparse
import base64
import configparser
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import icons  # noqa: E402
import icons_apps  # noqa: E402
import icons_glyph  # noqa: E402
from icons_style import ACCENT_CLASS, XLINK_NS, Style  # noqa: E402

THEMES = {spec.id: spec for spec in icons.THEME_SPECS}
RENDER = 256          # resolución del PNG incrustado
INSET = 0.68          # tamaño del icono dentro del squircle (lado del squircle = 52)
FULL_BLEED = 0.80     # cobertura opaca a partir de la cual el icono ya es un «tile»


def _data_dirs() -> list[Path]:
    home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    dirs = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    extra = [Path.home() / ".local/share/flatpak/exports/share", Path("/var/lib/flatpak/exports/share")]
    out = []
    for d in [home, *map(Path, dirs), *extra]:
        if d not in out and d.is_dir():
            out.append(d)
    return out


def _apps() -> dict[str, str]:
    """Icon= → nombre de la app, de los .desktop visibles (el primero gana)."""
    found: dict[str, str] = {}
    seen: set[str] = set()
    for base in _data_dirs():
        apps = base / "applications"
        if not apps.is_dir():
            continue
        for desktop in sorted(apps.rglob("*.desktop")):
            rel = str(desktop.relative_to(apps))
            if rel in seen:  # el de XDG_DATA_HOME tapa al del sistema
                continue
            seen.add(rel)
            cp = configparser.RawConfigParser(strict=False, interpolation=None)
            try:
                cp.read(desktop, encoding="utf-8")
                entry = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if entry.get("Type") != "Application" or entry.get("NoDisplay") == "true" or entry.get("Hidden") == "true":
                continue
            icon = entry.get("Icon", "").strip()
            if icon and not icon.startswith("/"):
                found.setdefault(icon, entry.get("Name", icon))
    return found


def _original(name: str) -> Path | None:
    """Icono propio de la app: hicolor (escalable o el mayor) y luego pixmaps."""
    best: tuple[int, Path] | None = None
    for base in _data_dirs():
        root = base / "icons" / "hicolor"
        if root.is_dir():
            for path in root.glob(f"*/apps/{name}.*"):
                if path.suffix not in (".svg", ".png"):
                    continue
                size_dir = path.parent.parent.name
                score = 10000 if size_dir == "scalable" else int(size_dir.split("x")[0]) if size_dir[0].isdigit() else 0
                if best is None or score > best[0]:
                    best = (score, path)
        if best is None:
            for ext in (".svg", ".png"):
                pix = base / "pixmaps" / f"{name}{ext}"
                if pix.is_file():
                    best = (0, pix)
                    break
    return best[1] if best else None


def _squircle_path(scale: float):
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPainterPath
    import math
    path = QPainterPath()
    n, r, steps = 5.0, 26 * scale, 96
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        pt = QPointF(32 * scale + r * math.copysign(abs(c) ** (2 / n), c),
                     32 * scale + r * math.copysign(abs(s) ** (2 / n), s))
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    return path


def _render(path: Path):
    """Original a RENDER×RENDER (ARGB), o None si no se puede leer."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    img = QImage(RENDER, RENDER, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    if path.suffix == ".svg":
        renderer = QSvgRenderer(str(path))
        if not renderer.isValid():
            return None
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p, QRectF(0, 0, RENDER, RENDER))
        p.end()
    else:
        src = QImage(str(path))
        if src.isNull():
            return None
        src = src.scaled(RENDER, RENDER, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p = QPainter(img)
        p.drawImage((RENDER - src.width()) // 2, (RENDER - src.height()) // 2, src)
        p.end()
    return img


def _coverage(img) -> float:
    bits = img.constBits().asstring(RENDER * RENDER * 4)
    alphas = bits[3::4]  # ARGB32 en little-endian: B G R A
    return sum(1 for a in alphas[:: 7] if a > 200) / len(alphas[:: 7])


def _png(img) -> str:
    from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return base64.b64encode(bytes(data)).decode()


def wrap(img, dark: bool) -> str:
    """SVG (lienzo 64) con el icono `img` encerrado en el squircle."""
    from PyQt6.QtGui import QImage, QPainter

    tt = icons_apps.tile_tokens()
    if _coverage(img) >= FULL_BLEED:
        # Ya es un «tile»: se recorta a la forma del squircle y ocupa todo.
        clipped = QImage(img.size(), QImage.Format.Format_ARGB32_Premultiplied)
        clipped.fill(0)
        p = QPainter(clipped)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setClipPath(_squircle_path(RENDER / 64))
        p.drawImage(0, 0, img)
        p.end()
        glyph = (f'<image x="0" y="0" width="64" height="64" '
                 f'xlink:href="data:image/png;base64,{_png(clipped)}"/>')
        body = icons_apps.tile(tt.graphite if dark else tt.wrap_paper, tt.white, glyph, dark, tt=tt)
        # sin sombra propia del símbolo: el recorte ya es el tile
        body = body.replace('<g filter="url(#glyphshadow)">', "<g>")
    else:
        side = 52 * INSET
        pos = 32 - side / 2
        glyph = (f'<image x="{pos:.2f}" y="{pos:.2f}" width="{side:.2f}" height="{side:.2f}" '
                 f'xlink:href="data:image/png;base64,{_png(img)}"/>')
        body = icons_apps.tile(tt.graphite if dark else tt.wrap_paper, tt.white, glyph, dark, tt=tt)
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="64" height="64" viewBox="0 0 64 64">{body}</svg>\n')


App = tuple[str, str, Path]   # icon name, Name= of the app, original icon


class Styled:
    """Tinted and Clear icons of the third-party apps: one glyph per app, one mask per glyph floor."""

    def __init__(self, rendered: dict, labels: dict[str, str]):
        tokens = icons_apps.style_token_data()
        self.extract_tokens = icons_glyph.ExtractTokens.from_tokens(tokens)
        self.style_tokens = icons_apps.style_tokens()
        self.scheme = icons_apps.color_scheme_fallback()
        table = icons_glyph.overrides(tokens)
        self.glyphs = {name: icons_glyph.extract(img, labels[name], self.extract_tokens,
                                                 icons_glyph.override_for(name, table))
                       for name, img in rendered.items()}
        self._masks: dict[tuple[str, float], str] = {}

    def mask(self, name: str, style: Style) -> str:
        floor = self.style_tokens.glyph_floor(style)
        if (name, floor) not in self._masks:
            self._masks[name, floor] = self.glyphs[name].mask(floor, self.extract_tokens)
        return self._masks[name, floor]

    def body(self, name: str, style: Style, dark: bool) -> str:
        """Tile body on the 64 canvas ("" when the app keeps the parent theme's wrapped icon)."""
        mask = self.mask(name, style)
        return icons_apps.styled_tile(mask, dark, style, st=self.style_tokens) if mask else ""

    def svg(self, name: str, style: Style, dark: bool) -> str:
        body = self.body(name, style, dark)
        return icons._svg(64, body, self.scheme) if body else ""


def theme_files(spec: icons.ThemeSpec, rendered: dict, styled: Styled) -> dict[str, str]:
    """name → SVG of the wrapped icons of one theme."""
    if spec.style is Style.DEFAULT:
        return {name: wrap(img, spec.dark) for name, img in rendered.items()}
    return {name: svg for name in rendered if (svg := styled.svg(name, spec.style, spec.dark))}


def _guard_inherits(spec: icons.ThemeSpec) -> tuple[str, ...]:
    """Themes whose names could be trimmed to a wrapped app: a styled theme's only
    parent is GoldenGlass*, which _theme_index skips, so it takes its parent's."""
    return THEMES[spec.base_theme].inherits if spec.base is icons.Base.INHERITED else spec.inherits


def _own_names(icons_dir: Path) -> set[str]:
    """Nombres que el tema ya resuelve: los que dibuja (de las definiciones del
    generador) y lo que haya instalado (p. ej. los enlaces de protección)."""
    names = {n for app in icons_apps.APPS for n in app.names} | {n for i in icons.ICONS for n in i.names}
    for base in (icons_dir, *icons.ICON_BASES):
        for sub in ("apps", "inherited", "places", "devices", "mimetypes"):
            d = base / "GoldenGlass" / sub
            if d.is_dir():
                names |= {p.stem for p in d.rglob("*") if p.suffix in (".svg", ".png")}
    return names


def _generator_files() -> list[Path]:
    """Lo que decide el dibujo: este script, los módulos que carga de su
    carpeta (icons, icons_apps, icons_mime…) y los tokens del tile (el TOML en el
    repositorio, el icon-tile.json en el paquete)."""
    here = Path(__file__).resolve().parent
    files = {Path(__file__).resolve()}
    for module in list(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if origin and Path(origin).resolve().parent == here:
            files.add(Path(origin).resolve())
    for tokens in (icons_apps.tile_tokens_source(), icons_apps.style_tokens_source()):
        if tokens:
            files.add(tokens)
    return sorted(files)


def third_party_apps(icons_dir: Path) -> tuple[set[str], list[App]]:
    """Names the themes already resolve, and the visible apps to wrap with their original icon."""
    own = _own_names(icons_dir)
    todo = []
    for name, label in sorted(_apps().items()):
        if name in own or icons._resolves_to(name, own):
            continue
        src = _original(name)
        if src:
            todo.append((name, label, src))
    return own, todo


SHEET_CELL = 104       # px of a sheet cell; the icon is drawn at SHEET_ICON
SHEET_ICON = 88
SHEET_LABEL = 30       # px under each app for its name and outcome
SHEET_COLUMNS = 2      # apps per row; each app shows the original and the four styled themes
SHEET_TEXT = "#1C1C1E"  # labels over the light backdrop of the sheet


def sheet(path: Path, apps: list[App], rendered: dict, styled: Styled, accent: str) -> None:
    """Review sheet: per app, its original icon and its Tinted and Clear icons in
    light and dark, each over its appearance backdrop (Clear over a wallpaper)."""
    from PyQt6.QtCore import QByteArray, QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QImage, QLinearGradient, QPainter
    from PyQt6.QtSvg import QSvgRenderer

    specs = [spec for spec in icons.THEME_SPECS if spec.style is not Style.DEFAULT]
    app_width = (1 + len(specs)) * SHEET_CELL
    rows = -(-len(apps) // SHEET_COLUMNS)
    row_height = SHEET_CELL + SHEET_LABEL
    img = QImage(SHEET_COLUMNS * app_width, rows * row_height, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(icons_apps.PREVIEW_BACKDROPS[False]))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    scheme = f'<style type="text/css">.{ACCENT_CLASS}{{color:{accent};}}</style>'
    inset = (SHEET_CELL - SHEET_ICON) / 2
    for index, (name, label, _) in enumerate(apps):
        x0, y0 = (index % SHEET_COLUMNS) * app_width, (index // SHEET_COLUMNS) * row_height
        if name in rendered:
            p.drawImage(QRectF(x0 + inset, y0 + inset, SHEET_ICON, SHEET_ICON), rendered[name])
        for column, spec in enumerate(specs, start=1):
            cell = QRectF(x0 + column * SHEET_CELL, y0, SHEET_CELL, SHEET_CELL)
            p.fillRect(cell, QColor(icons_apps.PREVIEW_BACKDROPS[spec.dark]))
            if spec.style is Style.CLEAR:
                wallpaper = QLinearGradient(cell.topLeft(), QPointF(cell.right(), cell.bottom()))
                for i, color in enumerate(icons_apps.PREVIEW_WALLPAPER):
                    wallpaper.setColorAt(i / (len(icons_apps.PREVIEW_WALLPAPER) - 1), QColor(color))
                p.fillRect(QRectF(cell.center().x(), cell.top(), SHEET_CELL / 2, SHEET_CELL), wallpaper)
            body = styled.body(name, spec.style, spec.dark) if name in rendered else ""
            if body:
                svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="{XLINK_NS}" viewBox="0 0 64 64">'
                       f'<defs>{scheme}</defs>{body}</svg>')
                QSvgRenderer(QByteArray(svg.encode())).render(p, cell.adjusted(inset, inset, -inset, -inset))
        glyph = styled.glyphs.get(name)
        outcome = (f"{glyph.kind.value}  ink {glyph.ink:.2f}  detail {glyph.detail:.1f}  "
                   f"outline {glyph.outline_detail:.1f}") if glyph else "unreadable"
        p.setPen(QColor(SHEET_TEXT))
        p.drawText(QRectF(x0 + 4, y0 + SHEET_CELL, app_width - 8, SHEET_LABEL),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{label} ({name})\n{outcome}")
    p.end()
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))


def outcome_counts(styled: Styled) -> dict[icons_glyph.Kind, int]:
    counts = dict.fromkeys(icons_glyph.Kind, 0)
    for glyph in styled.glyphs.values():
        counts[glyph.kind] += 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--icons-dir", type=Path,
                    default=Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons")
    ap.add_argument("--list", action="store_true", help="enseña qué se encerraría, sin escribir")
    ap.add_argument("--clean", action="store_true", help="borra los iconos encerrados")
    ap.add_argument("--if-changed", action="store_true",
                    help="no hace nada si las apps y sus iconos no cambiaron desde la última vez")
    ap.add_argument("--sheet", type=Path, help="escribe una hoja de revisión de los iconos Tintado y Transparente en vez de los temas")
    ap.add_argument("--accent", default=icons_apps.PREVIEW_ACCENT, help="color de acento de la hoja (#RRGGBB)")
    args = ap.parse_args()

    if args.clean:
        for theme in THEMES:
            shutil.rmtree(args.icons_dir / theme / "wrapped", ignore_errors=True)
        return 0

    from PyQt6.QtGui import QGuiApplication
    _app = QGuiApplication.instance() or QGuiApplication(["goldenglass-wrap-icons", "-platform", "offscreen"])  # noqa: F841

    own, todo = third_party_apps(args.icons_dir)

    # Huella de lo que se encerraría (nombres, archivos y fechas) y del propio
    # generador: con --if-changed, si coincide con la última, no se repite.
    digest = hashlib.sha256()
    for path in _generator_files():
        digest.update(f"{path.name}\0".encode() + path.read_bytes())
    for name, label, src in todo:
        digest.update(f"{name}\0{label}\0{src}\0{src.stat().st_mtime_ns}\0".encode())
    stamp = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "goldenglass" / "wrap-icons.stamp"
    complete = all((args.icons_dir / t / "wrapped").is_dir() for t in THEMES)
    if args.if_changed and complete and stamp.exists() and stamp.read_text() == digest.hexdigest():
        return 0
    if args.list:
        for name, label, src in todo:
            print(f"{name:40} {label:30} {src}")
        return 0

    rendered = {name: img for name, _, src in todo if (img := _render(src)) is not None}
    styled = Styled(rendered, {name: label for name, label, _ in todo})
    counts = ", ".join(f"{kind.value} {count}" for kind, count in outcome_counts(styled).items())
    if args.sheet:
        sheet(args.sheet, todo, rendered, styled, args.accent)
        print(f"{args.sheet}: {len(rendered)} apps ({counts})")
        return 0
    for spec in THEMES.values():
        out = args.icons_dir / spec.id / "wrapped"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        files = theme_files(spec, rendered, styled)
        for name, svg in files.items():
            (out / f"{name}.svg").write_text(svg, encoding="utf-8")
        # Mismo recorte de nombres que con las apps dibujadas (ver icons.py)
        icons._guards(args.icons_dir / spec.id, _guard_inherits(spec), set(files), own | set(files), folder="wrapped")
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(digest.hexdigest())
    print(f"GoldenGlass: {len(rendered)} iconos encerrados en {args.icons_dir}/GoldenGlass*/wrapped "
          f"(Tintado y Transparente: {counts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
