<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Contribuir a GoldenGlass

¡Gracias por tu interés! Antes de empezar lee [AGENTS.md](AGENTS.md) (reglas de
ramas y commits) y [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Flujo

1. Haz un fork y crea una rama desde `main` con prefijo `feature/`, `task/` o
   `fix/` (inglés, kebab-case).
2. Commits en inglés y firmados con DCO (`git commit -s`, ver abajo).
3. Abre un PR hacia `main`. La CI (compilación, pruebas, paquetes, REUSE,
   gitleaks y DCO) debe pasar y el mantenedor debe aprobarlo.

Para cambios grandes abre antes un issue para acordar el enfoque.

## Developer Certificate of Origin (DCO)

Cada commit debe terminar con una línea

    Signed-off-by: Tu Nombre <tu@correo>

con el mismo correo que el autor del commit (`git commit -s` la añade). Con ella
certificas el [Developer Certificate of Origin 1.1](https://developercertificate.org/):
que escribiste el cambio o tienes derecho a enviarlo bajo la licencia del
proyecto. Para corregir commits sin firmar: `git rebase --signoff main`.

## Licencias

- Todo aporte se publica bajo la licencia del archivo que modifica: el código
  propio es **GPL-3.0-or-later** y los assets gráficos **CC-BY-SA-4.0**. Las
  partes de upstream conservan la suya (ver [UPSTREAM.md](UPSTREAM.md) y
  [REUSE.toml](REUSE.toml)).
- Archivos nuevos: cabecera SPDX al inicio, por ejemplo

      # SPDX-FileCopyrightText: 2026 GoldenGlass contributors
      # SPDX-License-Identifier: GPL-3.0-or-later

  Comprobar con `reuse lint` ([reuse](https://reuse.software)) y
  `tools/check_spdx.sh main`: `REUSE.toml` da una licencia por defecto a todo,
  así que `reuse lint` no avisa de un archivo nuevo sin cabecera; la CI lo
  comprueba en cada PR.
- No se aceptan assets, fuentes, iconos ni sonidos de Apple u otros productos
  propietarios, ni material copiado sin una licencia compatible.

## Desarrollo

- Todo valor visual va en `tokens/goldenglass.toml`; `build/` es generado.
- Una vez por clon: `tools/setup-git.sh`.
- Pruebas C++ de `qmlplugin/` (ctest, `-DBUILD_TESTING=ON`): copia una de
  `qmlplugin/tests/*_test.cpp`, usa `GOLDENGLASS_TEST_MAIN(Clase)` de
  `testbus.h` (aísla HOME y XDG_*; obligatorio, nunca se toca tu
  configuración) y regístrala al final de `qmlplugin/tests/CMakeLists.txt`
  con `goldenglass_add_qmlplugin_test(nombre [SOURCES ...] [LIBS ...] [DBUS])`.
  Si necesita D-Bus (servicios falsos con `GoldenGlassTest::FakeService`),
  añade `DBUS` y empieza con `GG_REQUIRE_SESSION_BUS()`: ctest la ejecuta bajo
  `dbus-run-session` (paquete `dbus`) y, sin él, la omite. Nunca registres
  nombres en el bus de tu sesión. Detalles en
  [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- API privada de Plasma (`org.kde.*private*`, `org.kde.taskmanager`,
  `org.kde.notificationmanager`): al usar una nueva (módulo, tipo, propiedad,
  método, señal, valor de enum o rol de modelo), añádela en el mismo cambio a
  `tools/plasma_api.toml` (el formato está en su cabecera) y comprueba con
  `python3 tools/check_plasma_compat.py`. Un módulo privado que falte en el
  manifiesto hace fallar la CI.
- La CI completa en local:
  `podman run --rm -v "$PWD":/src:Z -w /src docker.io/library/archlinux:latest tools/ci.sh`.

## Seguridad

Las vulnerabilidades se reportan en privado: ver [SECURITY.md](SECURITY.md).
