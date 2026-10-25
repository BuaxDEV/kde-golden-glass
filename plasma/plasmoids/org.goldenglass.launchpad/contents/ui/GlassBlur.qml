/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Glass behind the Apps panel and the GlassOverlay pieces (tools/plasmoids.py
    copies it: SHARED). A file of its own because the org.goldenglass.glass
    module comes with goldenglass-kstyle: without it only this file fails
    (AppsPanel and GlassOverlay load it with a Loader) and the panel keeps
    working, unblurred.
*/

import org.goldenglass.glass

GlassRegion {}
