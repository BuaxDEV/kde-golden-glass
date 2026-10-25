# AGENTS.md

Reglas para cualquier agente (humano o IA) que trabaje en este repositorio.

## Ramas

- **Vida larga:** solo `main`. No se crean otras ramas permanentes
  (`develop`, `release`, etc.).
- **Vida corta:** todo cambio se hace en una rama con uno de estos prefijos y se
  integra en `main`:
  | Prefijo | Uso |
  |---|---|
  | `feature/*` | Funcionalidad nueva |
  | `task/*` | Tareas sin funcionalidad nueva: configuración, docs, refactor, empaquetado |
  | `fix/*` | Corrección de errores |
- Nombres en inglés y kebab-case: `feature/traffic-light-glass`,
  `fix/header-inactive-color`, `task/pkgbuild-split`.
- No se hacen commits directos a `main`.
- La rama se elimina después de integrarse.

## Commits

- **Mensajes solo en inglés.**
- **Sin firmas ni atribuciones de IA:** prohibido `Co-Authored-By`,
  `Generated with`, ni ninguna mención a Claude, Anthropic, Copilot, ChatGPT,
  OpenAI u otra IA o herramienta de IA, en commits, PRs, tags o comentarios de
  código.
- El autor del commit es la identidad git configurada del desarrollador.
- **DCO:** todo commit lleva `Signed-off-by` del autor (`git commit -s`); la
  CI lo exige en los PRs. Ver [CONTRIBUTING.md](CONTRIBUTING.md).
- Archivos nuevos con cabecera SPDX; `reuse lint` debe pasar.

## Código

- **El código explica su intención por sí mismo:** nombres claros de
  variables, funciones y tipos, funciones pequeñas y constantes con nombre en
  vez de valores sueltos. Si hace falta un comentario para entender *qué* hace
  algo, primero se intenta reescribir el código.
- **Comentarios solo cuando son de verdad necesarios:** para el *porqué* que el
  código no puede expresar (un límite de Plasma/KWin/Qt, un error de upstream,
  una decisión no obvia, un riesgo de seguridad). No se comenta lo evidente ni
  se repite lo que dice el código.
- **Comentarios en inglés**, también los docstrings y los mensajes de log. Los
  comentarios existentes en español se traducen solo al modificar ese código;
  no se hacen cambios masivos de traducción.
- No se aplica a la documentación (`docs/`, `README.md`, `CHANGELOG.md`…) ni a
  los textos de la interfaz, que siguen su propio idioma y flujo de i18n.

## Proyecto

- Arquitectura y fases: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Todo valor visual se define en `tokens/goldenglass.toml`. Los archivos de
  `build/` son generados (`python3 tools/gen_tokens.py`): no se editan a mano ni
  se versionan.
- `packaging/goldenglass/PKGBUILD`: makepkg reescribe `pkgver=`; con
  `tools/setup-git.sh` git lo normaliza a `VERSION` (si `git status` lo marca,
  `git add` no incluye ningún cambio). No se commitea un `pkgver` de makepkg.
