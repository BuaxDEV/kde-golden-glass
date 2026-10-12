#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Vista previa de los temas de Plymouth sin reiniciar ni root: Plymouth real
# (renderer x11) dentro de un contenedor podman, sobre un Xvfb, con capturas de
# cada estado. No toca el sistema ni abre ventanas.
#
#   tools/preview_plymouth.sh [goldenglass|goldenglass-light] [ANCHOxALTO]
#
# Salida: build/plymouth-preview/<tema>-{boot,password,question,message,shutdown}.png
# La primera vez crea la imagen local goldenglass-plymouth-preview (Arch +
# plymouth, gtk3, Xvfb, xdotool…); se rehace sola si cambia este script.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THEME="${1:-goldenglass}"
SIZE="${2:-1920x1080}"
IMAGE=localhost/goldenglass-plymouth-preview
OUT="$ROOT/build/plymouth-preview"

[[ -f $ROOT/build/plymouth/$THEME/$THEME.plymouth ]] || python3 "$ROOT/tools/gen_tokens.py" >/dev/null
[[ -f $ROOT/build/plymouth/$THEME/$THEME.plymouth ]] || { echo "no existe el tema $THEME" >&2; exit 2; }

recipe=$(sha256sum "${BASH_SOURCE[0]}" | cut -c1-12)
if ! podman image exists "$IMAGE:$recipe"; then
  echo "Creando la imagen $IMAGE (una vez)…" >&2
  podman build -q -t "$IMAGE:$recipe" -f - . >/dev/null <<'EOF'
FROM docker.io/library/archlinux:latest
RUN pacman -Syu --noconfirm --needed plymouth gtk3 xorg-server-xvfb xorg-xwd xdotool \
      imagemagick inter-font ttf-dejavu fontconfig && pacman -Scc --noconfirm
EOF
fi

mkdir -p "$OUT"
podman run --rm -t \
  -v "$ROOT/build/plymouth/$THEME:/usr/share/plymouth/themes/$THEME:ro,Z" \
  -v "$ROOT/fontconfig/60-goldenglass.conf:/etc/fonts/conf.d/60-goldenglass.conf:ro,Z" \
  -v "$OUT:/out:Z" \
  -e THEME="$THEME" -e SIZE="$SIZE" \
  "$IMAGE:$recipe" bash -c '
set -u
Xvfb :5 -screen 0 ${SIZE}x24 >/dev/null 2>&1 &
sleep 1
export DISPLAY=:5

start() {   # $1 = modo de plymouthd
  plymouthd --no-daemon --no-boot-log --mode=$1 --tty=$(tty) \
    --kernel-command-line="splash plymouth.splash=$THEME plymouth.ignore-udev" \
    --debug-file=/out/$THEME-$1.log &
  sleep 1
  plymouth show-splash
  xdotool search --sync --onlyvisible --name . windowfocus 2>/dev/null || true
}
shot() { sleep "${2:-0.6}"; xwd -root -silent | magick xwd:- "/out/$THEME-$1.png"; }

start boot
shot boot 3
plymouth ask-for-password --prompt="Introduce la contraseña del disco root" >/dev/null &
sleep 0.5; xdotool type --delay 40 "goldenglass"
shot password
xdotool key Return; sleep 0.3
plymouth ask-question --prompt="¿Continuar sin el disco de datos?" >/dev/null &
sleep 0.5; xdotool type --delay 40 "si"
shot question
xdotool key Return; sleep 0.3
plymouth display-message --text="Comprobando el disco /dev/nvme0n1p2…"
shot message
plymouth quit; sleep 0.5

start shutdown
shot shutdown 1.5
plymouth quit
' >/dev/null

ls -1 "$OUT"/"$THEME"-*.png
grep -h -iE "script.*error|error.*script|failed to parse" "$OUT"/"$THEME"-*.log || true
