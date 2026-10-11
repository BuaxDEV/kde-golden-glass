# GoldenGlass

Tema completo para KDE Plasma (CachyOS) inspirado en el diseño de macOS 27
"Golden Gate": vidrio translúcido con nivel ajustable, barra de menús superior,
dock, semáforos, variantes clara/oscura/automática.

> Proyecto independiente. No contiene assets, fuentes ni marcas de Apple.

**Estado:** F0–F4 completas; F5 en curso (fondos, cursores e iconos base listos; faltan iconos de archivos y apps). Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requisitos

- Plasma ≥ 6.7 en Wayland, Qt 6
- Python ≥ 3.11 con numpy y Pillow (generador de tokens y del fondo de pantalla)
- Recomendado: `inter-font` (fuente de respaldo si no tienes SF Pro)

## Desarrollo

```sh
python3 tools/gen_tokens.py              # regenera build/ desde tokens/goldenglass.toml
python3 tools/preview_plasma.py          # vista previa del Plasma Style (build/preview-*.png, requiere PyQt6)
python3 tools/preview_style.py           # vista previa del estilo de apps compilado: menú y controles
tools/sandbox.sh light                   # sesión Plasma aislada y sin ventana → capturas en build/sandbox/
tools/install.sh --dev                   # instala en ~/.local con symlinks
plasma-apply-lookandfeel -a org.goldenglass.light.desktop --resetLayout
tools/install.sh --uninstall
```

Estilo de apps y decoración de ventanas (C++), con pacman:

```sh
cd packaging/goldenglass-kstyle && makepkg -si   # compila main (otra rama: GOLDENGLASS_BRANCH=… makepkg -si)
sudo pacman -R goldenglass-kstyle                # desinstalar
```

Requiere `extra-cmake-modules`. Volver a ejecutar `makepkg -si` tras actualizar
Qt o KDE.

Nivel de vidrio en vivo: Preferencias del Sistema › Colores y temas › Vidrio, o desde la terminal (requiere `goldenglass-kstyle` instalado):

```sh
goldenglass-glass --level 0.8   # 0 = más transparente, 1 = más opaco
goldenglass-glass --get
```

`--resetLayout` (o marcar "Disposición del escritorio y ventanas" al aplicar el
Global Theme) es necesario para la barra de menús, el dock, los botones de
ventana a la izquierda y la pantalla de bloqueo. Tu layout anterior no se borra:
vuelve al regresar a Breeze (ver `docs/ARCHITECTURE.md` §4.5).

`tools/sandbox.sh` no toca tu sesión: usa KWin virtual, un DBus privado y
directorios XDG propios en `build/sandbox/home`.

Todo valor visual se cambia en `tokens/goldenglass.toml`, nunca en los archivos
generados.

## Licencia

Código: GPL-3.0-or-later. Assets gráficos: CC-BY-SA-4.0. Ver `LICENSES/`.
