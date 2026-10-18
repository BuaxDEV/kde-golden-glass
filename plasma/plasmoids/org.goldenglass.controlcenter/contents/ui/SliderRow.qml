/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Slider entre dos iconos (☼ … ☀), como los de macOS 26. El icono de inicio
    puede ser un botón (p. ej. silenciar) y al final puede ir un botón redondo
    (p. ej. salida de audio).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami

RowLayout {
    id: row

    property string iconFrom
    property string iconTo
    property bool iconClickable: false
    property string trailingIcon
    property string trailingToolTip
    property alias from: slider.from
    property alias to: slider.to
    property alias value: slider.value
    property alias stepSize: slider.stepSize
    property alias pressed: slider.pressed

    signal moved()
    signal released()
    signal iconClicked()
    signal trailingClicked()

    spacing: Kirigami.Units.smallSpacing * 2

    Kirigami.Icon {
        implicitWidth: Kirigami.Units.iconSizes.small
        implicitHeight: implicitWidth
        source: row.iconFrom
        isMask: true
        color: Kirigami.Theme.textColor
        opacity: iconArea.containsMouse ? 1 : 0.85

        MouseArea {
            id: iconArea
            anchors.fill: parent
            anchors.margins: -Kirigami.Units.smallSpacing
            enabled: row.iconClickable
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: row.iconClicked()
        }
    }

    GlassSlider {
        id: slider
        Layout.fillWidth: true
        onMoved: row.moved()
        onPressedChanged: if (!pressed) row.released()
    }

    Kirigami.Icon {
        implicitWidth: Kirigami.Units.iconSizes.small
        implicitHeight: implicitWidth
        source: row.iconTo
        isMask: true
        color: Kirigami.Theme.textColor
        opacity: 0.85
    }

    CircleButton {
        visible: row.trailingIcon.length > 0
        isToggle: false
        diameter: slider.implicitHeight
        glyphSize: Kirigami.Units.iconSizes.small
        iconName: row.trailingIcon
        toolTip: row.trailingToolTip
        onClicked: row.trailingClicked()
    }
}
