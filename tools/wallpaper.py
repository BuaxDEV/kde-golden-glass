# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fondo de pantalla «GoldenGlass»: ondas de vidrio sobre la bahía al atardecer
(día) y de noche, generado por código (sin imágenes en el repositorio).

Cada capa es una onda suave rellena con un color translúcido, con un filo de
luz en su borde superior, sobre un cielo en degradado y un brillo difuso (sol
de día, luna de noche). Un grano mínimo evita bandas en los degradados.

Salida (paquete de fondo de Plasma, cambio automático claro/oscuro):
  build/wallpapers/GoldenGlass/metadata.json
  build/wallpapers/GoldenGlass/contents/images/<WxH>.jpg
  build/wallpapers/GoldenGlass/contents/images_dark/<WxH>.jpg
  build/wallpapers/GoldenGlass/contents/screenshot.jpg

Uso directo para iterar el diseño:
  python3 tools/wallpaper.py --preview build/wallpaper-preview.png
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

THEME_ID = "GoldenGlass"
SIZES = ((5120, 2880), (3840, 2400))  # 16:9 y 16:10; Plasma elige el más cercano
SEED = 2027


@dataclass(frozen=True)
class Wave:
    base: float        # altura media del borde (0 = arriba, 1 = abajo)
    amplitude: float   # amplitud relativa a la altura
    frequency: float   # ondas a lo ancho
    phase: float
    top: str           # color junto al borde
    bottom: str        # color al fondo de la capa
    alpha: float
    rim: float         # intensidad del filo de luz
    tilt: float = 0.0  # inclinación del borde (diferencia entre extremos)


@dataclass(frozen=True)
class Palette:
    sky: tuple[tuple[float, str], ...]
    glow: tuple[float, float, float, str, float]  # x, y, radio (relativos), color, intensidad
    waves: tuple[Wave, ...]


DAY = Palette(
    sky=((0.0, "#1B2F5E"), (0.38, "#5B5FA6"), (0.62, "#D9788A"), (0.8, "#F5A15C"), (1.0, "#FBD9A6")),
    glow=(0.70, 0.40, 0.55, "#FFE2B0", 0.75),
    waves=(
        Wave(0.44, 0.090, 0.80, 0.6, "#FFB37A", "#E9785E", 0.55, 0.35, 0.10),
        Wave(0.53, 0.100, 0.65, 2.1, "#F28C4A", "#C9503B", 0.60, 0.45, -0.08),
        Wave(0.63, 0.080, 1.05, 4.0, "#E8553A", "#9E3A4C", 0.62, 0.50, 0.06),
        Wave(0.74, 0.060, 0.85, 1.2, "#5E5AA8", "#2F3C7A", 0.70, 0.40, -0.05),
        Wave(0.86, 0.050, 1.15, 3.3, "#2E4C8C", "#16285A", 0.80, 0.30, 0.04),
    ),
)

NIGHT = Palette(
    sky=((0.0, "#03071A"), (0.45, "#0E1A44"), (0.72, "#283670"), (0.88, "#4A3C78"), (1.0, "#6B4A7E")),
    glow=(0.30, 0.30, 0.45, "#9DB8FF", 0.35),
    waves=(
        Wave(0.44, 0.090, 0.80, 0.6, "#4A5BA8", "#2C3878", 0.50, 0.30, 0.10),
        Wave(0.53, 0.100, 0.65, 2.1, "#6B4FA0", "#3C2C6E", 0.55, 0.35, -0.08),
        Wave(0.63, 0.080, 1.05, 4.0, "#C4553A", "#5E2A44", 0.45, 0.45, 0.06),
        Wave(0.74, 0.060, 0.85, 1.2, "#1E3B7A", "#0F1E48", 0.72, 0.30, -0.05),
        Wave(0.86, 0.050, 1.15, 3.3, "#0F2252", "#060F2C", 0.85, 0.25, 0.04),
    ),
)


def _rgb(hex_color: str) -> np.ndarray:
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def _gradient(stops: tuple[tuple[float, str], ...], t: np.ndarray) -> np.ndarray:
    """Interpola colores (N, 3) en posiciones t (N,)."""
    positions = np.array([p for p, _ in stops], dtype=np.float32)
    colors = np.stack([_rgb(c) for _, c in stops])
    return np.stack([np.interp(t, positions, colors[:, k]) for k in range(3)], axis=-1).astype(np.float32)


