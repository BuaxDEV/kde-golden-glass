# Upstream

The C++ widget style (`kstyle/`), window decoration (`kdecoration/`) and
`libdarklycommon/` are a fork of **Darkly**, itself a fork of Lightly/Breeze.

| | |
|---|---|
| Project | https://github.com/Bali10050/darkly |
| License | GPL-2.0-or-later (redistributed here as GPL-3.0-or-later) |
| Base tag | `v0.5.40` |
| Base commit | `e60fae72c94e19118058ad9e4cc64d894f7d732a` |

Only `kstyle/`, `kdecoration/`, `libdarklycommon/`, `cmake/`, the root
`CMakeLists.txt` and its auxiliary files were imported. Upstream's Plasma
style, color scheme, Flatpak, Nix and install scripts were left out.

## Porting upstream changes

The import commit contains the base tag unmodified, so upstream changes can be
reviewed with:

```sh
git clone https://github.com/Bali10050/darkly /tmp/darkly
git -C /tmp/darkly diff e60fae72c94e19118058ad9e4cc64d894f7d732a <new-tag> -- kstyle kdecoration libdarklycommon
```

and ported by hand. Update the base tag/commit in this file after each port.

### Rename map (commit `9869361`)

| Darkly | GoldenGlass |
|---|---|
| `darkly*` files, `libdarklycommon/` | `goldenglass*`, `libgoldenglasscommon/` |
| namespace / classes `Darkly` | `GoldenGlass` |
| macros `DARKLY_*` | `GOLDENGLASS_*` |
| style key `Darkly` (`darkly6.so`) | `GoldenGlass` (`goldenglass6.so`) |
| config file `darklyrc` | `goldenglassrc` |
| decoration plugin `org.kde.darkly` | `org.goldenglass.decoration` |
| D-Bus `org.kde.Darkly.Style` | `org.goldenglass.Style` |
| `kcm_darklydecoration`, `darklystyleconfig` | `kcm_goldenglassdecoration`, `goldenglassstyleconfig` |
| `darkly-settings6` | `goldenglass-settings` |

To apply an upstream diff, rewrite it first:
`sed -e 's/org\.kde\.darkly/org.goldenglass.decoration/g; s/org\.kde\.Darkly\.Style/org.goldenglass.Style/g; s/DARKLY/GOLDENGLASS/g; s/Darkly/GoldenGlass/g; s/darkly/goldenglass/g'`.

Also removed after import: Qt5 build and Qt5-only code, Flatpak/CPack/Windows
support, and the CMake package config.

## Plasma lock screen

`plasma/shell/org.goldenglass.desktop/contents/lockscreen/` started as an
unmodified copy of `/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/`
from **plasma-desktop 6.7.5** (GPL-2.0-or-later / LGPL-2.0-or-later, original
headers kept). The copy is commit `e3a0932`; GoldenGlass changes are on top of
it (`git diff e3a0932 -- plasma/shell`). GoldenGlass changes are only in
`LockScreenUi.qml` (the clock and the height of the stack view); `GgClock.qml`
is new.

Ported since the copy: **plasma-desktop 6.8.1** (new authentication flow in
`LockScreenUi.qml` and `MainBlock.qml`). Next merge base: **6.8.1**.

## Panel view (`views/Panel.qml`)

`plasma/shell/org.goldenglass.desktop/contents/views/Panel.qml` started as an
unmodified copy of `/usr/share/plasma/shells/org.kde.plasma.desktop/contents/views/Panel.qml`
from **plasma-desktop 6.7.5** (GPL-2.0-or-later, original header kept). The
copy is commit `2fc7611`; GoldenGlass changes are on top of it
(`git log -- plasma/shell/org.goldenglass.desktop/contents/views/Panel.qml`):
the dock slab (`goldenglassDockSlab`: background, blur mask and shadow follow
the glass slab of `org.goldenglass.dock`; the containment keeps its normal
place), `goldenglassSetThickness()` and the menu bar (no background unless
enabled, dimmed on the screen without focus). Every other panel behaves as
upstream.

