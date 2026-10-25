#!/bin/sh
# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# El goldenglass-glass de prueba (tests/bin) solo cambia [Glass] Level: no
# borra [Accessibility] ni ningún otro grupo de goldenglassrc (R8 de
# docs/MACOS27-PLAN.md). Uso (ctest): goldenglass_glass_stub_test.sh RUTA_AL_STUB
set -eu
stub=${1:?uso: goldenglass_glass_stub_test.sh RUTA_AL_STUB}
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
export XDG_CONFIG_HOME="$dir"
rc="$dir/goldenglassrc"
fail=0

check() { # descripción, contenido esperado
  if [ "$(cat "$rc")" != "$2" ]; then
    printf 'FALLO: %s\n--- esperado\n%s\n--- obtenido\n%s\n' "$1" "$2" "$(cat "$rc")"
    fail=1
  fi
}

# sin archivo: lo crea con el grupo
"$stub" --level 0.25
check "archivo nuevo" "[Glass]
Level=0.25"

# con otros grupos: solo cambia Level, en su sitio
cat >"$rc" <<'EOF'
[Accessibility]
ReduceMotion=true
ShowBorders=true

[Glass]
Level=0.1
Refraction=true

[Plasma]
MenubarBackground=false
EOF
"$stub" --level 0.75
check "grupo existente" "[Accessibility]
ReduceMotion=true
ShowBorders=true

[Glass]
Level=0.75
Refraction=true

[Plasma]
MenubarBackground=false"

# [Glass] sin Level, en medio, y una clave que empieza igual (LevelX)
cat >"$rc" <<'EOF'
[Glass]
LevelX=1
[Accessibility]
ReduceTransparency=true
EOF
"$stub" --level 0.5
check "clave nueva en un grupo existente" "[Glass]
LevelX=1
Level=0.5
[Accessibility]
ReduceTransparency=true"

# sin [Glass]: lo añade al final
printf '[Accessibility]\nShowBorders=true\n' >"$rc"
"$stub" --level 1
check "grupo nuevo" "[Accessibility]
ShowBorders=true

[Glass]
Level=1"

# «Reduce transparency» only touches its own key
printf '[Accessibility]\nReduceMotion=true\n[Glass]\nLevel=0.4\n' >"$rc"
"$stub" --reduce-transparency on
check "reduce transparency" "[Accessibility]
ReduceMotion=true
ReduceTransparency=true
[Glass]
Level=0.4"
"$stub" --reduce-transparency off
check "reduce transparency off" "[Accessibility]
ReduceMotion=true
ReduceTransparency=false
[Glass]
Level=0.4"

# «Show borders» only touches its own key
"$stub" --show-borders on
check "show borders" "[Accessibility]
ReduceMotion=true
ReduceTransparency=false
ShowBorders=true
[Glass]
Level=0.4"
"$stub" --show-borders off
check "show borders off" "[Accessibility]
ReduceMotion=true
ReduceTransparency=false
ShowBorders=false
[Glass]
Level=0.4"

# a bad value fails without touching the file
if "$stub" --show-borders maybe 2>/dev/null; then
  echo "FALLO: --show-borders maybe was accepted"
  fail=1
fi
check "show borders bad value" "[Accessibility]
ReduceMotion=true
ReduceTransparency=false
ShowBorders=false
[Glass]
Level=0.4"

# no quedan temporales
if [ "$(find "$dir" -mindepth 1 | wc -l)" -ne 1 ]; then
  echo "FALLO: archivos de más en XDG_CONFIG_HOME: $(ls -A "$dir")"
  fail=1
fi

[ "$fail" -eq 0 ] && echo OK
exit "$fail"
