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

Uso:
  goldenglass-wrap-icons            (o python3 tools/wrap_icons.py)
  goldenglass-wrap-icons --list     solo enseña qué haría
  goldenglass-wrap-icons --clean    borra los iconos encerrados
  goldenglass-wrap-icons --if-changed   solo si cambiaron las apps (autostart)

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

THEMES = {"GoldenGlass": False, "GoldenGlass-Dark": True}  # tema → oscuro
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
    tokens = icons_apps.tile_tokens_source()
    if tokens:
        files.add(tokens)
    return sorted(files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--icons-dir", type=Path,
                    default=Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "icons")
    ap.add_argument("--list", action="store_true", help="enseña qué se encerraría, sin escribir")
    ap.add_argument("--clean", action="store_true", help="borra los iconos encerrados")
    ap.add_argument("--if-changed", action="store_true",
                    help="no hace nada si las apps y sus iconos no cambiaron desde la última vez")
    args = ap.parse_args()

    if args.clean:
        for theme in THEMES:
            shutil.rmtree(args.icons_dir / theme / "wrapped", ignore_errors=True)
        return 0

    from PyQt6.QtGui import QGuiApplication
    _app = QGuiApplication.instance() or QGuiApplication(["goldenglass-wrap-icons", "-platform", "offscreen"])  # noqa: F841

    own = _own_names(args.icons_dir)
    todo = []
    for name, label in sorted(_apps().items()):
        if name in own or icons._resolves_to(name, own):
            continue
        src = _original(name)
        if src:
            todo.append((name, label, src))

    # Huella de lo que se encerraría (nombres, archivos y fechas) y del propio
    # generador: con --if-changed, si coincide con la última, no se repite.
    digest = hashlib.sha256()
    for path in _generator_files():
        digest.update(f"{path.name}\0".encode() + path.read_bytes())
    for name, _, src in todo:
        digest.update(f"{name}\0{src}\0{src.stat().st_mtime_ns}\0".encode())
    stamp = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "goldenglass" / "wrap-icons.stamp"
    complete = all((args.icons_dir / t / "wrapped").is_dir() for t in THEMES)
    if args.if_changed and complete and stamp.exists() and stamp.read_text() == digest.hexdigest():
        return 0
    if args.list:
        for name, label, src in todo:
            print(f"{name:40} {label:30} {src}")
        return 0

    rendered = {name: img for name, _, src in todo if (img := _render(src)) is not None}
    for theme, dark in THEMES.items():
        out = args.icons_dir / theme / "wrapped"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        for name, img in rendered.items():
            (out / f"{name}.svg").write_text(wrap(img, dark), encoding="utf-8")
        # Mismo recorte de nombres que con las apps dibujadas (ver icons.py)
        inherits = icons.THEMES[theme].inherits
        icons._guards(args.icons_dir / theme, inherits, set(rendered), own | set(rendered), folder="wrapped")
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(digest.hexdigest())
    print(f"GoldenGlass: {len(rendered)} iconos encerrados en {args.icons_dir}/GoldenGlass{{,-Dark}}/wrapped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
