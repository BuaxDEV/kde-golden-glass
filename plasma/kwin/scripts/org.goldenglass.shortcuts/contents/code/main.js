// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Atajos de macOS para escritorios y ventanas. Cada uno lanza una acción de
// KWin que ya existe (por su nombre en kglobalaccel); como son atajos propios,
// aparecen en Preferencias del Sistema › Atajos y se pueden cambiar.
//
// Cambiar de escritorio se queda en Meta+Ctrl+←/→: Ctrl+←/→ es saltar palabra
// en los campos de texto de Linux (en macOS eso es Option+←/→).

function invoke(action) {
    callDBus("org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component", "invokeShortcut", action);
}

registerShortcut("GoldenGlass Mission Control", "GoldenGlass: Mission Control (overview)", "Ctrl+Up",
                 () => invoke("Overview"));
registerShortcut("GoldenGlass App Expose", "GoldenGlass: App Exposé (windows of the current app)", "Ctrl+Down",
                 () => invoke("ExposeClass"));
