# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tema de sonidos «GoldenGlass»: sintetizado por código (sin audio en el repo).

Cada evento de [sounds.events] en los tokens es una lista de capas (notas de
cristal y ráfagas de ruido filtrado) que se mezclan, pasan por una cola de sala
corta y se normalizan. Solo se cubren los eventos que tiene macOS (más los que
Plasma necesita para no perder avisos); el resto de nombres freedesktop se
desactiva con archivos `.disabled`: la especificación siempre recurre al tema
`freedesktop` cuando falta un sonido, y `.disabled` corta esa búsqueda.

Salida (tema freedesktop, Ogg Vorbis con python-soundfile):
  build/sounds/GoldenGlass/index.theme
  build/sounds/GoldenGlass/stereo/<evento>.oga
  build/sounds/GoldenGlass/stereo/<nombre>.oga  → enlace al de su evento
  build/sounds/GoldenGlass/stereo/<nombre>.disabled

Uso directo para iterar el diseño:
  python3 tools/sounds.py --preview build/sounds-preview   # un .wav por evento
  python3 tools/sounds.py --play notification             # escucharlo (pw-play)
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np

from ggcommon import load_tokens, stamp

THEME_ID = "GoldenGlass"

# Evento de los tokens → nombres freedesktop que lo usan. El primero da nombre
# al archivo; los demás son enlaces.
EVENTS: dict[str, tuple[str, ...]] = {
    # alerta de macOS; también los avisos de los cuadros de diálogo de KDE
    "alert": ("bell", "bell-window-system", "dialog-warning", "dialog-error",
              "dialog-error-critical", "dialog-error-serious"),
    "notification": ("message-new-instant", "message-new-email"),
    "trash": ("trash-empty",),
    "screenshot": ("screen-capture", "camera-shutter"),
    "volume": ("audio-volume-change",),
    "device_added": ("device-added",),
    "device_removed": ("device-removed",),
    "battery_low": ("battery-low", "battery-caution"),
    "power_plug": ("power-plug",),
    "alarm": ("alarm-clock-elapsed",),
    "auth": ("dialog-warning-auth",),
    "login": ("desktop-login",),
}

# Nombres de los temas freedesktop y ocean que quedan en silencio, como en
# macOS. No se tocan los de la prueba de altavoces (audio-channel-*,
# audio-test-signal) ni theme-demo.
SILENT = (
    "battery-full", "button-pressed", "button-pressed-modifier", "complete",
    "complete-media-burn", "complete-media-error", "completion-fail",
    "completion-partial", "completion-rotation", "completion-success",
    "desktop-logout", "dialog-information", "dialog-question", "game-over-loser",
    "game-over-winner", "media-insert-request", "message", "message-attention",
    "message-contact-in", "message-contact-out", "message-highlight",
    "message-sent-instant", "network-connectivity-established",
    "network-connectivity-lost", "outcome-failure", "outcome-success",
    "phone-incoming-call", "phone-outgoing-busy", "phone-outgoing-calling",
    "power-unplug", "service-login", "service-logout", "suspend-error",
    "window-attention", "window-question",
)

SILENCE_DB = -70.0  # se recorta la cola por debajo de este nivel
FADE_S = 0.01


# --- síntesis ---------------------------------------------------------------

def _db(x: float) -> float:
    return 10 ** (x / 20)


def _decay_env(t: np.ndarray, t60: float) -> np.ndarray:
    """Caída exponencial que llega a -60 dB en t60 segundos."""
    return np.power(10.0, -3.0 * t / max(t60, 1e-4))


def _tone(layer: dict, cfg: dict, sr: int) -> np.ndarray:
    freq = float(layer["tone"])
    t60 = float(layer["decay"])
    attack = float(layer.get("attack", cfg["attack"]))
    partials = layer.get("partials", cfg["partials"])
    n = int(sr * (t60 + attack)) + 1
    t = np.arange(n) / sr
    # glissando exponencial de freq a glide a lo largo de la nota
    glide = float(layer.get("glide", freq))
    inst = freq * np.power(glide / freq, np.minimum(t / max(t60, 1e-4), 1.0))
    phase = 2 * math.pi * np.cumsum(inst) / sr
    out = np.zeros(n)
    for ratio, amp, div in partials:
        if freq * ratio >= sr / 2:
            continue
        out += amp * np.sin(phase * ratio) * _decay_env(t, t60 / div)
    out *= np.minimum(t / max(attack, 1e-4), 1.0)
    return out


