# GoldenGlass

Tema completo para KDE Plasma (CachyOS) inspirado en el diseño de macOS 27
"Golden Gate": vidrio translúcido con nivel ajustable, barra de menús superior,
dock, semáforos, variantes clara/oscura/automática.

> Proyecto independiente. No contiene assets, fuentes ni marcas de Apple.

**Estado:** F0 (fundamentos). Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requisitos

- Plasma ≥ 6.7 en Wayland, Qt 6
- Python ≥ 3.11 (generador de tokens)
- Recomendado: `inter-font` (fuente de respaldo si no tienes SF Pro)

## Desarrollo

```sh
python3 tools/gen_tokens.py      # regenera build/ desde tokens/goldenglass.toml
tools/install.sh --dev           # instala en ~/.local con symlinks
plasma-apply-colorscheme GoldenGlassLight
tools/install.sh --uninstall
```

Todo valor visual se cambia en `tokens/goldenglass.toml`, nunca en los archivos
generados.

## Licencia

Código: GPL-3.0-or-later. Assets gráficos: CC-BY-SA-4.0. Ver `LICENSES/`.
