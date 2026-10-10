# GoldenGlass — Arquitectura

Tema completo para KDE Plasma en CachyOS inspirado en macOS 27 "Golden Gate"
(refinamiento de Liquid Glass presentado en WWDC 2026, publicado el 14/09/2026).

## 1. Objetivos

- Fidelidad **alta** a macOS: barra de menús superior con menú global, dock
  centrado, semáforos a la izquierda, Spotlight, Launchpad, Centro de control.
- Variantes **clara, oscura y automática** (día/noche).
- Replicar el **slider de transparencia** de macOS 27 como módulo de Ajustes.
- Distribuible en CachyOS/Arch mediante PKGBUILD.

### Referencia visual (macOS 27 Golden Gate)

| Rasgo | Detalle | Dónde se implementa |
|---|---|---|
| Slider de vidrio | 3 muescas (más claro / medio por defecto / más opaco) + valores intermedios; afecta dock, widgets, sidebars, toolbars y sus botones | `kcm/` + todos los consumidores de tokens |
| Menos transparencia por defecto | Más contraste y legibilidad que Tahoe | `tokens/` (nivel medio) |
| Esquinas de ventana | Radio más cerrado que Tahoe y uniforme en todas las apps | `kdecoration/`, `kstyle/` |
| Semáforos | Sombreado tipo vidrio ("candy-like", eco de Aqua) | `kdecoration/` |
| Sidebars | Pegadas al borde izquierdo (no flotantes), fondo más oscuro, iconos a color | `kstyle/` |
| Toolbars | Barras reales y uniformes, no botones flotantes | `kstyle/` + `kdecoration/` |
| Menús | Sin iconos junto a cada comando | `kstyle/` |
| Barra de menús | Desbordamiento de iconos tras un chevron «»; fondo translúcido opcional | `plasma/desktoptheme`, layout |
| Iconos de app | Squircle con capas y más detalle | `icons/` |

Fuentes: Six Colors (review), 9to5Mac (slider de Liquid Glass), Digital Trends,
Wccftech. Los valores numéricos exactos (radios, opacidades) no están publicados:
los tokens parten de valores iniciales que se calibran contra capturas.

## 2. Plataforma soportada

- **Plasma ≥ 6.7, solo Wayland.** Qt 6. Sin soporte X11.
- Desarrollo sobre CachyOS (Plasma 6.7.5, Qt 6.12, KWin 6.7.5).

## 3. Principio rector: tokens de diseño como única fuente de verdad

Todos los valores visuales (paleta clara/oscura, radios, niveles de vidrio, blur,
sombras, tipografía, semáforos) viven en **`tokens/goldenglass.toml`**.
`tools/gen_tokens.py` genera a partir de ahí, en **`build/`** (no versionado):

| Salida | Consumidor | Estado |
|---|---|---|
| `build/color-schemes/*.colors` | Plasma / KColorScheme (todas las apps KDE) | ✅ F0 |
| `build/tokens.json` | KCM y plasmoids QML | ✅ F0 |
| `goldenglass_tokens.h` | QStyle y KDecoration (valores por defecto) | F1 |
| `build/plasma/desktoptheme/GoldenGlass/` (SVG dibujados por código) | Plasma Style | ✅ F2 |
| `build/plasma/look-and-feel/org.goldenglass.{light,dark}.desktop/` | Global Themes (desde `plasma/look-and-feel/common/`) | ✅ F2 |
| `gtk/*.css` | GTK3 / GTK4 | F6 |

**Regla:** los archivos generados no se editan a mano ni se versionan. Se cambia
el token y se regenera (`install.sh` y el PKGBUILD lo hacen solos).

## 4. Componentes

