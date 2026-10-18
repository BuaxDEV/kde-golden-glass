// SPDX-FileCopyrightText: 2026 GoldenGlass contributors
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Categorías de Apps, como las de macOS 27 y en su orden. Cada categoría del
// menú de KDE (identificada por su icono, que no depende del idioma) va a una
// de ellas; lo que no está en la tabla va a «Otras».

.pragma library

var order = ["utilities", "developer", "social", "productivity", "entertainment", "creativity", "reading", "other"];

var byIcon = {
    "applications-utilities": "utilities",
    "applications-accessories": "utilities",
    "applications-system": "utilities",
    "preferences-system": "utilities",
    "preferences-desktop": "utilities",
    "applications-development": "developer",
    "applications-office": "productivity",
    "applications-internet": "social",
    "applications-graphics": "creativity",
    "applications-education": "reading",
    "applications-science": "reading",
    "help-about": "reading",
    "help-browser": "reading",
    "applications-multimedia": "entertainment",
    "applications-games": "entertainment",
};

function categoryFor(icon) {
    const base = String(icon || "").replace(/-symbolic$/, "");
    return byIcon[base] || "other";
}
