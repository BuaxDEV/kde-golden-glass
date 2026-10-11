/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tarjeta con título y control deslizante con icono (pantalla, sonido,
    vidrio). El icono puede ser un botón (p. ej. silenciar).
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3

Tile {
    id: tile

    property string title
    property string iconName
    property alias from: slider.from
    property alias to: slider.to
    property alias value: slider.value
    property alias stepSize: slider.stepSize
    property alias pressed: slider.pressed
    property bool iconClickable: false

    signal moved()
    signal released()
    signal iconClicked()

    PlasmaComponents3.Label {
        text: tile.title
        font.weight: Font.DemiBold
        textFormat: Text.PlainText
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        PlasmaComponents3.ToolButton {
            visible: tile.iconClickable
            icon.name: tile.iconName
            display: QQC2.AbstractButton.IconOnly
            text: tile.title
            onClicked: tile.iconClicked()
        }
        Kirigami.Icon {
            visible: !tile.iconClickable
            source: tile.iconName
            isMask: true
            color: Kirigami.Theme.textColor
            implicitWidth: Kirigami.Units.iconSizes.small
            implicitHeight: implicitWidth
        }
        PlasmaComponents3.Slider {
            id: slider
            Layout.fillWidth: true
            onMoved: tile.moved()
            onPressedChanged: if (!pressed) tile.released()
        }
    }
}
