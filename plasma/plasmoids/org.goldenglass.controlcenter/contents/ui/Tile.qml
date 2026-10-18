/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tarjeta del Centro de control: una pieza de vidrio suelta. KWin la
    difumina (GlassRegion) y lleva el fondo del vidrio de Plasma, más claro
    que el de los popups, como en macOS 26. Las píldoras y los botones
    redondos ponen radius a la mitad de su altura.
*/

import QtQuick

import org.kde.kirigami as Kirigami

import "tokens.js" as T

Rectangle {
    // GlassRegion pide blur detrás de los elementos con esta propiedad a true
    property bool goldenGlassTile: true
    readonly property color glassColor: Qt.alpha(Kirigami.Theme.backgroundColor, T.tokens.control_center.tile_alpha)

    radius: T.tokens.control_center.tile_radius
    color: glassColor
    border.width: 1
    border.color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.glass.border.alpha)
}
