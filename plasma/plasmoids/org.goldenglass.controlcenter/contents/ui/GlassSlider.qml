/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Slider del Centro de control como el de macOS 26: pista fina y redondeada
    con el tramo recorrido en el color del texto, sin tirador. Se arrastra
    desde cualquier punto de la pista (y con la rueda del ratón).
*/

import QtQuick
import QtQuick.Templates as QQT

import org.kde.kirigami as Kirigami

import "tokens.js" as T

QQT.Slider {
    id: control

    readonly property var cc: T.tokens.control_center

    implicitWidth: Kirigami.Units.gridUnit * 10
    // alto del botón redondo opcional de SliderTile: todas las tarjetas miden igual
    implicitHeight: Kirigami.Units.iconSizes.small + Kirigami.Units.smallSpacing * 2
    wheelEnabled: true
    opacity: enabled ? 1 : T.tokens.text.disabled_alpha

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        width: control.availableWidth
        height: control.cc.slider_height + (control.pressed || control.hovered ? 2 : 0)
        radius: height / 2
        color: Qt.alpha(Kirigami.Theme.textColor, control.cc.slider_track_alpha)
        Behavior on height { NumberAnimation { duration: Kirigami.Units.shortDuration } }

        Rectangle {
            x: control.mirrored ? parent.width - width : 0
            width: Math.max(parent.height, control.position * parent.width)
            height: parent.height
            radius: parent.radius
            color: Kirigami.Theme.textColor
            visible: control.position > 0
        }
    }

    handle: Item {
        x: control.leftPadding + control.visualPosition * control.availableWidth
        y: control.topPadding
        height: control.availableHeight
    }
}