```
goldenglass/
├── tokens/              # goldenglass.toml
├── tools/               # gen_tokens.py (+ plasma_theme.py, lookandfeel.py), install.sh,
│                        # preview_plasma.py (vista previa), sandbox.sh (sesión aislada)
├── assets/logo/         # logo GoldenGlass (símbolo monocromo y versión a color)
├── kstyle/              # QStyle C++ (fork de Darkly) → goldenglass6.so
├── kdecoration/         # Plugin KDecoration3
├── kcm/                 # Módulo de Ajustes "GoldenGlass"
├── plasma/
│   ├── look-and-feel/   # plantilla común de los Global Themes (layout, splash)
│   ├── shell/           # shell org.goldenglass.desktop (pantalla de bloqueo)
│   └── plasmoids/       # Centro de control, Launchpad, menú de sistema
├── gtk/                 # (generado en parte)
├── icons/               # GoldenGlass + GoldenGlass-Dark
├── cursors/             # SVG fuente → xcursor + cursores SVG
├── wallpapers/          # variantes claro/oscuro
├── fontconfig/          # alias de familias tipográficas
├── packaging/           # PKGBUILD dividido
├── docs/
└── build/               # salidas generadas (no versionado)
```

### 4.1 Estilo de aplicaciones — `kstyle/` (C++)
- **Fork de [Darkly](https://github.com/Bali10050/darkly)** v0.5.40 (GPL-2.0-or-later →
  publicado como GPL-3.0-or-later). Renombrado completo; tabla de equivalencias
  en `UPSTREAM.md`. Identificadores: estilo `GoldenGlass` (`goldenglass6.so`),
  decoración `org.goldenglass.decoration`, config `goldenglassrc`, app
  `goldenglass-settings`, señal D-Bus `org.goldenglass.Style`. No choca con un
  Darkly instalado: ambos pueden convivir.
- Darkly ya aporta transparencia y blur por ventana. Se añade: sidebars de borde
  a borde con fondo más oscuro, toolbar unificada con la barra de título, menús
  sin iconos, controles con radios de los tokens.
- Lee `~/.config/goldenglassrc` y reacciona en vivo (KConfigWatcher) a los
  cambios del slider.
- Las apps Kirigami/QML lo heredan vía `qqc2-desktop-style`.

### 4.2 Decoración de ventanas — `kdecoration/` (C++, KDecoration3)
- En el mismo árbol CMake que `kstyle/` (como Breeze/Darkly), config compartida.
- Semáforos a la izquierda con sombreado de vidrio, símbolos al pasar el ratón,
  estado inactivo gris.
- Radio de esquina y sombras desde los tokens. Barra de título fundida con la
  toolbar (mismo color/opacidad que el header del estilo).

### 4.3 Efecto de vidrio
- **Blur nativo de KWin + superficies semitransparentes.** Sin efecto KWin propio
  ni dependencias de terceros. Sin refracción.
- La opacidad de cada superficie sale del nivel de vidrio activo.

### 4.4 Módulo de Ajustes — `kcm/` (C++ + QML)
- Aparece en Preferencias del Sistema › Apariencia › GoldenGlass.
- **Slider de vidrio** continuo con 3 muescas; vista previa en vivo.
- Selector de acento: "Sistema" (por defecto, respeta el acento de Plasma).
- Escribe `~/.config/goldenglassrc`. Consumidores:
  - `kstyle/` y `kdecoration/`: recarga en vivo.
  - Plasma Style: **⚠ riesgo** — los SVG tienen opacidad fija. Plan: regenerar el
    tema desde plantillas en `~/.local/share/plasma/desktoptheme/GoldenGlass` y
    forzar la recarga de Plasma. **Se valida con un spike antes de F3.**