def render(width: int, height: int, palette: Palette) -> Image.Image:
    rng = np.random.default_rng(SEED)
    ys = (np.arange(height, dtype=np.float32) + 0.5) / height
    xs = (np.arange(width, dtype=np.float32) + 0.5) / width

    # Cielo
    canvas = np.repeat(_gradient(palette.sky, ys)[:, None, :], width, axis=1)

    # Brillo difuso (sol o luna); aspecto corregido para que sea redondo
    gx, gy, gr, gcolor, gstrength = palette.glow
    aspect = width / height
    dx = (xs[None, :] - gx) * aspect
    dy = ys[:, None] - gy
    glow = np.exp(-(dx * dx + dy * dy) / (2 * (gr * 0.5) ** 2)).astype(np.float32) * gstrength
    canvas += (_rgb(gcolor) - canvas) * glow[..., None]

    # Ondas de vidrio, de atrás hacia delante
    px = 1.0 / height  # un píxel en unidades relativas
    for wave in palette.waves:
        x = xs * 2 * math.pi * wave.frequency + wave.phase
        edge = (wave.base
                + wave.tilt * (xs - 0.5)
                + wave.amplitude * np.sin(x)
                + wave.amplitude * 0.35 * np.sin(2.3 * x + 1.7)
                + wave.amplitude * 0.15 * np.sin(5.1 * x + 0.4))
        d = ys[:, None] - edge[None, :]                       # >0 dentro de la capa
        coverage = np.clip(d / (1.5 * px) + 0.5, 0.0, 1.0)    # borde antialias
        depth = np.clip(d / 0.25, 0.0, 1.0)
        color = _rgb(wave.top) + (_rgb(wave.bottom) - _rgb(wave.top)) * depth[..., None]
        alpha = (wave.alpha * coverage)[..., None]
        canvas = canvas * (1 - alpha) + color * alpha
        # filo de luz: banda gaussiana justo dentro del borde
        rim = np.exp(-((d - 3 * px) / (10 * px)) ** 2) * coverage * wave.rim
        canvas += (1.0 - canvas) * rim[..., None] * 0.6

    # Grano mínimo contra las bandas
    canvas += rng.normal(0.0, 1.2 / 255, size=canvas.shape).astype(np.float32)
    data = (np.clip(canvas, 0.0, 1.0) * 255 + 0.5).astype(np.uint8)
    return Image.fromarray(data, "RGB")


def _stamp() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def build(out: Path) -> list[Path]:
    """Genera el paquete de fondo; se salta si el generador no cambió."""
    root = out / "wallpapers" / THEME_ID
    stamp_file = root / ".stamp"
    if stamp_file.exists() and stamp_file.read_text() == _stamp():
        return []
    if root.exists():
        shutil.rmtree(root)

    written: list[Path] = []
    for folder, palette in (("images", DAY), ("images_dark", NIGHT)):
        for width, height in SIZES:
            path = root / "contents" / folder / f"{width}x{height}.jpg"
            path.parent.mkdir(parents=True, exist_ok=True)
            render(width, height, palette).save(path, quality=93, optimize=True, progressive=True)
            written.append(path)

    shot = root / "contents" / "screenshot.jpg"
    render(800, 450, DAY).save(shot, quality=90)
    written.append(shot)

    meta = root / "metadata.json"
    meta.write_text(json.dumps({
        "KPlugin": {
            "Authors": [{"Name": "GoldenGlass contributors"}],
            "Id": THEME_ID,
            "License": "CC-BY-SA-4.0",
            "Name": "GoldenGlass",
        }
    }, indent=4) + "\n", encoding="utf-8")
    written.append(meta)
    stamp_file.write_text(_stamp())
    return written


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preview", type=Path, required=True, help="PNG de vista previa (día arriba, noche abajo)")
    ap.add_argument("--width", type=int, default=1280)
    args = ap.parse_args()
    h = args.width * 9 // 16
    sheet = Image.new("RGB", (args.width, h * 2))
    sheet.paste(render(args.width, h, DAY), (0, 0))
    sheet.paste(render(args.width, h, NIGHT), (0, h))
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.preview)
    print(args.preview)
