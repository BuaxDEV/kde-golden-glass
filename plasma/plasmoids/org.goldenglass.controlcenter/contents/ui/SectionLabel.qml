/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Encabezado de sección de una vista de detalle («Redes conocidas»,
    «Salida»…), gris y pequeño como en macOS.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import "tokens.js" as T

PlasmaComponents3.Label {
    Layout.fillWidth: true
    Layout.leftMargin: Kirigami.Units.smallSpacing
    Layout.topMargin: Kirigami.Units.smallSpacing
    opacity: T.tokens.text.tertiary_alpha
    font.weight: Font.DemiBold
    font.pointSize: Kirigami.Theme.smallFont.pointSize
    elide: Text.ElideRight
    textFormat: Text.PlainText
}