### 4.5 Escritorio Plasma — `plasma/`
- **Plasma Style** `GoldenGlass`: lo genera `tools/plasma_theme.py` dibujando
  cada pieza de FrameSvg por código (esquinas, bordes, máscara de blur, sombra).
  Usa clases `ColorScheme-*`, así que **un solo Plasma Style sirve para claro y
  oscuro**; solo la opacidad queda fija en el SVG. Genera diálogos, panel (barra
  de menús y dock), tooltips, fondo de widgets, tareas del dock (punto bajo las
  apps abiertas), resaltado de listas, campos de texto y cabeceras de popups. Lo
  que no genera se hereda de Breeze. `plasmarc` pide saturación extra detrás del
  blur ("vibrancy").
- **Global Themes** (`look-and-feel/`): `org.goldenglass.light.desktop` y
  `org.goldenglass.dark.desktop`. Incluyen:
  - Script de layout: panel superior (menú de sistema, menú global, bandeja,
    reloj) + **dock** = panel nativo flotante centrado con gestor de tareas solo
    iconos (sin magnificación).
  - Splash de inicio (logo + barra de progreso).
  - Fuentes, esquema de color, Plasma Style, estilo de apps `GoldenGlass` y
    decoración `org.goldenglass.decoration` (requieren el paquete
    `goldenglass-kstyle`; sin él Plasma usa Breeze).
  - Botones de ventana a la izquierda (`ButtonsOnLeft=XIA`) en
    `contents/layouts/defaults`: KLookAndFeelManager solo lee de ahí los ajustes
    de disposición de KWin, no de `contents/defaults`.
  - `ShellPackage=org.goldenglass.desktop` (ver pantalla de bloqueo).
  - Iconos, cursores y wallpaper se añaden en F5.
- **Pantalla de bloqueo** estilo macOS (reloj grande arriba, avatar y contraseña
  abajo). Desde Plasma 6 vive en el **paquete de shell**, no en el Global Theme:
  - `plasma/shell/org.goldenglass.desktop` solo trae `lockscreen/` y hereda el
    resto de `org.kde.plasma.desktop` (`X-Plasma-FallbackPackage`).
  - `lockscreen/` es la de plasma-desktop 6.7.5 con cambios mínimos (ver
    `UPSTREAM.md`).
  - Efecto: plasmashell guarda el layout en
    `plasma-org.goldenglass.desktop-appletsrc`. El layout previo del usuario no se
    toca y vuelve si regresa a Breeze. Por eso el Global Theme trae el layout con
    los dos nombres (`org.kde.plasma.desktop-layout.js` y
    `org.goldenglass.desktop-layout.js`).
  - El shell y los botones solo se aplican con "Disposición del escritorio y
    ventanas" (`plasma-apply-lookandfeel --resetLayout`).
- **Spotlight:** KRunner flotante y centrado (`krunnerrc FreeFloating=true`,
  escrito por el script de layout), estilizado por el Plasma Style.
- **Plasmoids propios** (`plasmoids/`):
  - `org.goldenglass.controlcenter` — Wi-Fi, Bluetooth, sonido, brillo, modo
    oscuro, slider de vidrio.
  - `org.goldenglass.launchpad` — cuadrícula de apps a pantalla completa con blur.
  - `org.goldenglass.systemmenu` — menú del "logo" (Acerca de, Ajustes, Suspender,
    Reiniciar, Apagar, Bloquear, Cerrar sesión).
- **Modo automático:** se apoya en el cambio día/noche nativo de Plasma entre los
  dos Global Themes. Los wallpapers usan `images_dark/` para cambiar solos.

### 4.6 Tipografía — `fontconfig/`
- SF Pro **no se redistribuye** (licencia de Apple).
- Alias de fontconfig `GoldenGlass Sans` → SF Pro → SF Pro Text → Inter, y
  `GoldenGlass Mono` → SF Mono → JetBrains Mono → Hack.
- KDE se configura siempre con el alias. Si el usuario instala SF Pro por su
  cuenta se usa; si no, Inter.
- **⚠ A verificar en F0:** que Qt resuelva un alias sin familia real en el
  selector de fuentes de KDE. Plan B: el Global Theme escribe la familia concreta
  detectada al aplicarse.

