#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Instalación de desarrollo de GoldenGlass en ~/.local (sin empaquetar).
# Para instalar en el sistema usar packaging/goldenglass/PKGBUILD (paquetes divididos).
#
#   tools/install.sh            genera e instala (copia)
#   tools/install.sh --dev      genera e instala con symlinks (iterar sin reinstalar)
#                               ~/.local manda sobre el paquete y el hook de pacman que
#                               protege el shell no lo cubre: la sesión usa el árbol de
#                               trabajo tal cual (rama, cambios a medias).
#   tools/install.sh --uninstall
#
# No aplica nada: para usar el tema, elegir el Global Theme en Preferencias del
# Sistema › Colores y temas, o `plasma-apply-lookandfeel -a org.goldenglass.light.desktop`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

# origen (relativo a ROOT; archivo o carpeta) → destino
declare -A TARGETS=(
  [build/color-schemes/GoldenGlassLight.colors]="$DATA/color-schemes/GoldenGlassLight.colors"
  [build/color-schemes/GoldenGlassDark.colors]="$DATA/color-schemes/GoldenGlassDark.colors"
  [fontconfig/60-goldenglass.conf]="$CONF/fontconfig/conf.d/60-goldenglass.conf"
  [build/plasma/desktoptheme/GoldenGlass]="$DATA/plasma/desktoptheme/GoldenGlass"
  [build/plasma/look-and-feel/org.goldenglass.light.desktop]="$DATA/plasma/look-and-feel/org.goldenglass.light.desktop"
  [build/plasma/look-and-feel/org.goldenglass.dark.desktop]="$DATA/plasma/look-and-feel/org.goldenglass.dark.desktop"
  [build/plasma/shells/org.goldenglass.desktop]="$DATA/plasma/shells/org.goldenglass.desktop"
  [build/plasma/plasmoids/org.goldenglass.systemmenu]="$DATA/plasma/plasmoids/org.goldenglass.systemmenu"
  [build/plasma/plasmoids/org.goldenglass.appname]="$DATA/plasma/plasmoids/org.goldenglass.appname"
  [build/plasma/plasmoids/org.goldenglass.clock]="$DATA/plasma/plasmoids/org.goldenglass.clock"
  [build/plasma/plasmoids/org.goldenglass.controlcenter]="$DATA/plasma/plasmoids/org.goldenglass.controlcenter"
  [build/plasma/plasmoids/org.goldenglass.launchpad]="$DATA/plasma/plasmoids/org.goldenglass.launchpad"
  [build/plasma/plasmoids/org.goldenglass.trash]="$DATA/plasma/plasmoids/org.goldenglass.trash"
  [build/plasma/plasmoids/org.goldenglass.dock]="$DATA/plasma/plasmoids/org.goldenglass.dock"
  [plasma/kwin/scripts/org.goldenglass.shortcuts]="$DATA/kwin/scripts/org.goldenglass.shortcuts"
  [build/wallpapers/GoldenGlass]="$DATA/wallpapers/GoldenGlass"
  [build/cursors/GoldenGlass-cursors]="$DATA/icons/GoldenGlass-cursors"
  [build/icons/GoldenGlass]="$DATA/icons/GoldenGlass"
  [build/icons/GoldenGlass-Dark]="$DATA/icons/GoldenGlass-Dark"
  [build/gtk/GoldenGlass]="$DATA/themes/GoldenGlass"
  [build/gtk/GoldenGlass-Dark]="$DATA/themes/GoldenGlass-Dark"
  [build/gtk/libadwaita.css]="$DATA/goldenglass/gtk/libadwaita.css"
  [build/sounds/GoldenGlass]="$DATA/sounds/GoldenGlass"
  [assets/logo/goldenglass.svg]="$DATA/icons/hicolor/scalable/apps/goldenglass.svg"
  [assets/logo/goldenglass-symbolic.svg]="$DATA/icons/hicolor/scalable/apps/goldenglass-symbolic.svg"
)

