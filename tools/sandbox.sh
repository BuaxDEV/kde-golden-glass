#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Prueba GoldenGlass en una sesión Plasma aislada y sin ventana (KWin virtual),
# con DBus privado y todos los directorios XDG en build/sandbox/home. No toca la
# configuración ni la sesión del usuario.
#
#   tools/sandbox.sh [light|dark]
#   GG_SANDBOX_APP=dolphin tools/sandbox.sh   # app para la captura «app» (por defecto systemsettings)
#   GG_SANDBOX_HOOK=script.sh tools/sandbox.sh  # script propio dentro de la sesión (OUT, VARIANT, ROOT)
#
# Deja capturas en build/sandbox/: desktop, app, spotlight, lockscreen,
# lockscreen-ui y splash. El estilo y la decoración se compilan desde build/cmake.
# El registro completo de la sesión queda en build/sandbox/session.log.
#
# Aislamiento:
#  - El entorno XDG del sandbox se exporta ANTES de crear el bus privado: el
#    dbus-daemon y todo servicio que active (kded6, kactivitymanagerd, portales…)
#    lo heredan y nunca usan la configuración real.
#  - Los servicios que saldrían de la máquina (KDE Connect, OBEX) se sustituyen
#    por /bin/false en el bus privado.
#  - Los lanzadores que instala tools/install.sh (goldenglass-system, goldenglass-dock)
#    van a GOLDENGLASS_BIN_DIR, dentro del sandbox, que se añade al PATH: el HOME
#    real no recibe ningún archivo.
#  - Cada ejecución marca su entorno con GG_SANDBOX_ID; al terminar se cierran
#    todos los procesos con esa marca (los servicios activados sobreviven al bus).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VARIANT="${1:-light}"
OUT="$ROOT/build/sandbox"
HOME_DIR="$OUT/home"
WIDTH=1600
HEIGHT=1000

case "$VARIANT" in light|dark) ;; *) echo "uso: $0 [light|dark]" >&2; exit 2 ;; esac

log() { printf '[sandbox] %s\n' "$*"; }

# Cierra todos los procesos del usuario marcados con este GG_SANDBOX_ID.
reap() {
  local id=$1 sig pid
  for sig in TERM TERM KILL; do
    for pid in $(pgrep -u "$USER"); do
      [[ $pid == "$$" ]] && continue
      if { tr '\0' '\n' <"/proc/$pid/environ"; } 2>/dev/null | grep -qx "GG_SANDBOX_ID=$id"; then
        kill "-$sig" "$pid" 2>/dev/null || true
      fi
    done
    sleep 1
  done
}

# --- Proceso externo: prepara el entorno, lanza el bus privado y limpia --------
if [[ -z ${GG_SANDBOX_INNER:-} ]]; then
  rm -rf -- "$HOME_DIR"
  mkdir -p -- "$OUT" "$HOME_DIR"/{config,data,cache,state}

  export GG_SANDBOX_ID="goldenglass-$$-$RANDOM"
  export XDG_CONFIG_HOME="$HOME_DIR/config" XDG_DATA_HOME="$HOME_DIR/data"
  export XDG_CACHE_HOME="$HOME_DIR/cache" XDG_STATE_HOME="$HOME_DIR/state"
  # Como startplasma: los defaults del Global Theme se leen de kdedefaults/.
  export XDG_CONFIG_DIRS="$XDG_CONFIG_HOME/kdedefaults:${XDG_CONFIG_DIRS:-/etc/xdg}"
  # libXcursor busca en ~/.local/share/icons (HOME real), no en XDG_DATA_HOME.
  # Lanzadores de install.sh dentro del sandbox (no en ~/.local/bin del HOME real).
  export GOLDENGLASS_BIN_DIR="$HOME_DIR/bin"
  mkdir -p -- "$GOLDENGLASS_BIN_DIR"
  export PATH="$GOLDENGLASS_BIN_DIR:$PATH"
  export XCURSOR_PATH="$XDG_DATA_HOME/icons:/usr/share/icons:/usr/share/pixmaps"
  export XDG_CURRENT_DESKTOP=KDE KDE_FULL_SESSION=true KDE_SESSION_VERSION=6
  # Directorio de sockets propio (ruta corta: los sockets Unix admiten ~108
  # caracteres): los servicios no ven los de la sesión real (PipeWire, portales…).
  XDG_RUNTIME_DIR="$(mktemp -d /tmp/gg-runtime.XXXXXX)"
  export XDG_RUNTIME_DIR
  unset WAYLAND_DISPLAY DISPLAY DBUS_SESSION_BUS_ADDRESS

  # Estilo y decoración (C++) desde el árbol de compilación, instalados en una
  # carpeta del sandbox con DESTDIR: no se toca /usr. KWin y las apps Qt cargan
  # plugins de QT_PLUGIN_PATH.
  STAGE="$HOME_DIR/stage"
  if [[ ! -f $ROOT/build/cmake/CMakeCache.txt ]]; then
    cmake -S "$ROOT" -B "$ROOT/build/cmake" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DCMAKE_INSTALL_PREFIX=/usr >/dev/null
  fi
  cmake --build "$ROOT/build/cmake" >"$OUT/build.log" 2>&1 \
    || { log "FALLO compilando build/cmake (ver build/sandbox/build.log)"; exit 1; }
  DESTDIR="$STAGE" cmake --install "$ROOT/build/cmake" >/dev/null
  export QT_PLUGIN_PATH="$STAGE/usr/lib/qt6/plugins${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
  # the org.goldenglass.glass QML module of this tree, not an older installed one
  export QML_IMPORT_PATH="$STAGE/usr/lib/qt6/qml${QML_IMPORT_PATH:+:$QML_IMPORT_PATH}"
  export XDG_DATA_DIRS="$STAGE/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
  export PATH="$STAGE/usr/bin:$PATH"

  # El bus de sesión busca servicios primero en $XDG_DATA_HOME/dbus-1/services.
  mkdir -p -- "$XDG_DATA_HOME/dbus-1/services"
  for svc in org.kde.kdeconnect org.bluez.obex; do
    printf '[D-BUS Service]\nName=%s\nExec=/bin/false\n' "$svc" \
      >"$XDG_DATA_HOME/dbus-1/services/$svc.service"
  done

  trap 'reap "$GG_SANDBOX_ID"; rm -rf -- "$XDG_RUNTIME_DIR"' EXIT
  status=0
  dbus-run-session -- env GG_SANDBOX_INNER=1 "$0" "$@" </dev/null >"$OUT/session.log" 2>&1 || status=$?
  grep '^\[sandbox\]' "$OUT/session.log" || true
  exit "$status"
