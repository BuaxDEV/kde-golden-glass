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

and ported by hand (file names differ after the GoldenGlass rename).
Update the base tag/commit in this file after each port.

## Plasma lock screen

`plasma/shell/org.goldenglass.desktop/contents/lockscreen/` started as an
unmodified copy of `/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/`
from **plasma-desktop 6.7.5** (GPL-2.0-or-later / LGPL-2.0-or-later, original
headers kept). The copy is commit `e3a0932`; GoldenGlass changes are on top of
it (`git diff e3a0932 -- plasma/shell`). `GgClock.qml` is new.

When Plasma updates its lock screen, diff the new upstream files against the
installed ones and port the changes by hand.