mode=copy
case "${1:-}" in
  --dev) mode=link ;;
  --uninstall) mode=uninstall ;;
  "") ;;
  *) echo "uso: $0 [--dev|--uninstall]" >&2; exit 2 ;;
esac

refresh_caches() {
  fc-cache -f >/dev/null
  command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
}

AUTOSTART="$CONF/autostart/goldenglass-gtk-sync.desktop"
SYSTEM_BIN="$HOME/.local/bin/goldenglass-system"
DOCK_BIN="$HOME/.local/bin/goldenglass-dock"

if [[ $mode == uninstall ]]; then
  pkill -u "$USER" -f "$ROOT/tools/gtk_sync.py" 2>/dev/null || true
  python3 "$ROOT/tools/gtk_sync.py" --restore 2>/dev/null || true
  rm -fv -- "$AUTOSTART"
  # deja la configuración del usuario como estaba antes de goldenglass-system
  python3 "$ROOT/tools/system.py" disable sounds chime || true
  rm -fv -- "$SYSTEM_BIN" "$DOCK_BIN"
  for dst in "${TARGETS[@]}"; do
    [[ -e $dst || -L $dst ]] && rm -rfv -- "$dst"
  done
  refresh_caches
  exit 0
fi

echo "Generando desde tokens…"
python3 "$ROOT/tools/gen_tokens.py" >/dev/null

echo "Instalando ($mode)…"
for src in "${!TARGETS[@]}"; do
  dst="${TARGETS[$src]}"
  mkdir -p -- "$(dirname -- "$dst")"
  [[ -e $dst || -L $dst ]] && rm -rf -- "$dst"
  if [[ $mode == link ]]; then
    ln -sfnv -- "$ROOT/$src" "$dst"
  elif [[ -d $ROOT/$src ]]; then
    cp -rv -- "$ROOT/$src" "$dst" | tail -1
  else
    install -Dm644 -v -- "$ROOT/$src" "$dst"
  fi
done

# GTK: el Global Theme no puede fijarlo; goldenglass-gtk-sync lo aplica mientras
# el Global Theme sea GoldenGlass (arranca con la sesión).
mkdir -p -- "$(dirname -- "$AUTOSTART")"
cat >"$AUTOSTART" <<EOF
[Desktop Entry]
Type=Application
Name=GoldenGlass GTK sync
Comment=Applies the GoldenGlass GTK theme while the GoldenGlass global theme is active
Exec=python3 "$ROOT/tools/gtk_sync.py"
OnlyShowIn=KDE;
X-KDE-autostart-phase=1
NoDisplay=true
EOF
python3 "$ROOT/tools/gtk_sync.py" --once || true

# goldenglass-system (sonidos, chime): lo usa el módulo «Efectos de sonido».
# No activa nada: `goldenglass-system enable sounds chime`.
mkdir -p -- "$(dirname -- "$SYSTEM_BIN")"
cat >"$SYSTEM_BIN" <<EOF
#!/bin/sh
exec python3 "$ROOT/tools/system.py" "\$@"
EOF
chmod 755 "$SYSTEM_BIN"
# goldenglass-dock (ajustes del dock en vivo): lo usa el módulo «Dock».
cat >"$DOCK_BIN" <<EOF
#!/bin/sh
exec python3 "$ROOT/tools/dock.py" "\$@"
EOF
chmod 755 "$DOCK_BIN"

# Apps de terceros encerradas en squircle a partir de sus iconos instalados.
# (Volver a ejecutar tools/wrap_icons.py al instalar apps nuevas.)
python3 "$ROOT/tools/wrap_icons.py" || echo "Aviso: no se pudieron encerrar los iconos de terceros" >&2

refresh_caches
echo "Listo. Aplicar: plasma-apply-lookandfeel -a org.goldenglass.light.desktop (o .dark.desktop)"
