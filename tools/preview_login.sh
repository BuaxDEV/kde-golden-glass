#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Vista previa del tema de SDDM sin cerrar sesión ni root: el greeter real de
# SDDM en modo prueba dentro de un contenedor podman, sobre un Xvfb, con
# usuarios de prueba. La hora se fija con TZ para ver el fondo de día y el de
# noche. No toca el sistema ni abre ventanas.
#
#   tools/preview_login.sh [ANCHOxALTO]
#
# Salida: build/login-preview/{day,night,typed,users,chosen}.png
# La primera vez crea la imagen local goldenglass-login-preview; se rehace sola
# si cambia este script.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIZE="${1:-1920x1080}"
IMAGE=localhost/goldenglass-login-preview
OUT="$ROOT/build/login-preview"

[[ -f $ROOT/build/login/sddm/GoldenGlass/theme.conf && -d $ROOT/build/wallpapers/GoldenGlass ]] \
  || QT_QPA_PLATFORM=offscreen python3 "$ROOT/tools/gen_tokens.py" >/dev/null

recipe=$(sha256sum "${BASH_SOURCE[0]}" | cut -c1-12)
if ! podman image exists "$IMAGE:$recipe"; then
  echo "Creando la imagen $IMAGE (una vez)…" >&2
  podman build -q -t "$IMAGE:$recipe" -f - . >/dev/null <<'EOF'
FROM docker.io/library/archlinux:latest
RUN pacman -Syu --noconfirm --needed sddm qt6-svg xorg-server-xvfb xorg-xwd xdotool imagemagick \
      inter-font ttf-dejavu fontconfig && pacman -Scc --noconfirm
EOF
fi

mkdir -p "$OUT"
podman run --rm \
  -v "$ROOT/build/login/sddm/GoldenGlass:/theme:ro,Z" \
  -v "$ROOT/build/wallpapers/GoldenGlass:/usr/share/wallpapers/GoldenGlass:ro,Z" \
  -v "$ROOT/fontconfig/60-goldenglass.conf:/etc/fonts/conf.d/60-goldenglass.conf:ro,Z" \
  -v "$OUT:/out:Z" \
  -e SIZE="$SIZE" -e LANG=es_ES.UTF-8 \
  "$IMAGE:$recipe" bash -c '
set -u
# en modo prueba SDDM dice que no se puede apagar: en la copia se muestran los
# botones igualmente
cp -r /theme /usr/share/sddm/themes/GoldenGlass
sed -i "s/sddm\.can\(Suspend\|Reboot\|PowerOff\)/true/" /usr/share/sddm/themes/GoldenGlass/Main.qml
# hora local fija: TZ=Etc/GMT-k suma k horas a UTC
tz_for() { local k=$(( ($1 - 10#$(date -u +%H) + 36) % 24 - 12 )); echo "Etc/GMT$( ((k >= 0)) && echo "-$k" || echo "+$((-k))")"; }

Xvfb :5 -screen 0 ${SIZE}x24 >/dev/null 2>&1 &
sleep 1
export DISPLAY=:5

greeter() {   # $1 = hora local
  TZ=$(tz_for $1) sddm-greeter-qt6 --test-mode --theme /usr/share/sddm/themes/GoldenGlass >>/out/greeter.log 2>&1 &
  sleep 3
}
shot() { sleep "${2:-0.5}"; xwd -root -silent | magick xwd:- "/out/$1.png"; }
stop() { pkill -f sddm-greeter-qt6; sleep 0.5; }
: >/out/greeter.log

useradd -m -u 1000 -c "Buapdev" buapdev
greeter 12; shot day
xdotool type --delay 40 "goldenglass"; shot typed
stop
greeter 22; shot night
stop

useradd -m -u 1001 -c "Ana García" ana
mkdir -p /usr/share/sddm/faces
magick -size 256x256 gradient:"#F2A65A-#C4553A" /usr/share/sddm/faces/ana.face.icon.png
mv /usr/share/sddm/faces/ana.face.icon.png /usr/share/sddm/faces/ana.face.icon
greeter 12; shot users
xdotool key Return; shot chosen
stop
' >/dev/null

ls -1 "$OUT"/*.png
grep -iE "error|warning|qrc|file:" "$OUT/greeter.log" | grep -v "^$" | sort -u | head -20 || true
