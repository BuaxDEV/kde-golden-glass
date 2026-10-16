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

  Comprobar con `reuse lint` ([reuse](https://reuse.software)).
- No se aceptan assets, fuentes, iconos ni sonidos de Apple u otros productos
  propietarios, ni material copiado sin una licencia compatible.

## Desarrollo

- Todo valor visual va en `tokens/goldenglass.toml`; `build/` es generado.
- Una vez por clon: `tools/setup-git.sh`.
- La CI completa en local:
  `podman run --rm -v "$PWD":/src:Z -w /src docker.io/library/archlinux:latest tools/ci.sh`.

## Seguridad

Las vulnerabilidades se reportan en privado: ver [SECURITY.md](SECURITY.md).