def _band_noise(n: int, lo: float, hi: float, sr: int, rng: np.random.Generator) -> np.ndarray:
    """Ruido blanco filtrado a una banda (en frecuencia, con bordes suaves)."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / sr)
    edge = 0.25  # octavas de transición en cada borde
    with np.errstate(divide="ignore"):
        octs = np.log2(np.maximum(f, 1.0))
    low = np.clip((octs - math.log2(lo)) / edge + 0.5, 0, 1)
    high = np.clip((math.log2(hi) - octs) / edge + 0.5, 0, 1)
    out = np.fft.irfft(spec * low * high, n)
    peak = np.max(np.abs(out))
    return out / peak if peak > 0 else out


def _noise(layer: dict, sr: int) -> np.ndarray:
    lo, hi = (float(x) for x in layer["noise"])
    length = float(layer["length"])
    rng = np.random.default_rng(int(layer.get("seed", 1)))
    n = max(int(sr * length), 16)
    grains = int(layer.get("grains", 1))
    if grains <= 1:
        burst = _band_noise(n, lo, hi, sr, rng)
        t = np.arange(n) / n
        return burst * np.minimum(t * 8, 1.0) * np.power(1 - t, 2)
    # ráfagas sueltas: crecen y se apagan a lo largo de length (papel)
    out = np.zeros(n + int(sr * 0.05))
    starts = np.sort(rng.uniform(0, length, grains))
    for s in starts:
        g_len = int(sr * rng.uniform(0.012, 0.045))
        g = _band_noise(g_len, lo * rng.uniform(0.8, 1.2), hi, sr, rng)
        g *= np.hanning(g_len) * rng.uniform(0.35, 1.0)
        g *= math.sin(math.pi * min(s / length, 1.0)) ** 0.6 + 0.15
        i = int(s * sr)
        out[i:i + g_len] += g[: len(out) - i]
    return out


def _reverb(dry: np.ndarray, cfg: dict, sr: int) -> np.ndarray:
    """Cola de sala corta: ruido que decae, distinto en cada canal (amplitud)."""
    mix = float(cfg["reverb"])
    t60 = float(cfg["reverb_decay"])
    n_ir = int(sr * t60)
    rng = np.random.default_rng(2027)
    t = np.arange(n_ir) / sr
    n = len(dry) + n_ir
    size = 1 << (n - 1).bit_length()
    dry_f = np.fft.rfft(dry, size)
    out = np.zeros((n, 2))
    for ch in range(2):
        ir = rng.standard_normal(n_ir) * _decay_env(t, t60)
        ir[: int(sr * 0.008)] = 0  # predelay
        ir /= np.sqrt(np.sum(ir ** 2))
        wet = np.fft.irfft(dry_f * np.fft.rfft(ir, size), size)[:n]
        out[: len(dry), ch] += dry
        out[:, ch] += mix * wet
    return out


def render(name: str, cfg: dict) -> np.ndarray:
    """Devuelve el evento como array (muestras, 2) en float32, ya normalizado."""
    sr = int(cfg["sample_rate"])
    event = cfg["events"][name]
    voices: list[tuple[float, np.ndarray]] = []
    for layer in event["layers"]:
        if "tone" in layer:
            sig = _tone(layer, cfg, sr)
        elif "noise" in layer:
            sig = _noise(layer, sr)
        else:
            raise ValueError(f"[sounds.events.{name}]: capa sin tone ni noise: {layer}")
        voices.append((float(layer.get("at", 0.0)), sig * float(layer.get("gain", 1.0))))

    repeat = int(event.get("repeat", 1))
    every = float(event.get("every", 0.0))
    starts = [(at + k * every, sig) for k in range(repeat) for at, sig in voices]
    length = max(int(at * sr) + len(sig) for at, sig in starts)
    dry = np.zeros(length)
    for at, sig in starts:
        i = int(at * sr)
        dry[i:i + len(sig)] += sig

    out = _reverb(dry, cfg, sr)
    peak = np.max(np.abs(out))
    out *= float(cfg["volume"]) * float(event.get("gain", 1.0)) / peak

    # recorta la cola en silencio y la cierra con un fundido
    loud = np.nonzero(np.max(np.abs(out), axis=1) > _db(SILENCE_DB))[0]
    end = int(loud[-1]) + 1 if len(loud) else len(out)
    out = out[:end]
    fade = min(int(sr * FADE_S), len(out))
    out[len(out) - fade:] *= np.linspace(1.0, 0.0, fade)[:, None]
    return out.astype(np.float32)


# --- tema -------------------------------------------------------------------

def _check(cfg: dict) -> None:
    events = set(cfg["events"])
    if events != set(EVENTS):
        missing, extra = set(EVENTS) - events, events - set(EVENTS)
        raise ValueError(f"[sounds.events]: faltan {sorted(missing)}, sobran {sorted(extra)}")
    covered = [n for names in EVENTS.values() for n in names]
    if len(covered) != len(set(covered)) or set(covered) & set(SILENT):
        raise ValueError("tools/sounds.py: un nombre freedesktop está repetido")


def _stamp(cfg: dict) -> str:
    return stamp(Path(__file__), data=cfg)


def build(tokens: dict, out: Path) -> list[Path]:
    """Genera el tema de sonidos; se salta si ni el generador ni [sounds] cambiaron."""
    cfg = tokens["sounds"]
    _check(cfg)
    root = out / "sounds" / THEME_ID
    stamp_file = root / ".stamp"
    if stamp_file.exists() and stamp_file.read_text() == _stamp(cfg):
        return []
    try:
        import soundfile  # solo para generar; el tema instalado no lo necesita
    except ImportError:
        raise SystemExit("tools/sounds.py: falta python-soundfile (sudo pacman -S python-soundfile)") from None

    if root.exists():
        shutil.rmtree(root)
    stereo = root / "stereo"
    stereo.mkdir(parents=True)
    written: list[Path] = []
    for event, names in EVENTS.items():
        main = stereo / f"{names[0]}.oga"
        soundfile.write(main, render(event, cfg), int(cfg["sample_rate"]),
                        format="OGG", subtype="VORBIS")
        written.append(main)
        for alias in names[1:]:
            link = stereo / f"{alias}.oga"
            link.symlink_to(main.name)
            written.append(link)
    for name in SILENT:
        path = stereo / f"{name}.disabled"
        path.touch()
        written.append(path)

    index = root / "index.theme"
    index.write_text(
        "# Generado por tools/sounds.py desde tokens/goldenglass.toml — NO EDITAR\n"
        "[Sound Theme]\n"
        "Name=GoldenGlass\n"
        "Comment=Glass sounds for the GoldenGlass theme\n"
        "Comment[es]=Sonidos de cristal del tema GoldenGlass\n"
        "Directories=stereo\n"
        "\n"
        "[stereo]\n"
        "OutputProfile=stereo\n",
        encoding="utf-8",
    )
    written.append(index)
    stamp_file.write_text(_stamp(cfg))
    return written


if __name__ == "__main__":
    import argparse
    import subprocess
    import sys
    import tempfile
    import wave

    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tokens", type=Path, default=root / "tokens" / "goldenglass.toml")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", type=Path, metavar="DIR", help="escribe un .wav por evento")
    group.add_argument("--play", nargs="+", metavar="EVENTO", choices=sorted(EVENTS),
                       help="reproduce eventos con pw-play")
    args = ap.parse_args()
    cfg = load_tokens(args.tokens)["sounds"]
    _check(cfg)

    def write_wav(path: Path, data: np.ndarray) -> None:
        pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(int(cfg["sample_rate"]))
            w.writeframes(pcm.tobytes())

    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        for event in EVENTS:
            path = args.preview / f"{event}.wav"
            write_wav(path, render(event, cfg))
            print(path)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            for event in args.play:
                path = Path(tmp) / f"{event}.wav"
                write_wav(path, render(event, cfg))
                print(event, file=sys.stderr)
                subprocess.run(["pw-play", str(path)], check=True)