### 4.7 Iconos, cursores y wallpapers
- **Iconos:** diseño propio de carpetas, lugares, sistema, acciones y ~50 apps
  más usadas (squircle con capas). Hereda (`Inherits=`) de **WhiteSur** (AUR).
- **Cursores:** propios, estilo macOS, fuente SVG → xcursor + cursores SVG de
  Plasma 6 (nítidos a cualquier escala).
- **Wallpapers:** originales generados por nosotros (no el de Apple), con
  variante día/noche.
- **Acento:** azul macOS por defecto (`#007AFF` claro / `#0A84FF` oscuro),
  sobreescribible por el acento del sistema.

### 4.8 GTK — `gtk/`
- GTK3: tema completo generado desde tokens.
- GTK4/libadwaita: **solo colores** vía `~/.config/gtk-4.0/gtk.css` (libadwaita no
  admite temas oficialmente). Limitación aceptada.

## 5. Distribución

- Ya existe `packaging/goldenglass-kstyle/PKGBUILD` (estilo + decoración + KCMs,
  compila desde el repo local). El resto (Plasma, iconos…) se instala de momento
  con `tools/install.sh`.
- **PKGBUILD dividido** (`packaging/`) para AUR/CachyOS:
  `goldenglass-kstyle` (estilo + decoración + KCM, compilado),
  `goldenglass-plasma`, `goldenglass-icons`, `goldenglass-cursors`,
  `goldenglass-wallpapers`, `goldenglass-gtk` y el metapaquete `goldenglass`.
  Las partes C++ deben recompilarse con cada actualización de Qt/KDE.
- **`tools/install.sh`** para desarrollo: instala en `~/.local` sin empaquetar.
  `--dev` crea symlinks para iterar sin reinstalar.
- KDE Store: opcional y posterior, solo para partes no compiladas.

## 6. Repositorio y licencias

- Monorepo en GitHub.
- Código: **GPL-3.0-or-later**. Assets gráficos (iconos, cursores, wallpapers,
  SVG): **CC-BY-SA-4.0**.
- No se incluye ningún asset, fuente ni marca de Apple. El nombre del proyecto
  evita "macOS"/"Apple".

## 7. Fases

| Fase | Contenido | Estado |
|---|---|---|
| F0 | Repo, tokens, generador, color schemes, fontconfig, `install.sh` | ✅ |
| F1 | Fork de Darkly renombrado: QStyle + decoración (semáforos, radios, sidebar, toolbar unificada) | en curso (importado y renombrado) |
| F2 | Plasma Style, Global Themes, layout (barra superior + dock), Spotlight, pantalla de bloqueo | ✅ |
| F3 | Spike de opacidad del Plasma Style → KCM completo | pendiente |
| F4 | Plasmoids: Centro de control, Launchpad, menú de sistema | pendiente |
| F5 | Iconos, cursores, wallpapers | pendiente |
| F6 | GTK, PKGBUILD, CI en GitHub | pendiente |

## 8. Fuera de alcance

SDDM, Plymouth, sonidos del sistema, dock con magnificación, efecto KWin propio
con refracción, X11 y Plasma < 6.7.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| Opacidad del Plasma Style no ajustable en vivo | Spike en F3; plan B: 3 sub-temas fijos (claro/medio/opaco) |
| Divergencia del fork de Darkly respecto a upstream | Renombrado limpio y registro de cambios propios para poder hacer rebase |
| Roturas por actualizaciones de Qt/KDE (rolling) | PKGBUILD con rebuild; CI contra la versión actual de Arch |
| Alias de fuente no resuelto por Qt | Plan B descrito en 4.6 |
| libadwaita ignora temas | Solo colores; documentado |
| Plasma limita la altura de cada panel a la suma de las esquinas de `panel-background` (barra y dock comparten SVG) | `radius.dock ≤ menubar_height / 2` (14 px); el generador lo valida |
