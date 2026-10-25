/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Interruptor de macOS (cabecera de Wi‑Fi y Bluetooth en sus vistas de
    detalle): pista redondeada de acento cuando está encendido y bola blanca.
*/

import QtQuick
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami

import "tokens.js" as T

QQC2.AbstractButton {
    id: control

    readonly property var cc: T.tokens.control_center

    checkable: true
    hoverEnabled: true
    implicitWidth: cc.switch_width
    implicitHeight: cc.switch_height
    Accessible.role: Accessible.CheckBox
    opacity: enabled ? 1 : T.tokens.text.disabled_alpha

    background: Rectangle {
        radius: height / 2
        color: control.checked ? Kirigami.Theme.highlightColor
                               : Qt.alpha(Kirigami.Theme.textColor, control.hovered ? control.cc.off_hover_alpha : control.cc.off_alpha)
        Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }
    }

    contentItem: Item {
        Rectangle {
            readonly property real inset: 2
            width: parent.height - 2 * inset
            height: width
            radius: width / 2
            y: inset
            x: control.checked ? parent.width - width - inset : inset
            color: control.cc.switch_knob
            border.width: 1
            border.color: Qt.rgba(0, 0, 0, control.cc.switch_knob_border_alpha)
            Behavior on x { NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic } }
        }
    }
}