fi

# --- Proceso interno: dentro del bus privado ---------------------------------
shot() {
  if timeout 20 spectacle -b -n -f -o "$OUT/$1-$VARIANT.png" >/dev/null 2>&1; then
    log "captura: build/sandbox/$1-$VARIANT.png"
  else
    log "FALLO captura: $1"
  fi
}
dbus() { timeout 5 qdbus6 "$@" >/dev/null 2>&1 || log "FALLO dbus: $*"; }

log "instalando en el sandbox"
"$ROOT/tools/install.sh" >/dev/null

# Copia de la pantalla de bloqueo con la UI siempre visible, para capturar el
# campo de contraseña sin simular entrada.
LOCK_UI="$XDG_DATA_HOME/plasma/shells/org.goldenglass.desktop-ui"
rm -rf -- "$LOCK_UI"
cp -r -- "$ROOT/build/plasma/shells/org.goldenglass.desktop" "$LOCK_UI"
sed -i 's/"Id": "org.goldenglass.desktop"/"Id": "org.goldenglass.desktop-ui"/' "$LOCK_UI/metadata.json"
sed -i 's/property bool uiVisible: false/property bool uiVisible: true/' "$LOCK_UI/contents/lockscreen/LockScreenUi.qml"

# Antes de KWin, como al iniciar sesión: KWin lee la decoración al arrancar.
# --resetLayout aplica también los ajustes de disposición (shell, botones).
log "aplicando org.goldenglass.$VARIANT.desktop"
QT_QPA_PLATFORM=offscreen plasma-apply-lookandfeel -a "org.goldenglass.$VARIANT.desktop" --resetLayout || true

SOCK="goldenglass-sandbox-$$"
log "arrancando KWin virtual ${WIDTH}x${HEIGHT}"
kwin_wayland --virtual --width "$WIDTH" --height "$HEIGHT" --socket "$SOCK" --no-lockscreen &
for _ in $(seq 100); do [[ -S $XDG_RUNTIME_DIR/$SOCK ]] && break; sleep 0.1; done
[[ -S $XDG_RUNTIME_DIR/$SOCK ]] || { log "KWin no arrancó (ver build/sandbox/session.log)"; exit 1; }
export WAYLAND_DISPLAY="$SOCK" QT_QPA_PLATFORM=wayland
# Como startplasma: los servicios que active el bus desde ahora usan esta
# pantalla (sin esto abortan, o usarían la de la sesión real).
dbus-update-activation-environment WAYLAND_DISPLAY QT_QPA_PLATFORM

log "arrancando plasmashell"
plasmashell --no-respawn &
sleep 12
shot desktop

# Gancho para experimentos: un script que se ejecuta dentro de la sesión con
# OUT, VARIANT y ROOT disponibles (por ejemplo, para medir recargas del tema).
if [[ -n ${GG_SANDBOX_HOOK:-} ]]; then
  log "gancho: $GG_SANDBOX_HOOK"
  OUT="$OUT" VARIANT="$VARIANT" ROOT="$ROOT" bash "$GG_SANDBOX_HOOK" || log "FALLO gancho"
fi

log "abriendo una aplicación (estilo + decoración): ${GG_SANDBOX_APP:-systemsettings}"
${GG_SANDBOX_APP:-systemsettings} &
app=$!
sleep 6
shot app
# Qué cargó KWin de verdad (plugin de decoración, efectos…).
timeout 5 qdbus6 org.kde.KWin /KWin supportInformation >"$OUT/kwin-support-$VARIANT.txt" 2>&1 \
  || log "FALLO dbus: supportInformation"
kill "$app" 2>/dev/null || true

log "abriendo Spotlight (KRunner)"
krunner &
sleep 3
dbus org.kde.krunner /App org.kde.krunner.App.query "konsole"
sleep 3
shot spotlight
dbus org.kde.krunner /App org.kde.krunner.App.toggleDisplay

log "pantalla de bloqueo (modo prueba)"
/usr/lib/kscreenlocker_greet --testing &
lock=$!
sleep 6
shot lockscreen
kill "$lock" 2>/dev/null || true

log "pantalla de bloqueo con la UI visible"
/usr/lib/kscreenlocker_greet --testing --shell org.goldenglass.desktop-ui &
lock=$!
sleep 6
shot lockscreen-ui
kill "$lock" 2>/dev/null || true

log "splash"
ksplashqml "org.goldenglass.$VARIANT.desktop" --test &
splash=$!
sleep 4
shot splash
kill "$splash" 2>/dev/null || true

log "hecho"
