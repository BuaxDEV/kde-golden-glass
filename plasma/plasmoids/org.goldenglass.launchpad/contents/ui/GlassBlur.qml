/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Vidrio detrás del panel de Apps y de las tarjetas del Centro de control
    (tools/plasmoids.py lo copia: SHARED). Aparte porque el módulo
    org.goldenglass.glass viene con goldenglass-kstyle: si no está, falla solo
    este archivo (AppsPanel y FloatingPanel lo cargan con un Loader) y el panel
    sigue funcionando sin difuminado.
*/

import org.goldenglass.glass

GlassRegion {}
