/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Botón circular con un glifo, como los de macOS 26. Encendido: círculo
    blanco con el glifo en color de acento (en tema claro, al revés, para que
    contraste). Apagado: el gris de los círculos de las píldoras o, con tile,
    el vidrio de una tarjeta (botones sueltos de la cuadrícula).
*/

import QtQuick
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

import "tokens.js" as T

QQC2.AbstractButton {
    id: button

    property string iconName
    property bool active: false
    property bool tile: false
    // Interruptor (encendido/apagado) o botón que solo lanza algo
    property bool isToggle: true
    property real diameter: T.tokens.control_center.icon_circle
    property real glyphSize: T.tokens.control_center.icon
    // Texto del tooltip (los botones sueltos no tienen etiqueta)
    property string toolTip

    readonly property bool dark: Kirigami.ColorUtils.brightnessForColor(Kirigami.Theme.backgroundColor) === Kirigami.ColorUtils.Dark
    readonly property var cc: T.tokens.control_center

    implicitWidth: diameter
    implicitHeight: diameter
    hoverEnabled: true
    Accessible.name: toolTip.length > 0 ? toolTip : text
    Accessible.role: isToggle ? Accessible.CheckBox : Accessible.Button
    Accessible.checkable: isToggle
    Accessible.checked: active

    scale: pressed ? 0.94 : 1
    Behavior on scale { NumberAnimation { duration: Kirigami.Units.shortDuration } }

    // con tile, una pieza de vidrio más (Tile); si no, el círculo gris de las píldoras
    background: Tile {
        id: circle
        goldenGlassTile: button.tile
        radius: width / 2
        opacity: button.enabled ? 1 : 0.5
        color: button.active ? (button.dark ? "white" : Kirigami.Theme.highlightColor)
             : button.tile ? (button.hovered ? Qt.tint(circle.glassColor, Qt.alpha(Kirigami.Theme.textColor, 0.06)) : circle.glassColor)
             : Qt.alpha(Kirigami.Theme.textColor, button.hovered ? button.cc.off_hover_alpha : button.cc.off_alpha)
        border.width: button.tile && !button.active ? 1 : 0
        Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }
    }

    contentItem: Item {
        Kirigami.Icon {
            anchors.centerIn: parent
            width: button.glyphSize
            height: width
            source: button.iconName
            // sin redondear a 16/22 px: el glifo mide lo que dicen los tokens
            roundToIconSize: false
            isMask: true
            color: !button.active ? Kirigami.Theme.textColor
                 : button.dark ? Kirigami.Theme.highlightColor : Kirigami.Theme.highlightedTextColor
            opacity: button.enabled ? 1 : 0.5
        }
    }

    PlasmaComponents3.ToolTip {
        text: button.toolTip
        visible: button.hovered && text.length > 0
    }
}
