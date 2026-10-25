/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Splash de GoldenGlass: logo centrado y barra de progreso fina, como el
    arranque de macOS. ksplash avanza `stage` de 1 a 6.

    Plantilla: tools/lookandfeel.py sustituye los marcadores @sección.clave@ desde los tokens.
    Las medidas son las de [boot] (las del arranque de Plymouth) en gridUnit.
*/

import QtQuick
import org.kde.kirigami as Kirigami

import "tokens.js" as T

Rectangle {
    id: root
    color: "@lookandfeel.splash_background@"

    property int stage
    readonly property int lastStage: 6
    readonly property var boot: T.tokens.boot

    onStageChanged: {
        if (stage === 1) {
            fadeIn.running = true;
        } else if (stage === lastStage) {
            fadeOut.running = true;
        }
    }

    Item {
        id: content
        anchors.fill: parent
        opacity: 0

        Image {
            id: logo
            readonly property real size: Kirigami.Units.gridUnit * root.boot.logo_size / root.boot.grid_unit
            anchors.centerIn: parent
            anchors.verticalCenterOffset: Kirigami.Units.gridUnit * root.boot.logo_offset / root.boot.grid_unit
            asynchronous: true
            source: "images/goldenglass.svg"
            sourceSize.width: size
            sourceSize.height: size
        }

        // Barra de progreso: pista y relleno redondeados.
        Rectangle {
            id: track
            width: Kirigami.Units.gridUnit * root.boot.bar_width / root.boot.grid_unit
            height: root.boot.bar_height
            radius: height / 2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: logo.bottom
            anchors.topMargin: Kirigami.Units.gridUnit * root.boot.bar_gap / root.boot.grid_unit
            color: "@lookandfeel.splash_track@"

            Rectangle {
                height: parent.height
                radius: parent.radius
                color: "@lookandfeel.splash_fill@"
                width: Math.max(parent.height, parent.width * Math.min(root.stage, root.lastStage) / root.lastStage)
                Behavior on width {
                    NumberAnimation {
                        duration: Kirigami.Units.longDuration * 2
                        easing.type: Easing.OutCubic
                    }
                }
            }
        }
    }

    OpacityAnimator {
        id: fadeIn
        target: content
        from: 0
        to: 1
        duration: Kirigami.Units.veryLongDuration
        easing.type: Easing.InOutQuad
    }

    OpacityAnimator {
        id: fadeOut
        target: content
        from: 1
        to: 0
        duration: Kirigami.Units.veryLongDuration
        easing.type: Easing.InOutQuad
    }
}
