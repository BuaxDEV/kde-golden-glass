// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Atajos de macOS para escritorios y ventanas. Cada uno lanza una acción de
// KWin que ya existe (por su nombre en kglobalaccel); como son atajos propios,
// aparecen en Preferencias del Sistema › Atajos y se pueden cambiar.
//
// Cambiar de escritorio se queda en Meta+Ctrl+←/→: Ctrl+←/→ es saltar palabra
// en los campos de texto de Linux (en macOS eso es Option+←/→).
//
// Organizar ventanas, como Fn+Ctrl+F/C/R de macOS Sequoia (Meta en lugar de
// Fn): Meta+Ctrl+F llena la pantalla, Meta+Ctrl+C centra y Meta+Ctrl+R vuelve
// al tamaño anterior. Las mitades son las nativas Meta+←/→/↑/↓ y los cuartos se
// alcanzan encadenándolas (p. ej. Meta+← y luego Meta+↑).

function invoke(action) {
    callDBus("org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component", "invokeShortcut", action);
}

registerShortcut("GoldenGlass Mission Control", "GoldenGlass: Mission Control (overview)", "Ctrl+Up",
                 () => invoke("Overview"));
registerShortcut("GoldenGlass App Expose", "GoldenGlass: App Exposé (windows of the current app)", "Ctrl+Down",
                 () => invoke("ExposeClass"));

// «Llenar» no alterna: si ya llena la pantalla no hace nada (volver es Meta+Ctrl+R).
// setMaximize quita antes el mosaico de la ventana. Una ventana que no se puede
// maximizar (diálogo, tamaño fijo, pantalla completa) se deja como está.
registerShortcut("GoldenGlass Fill", "GoldenGlass: Fill the screen (maximize)", "Meta+Ctrl+F", () => {
    const w = workspace.activeWindow;
    if (w && w.maximizable) {
        w.setMaximize(true, true);
    }
});
registerShortcut("GoldenGlass Center", "GoldenGlass: Center window", "Meta+Ctrl+C",
                 () => invoke("Window Move Center"));
// «Window Restore» de KWin 6.8 deshace maximizada, mosaico (mitades y cuartos) y
// pantalla completa; en una ventana normal no hace nada.
registerShortcut("GoldenGlass Return", "GoldenGlass: Return to previous size", "Meta+Ctrl+R",
                 () => invoke("Window Restore"));