Ported since the copy: **plasma-desktop 6.8.1** (`org.kde.plasma.shell.panel`
merged into `org.kde.plasma.shell`, `ContainmentItem`, the virtual keyboard
counts as touching a window). Next merge base: **6.8.1**.

This file must load: if it fails, plasmashell crashes instead of falling back
to the upstream panel (Plasma 6.8.1), and the session has no desktop. The
package guards against it: `X-GoldenGlass-PlasmaVersion` in the shell's
`metadata.json` is the Plasma version `views/` and `lockscreen/` are ported to,
and a pacman hook (`tools/goldenglass-plasma-guard`) deletes both when
`plasma-desktop` is another major.minor, so Plasma's own are used until
`goldenglass-plasma` is rebuilt with a port. CI fails on the same mismatch and
on any QML module we import that is no longer installed
(`tools/check_plasma_compat.py`).

## Porting a new Plasma version (shell)

Three-way merge each copied file: the upstream file of the last merge base, the
new upstream file and ours. The upstream files are in the cached packages:

```sh
mkdir -p /tmp/pd/{old,new}
bsdtar -xf /var/cache/pacman/pkg/plasma-desktop-<base>-*.pkg.tar.zst -C /tmp/pd/old usr/share/plasma/shells
bsdtar -xf /var/cache/pacman/pkg/plasma-desktop-<new>-*.pkg.tar.zst -C /tmp/pd/new usr/share/plasma/shells
up=usr/share/plasma/shells/org.kde.plasma.desktop/contents
git merge-file plasma/shell/org.goldenglass.desktop/contents/views/Panel.qml \
  /tmp/pd/old/$up/views/Panel.qml /tmp/pd/new/$up/views/Panel.qml
```

Same for each file in `lockscreen/` (except `GgClock.qml`). Resolve the
conflicts, then check that the panel loads (`systemctl --user restart
plasma-plasmashell`, no `Panel.qml` errors in `journalctl --user`) and the lock
screen loads (`QT_QPA_PLATFORM=offscreen timeout 8 /usr/lib/kscreenlocker_greet
--testing --shell org.goldenglass.desktop`, no `Failed to load lockscreen QML`
in the journal). Update the merge bases above and `X-GoldenGlass-PlasmaVersion`.

## KWin glass effect (`kwin-effect/`)

`kwin-effect/` is a fork of the **Blur** effect of **KWin 6.7.5**
(`src/plugins/blur`, GPL-2.0-or-later, original headers kept), built out of
tree as the plugin `goldenglass_glass` against the installed KWin headers.
The first commit is the upstream copy with only mechanical changes (the
`GoldenGlass` namespace and `Glass*` names so it does not clash with the
built-in blur in `libkwin`, its own resource prefix and logging category,
linking xcb); `git log -- kwin-effect` shows the GoldenGlass changes on top:
the refraction pass (`shaders/glass.frag`, `drawGlass()`, `isGlassSurface()`,
corner radii from the blur region) and reading the glass level from
`goldenglassrc`. `shaders/glass.frag` includes KWin's `src/opengl/sdf.glsl`
for `sdfRoundedBox`, as the upstream `onscreen_rounded.frag` does.
It reads the same `Effect-blur` settings as KWin's Blur.

The plugin only loads with the KWin version it was built against
(`KWIN_PLUGIN_VERSION_STRING`; a pacman hook, `tools/goldenglass-kwin-check`,
says so after a KWin update). When KWin updates, rebuild
`goldenglass-kstyle`; when KWin changes its blur, diff the new upstream
`src/plugins/blur` against the base commit and port the changes by hand.

Ported since the fork: **KWin 6.8.0** (`git diff v6.7.5 v6.8.0 --
src/plugins/blur src/effect/effect.h`): `drawWindow()` returns whether painting
succeeded (KWin 6.8 is now the minimum) and the blur region is only offset by
the content rect with server-side decorations (upstream `5d45a63f8d`). Next
diff base: `v6.8.0`.

