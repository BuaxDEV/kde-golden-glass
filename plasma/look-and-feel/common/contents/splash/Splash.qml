/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Splash de GoldenGlass: logo centrado y barra de progreso fina, como el
    arranque de macOS. ksplash avanza `stage` de 1 a 6.

    Plantilla: tools/gen_tokens.py sustituye los marcadores entre arrobas desde los tokens.
*/

import QtQuick
import org.kde.kirigami as Kirigami

Rectangle {
    id: root
    color: "@SPLASH_BACKGROUND@"

    property int stage
    readonly property int lastStage: 6

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
            readonly property real size: Kirigami.Units.gridUnit * 7
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -Kirigami.Units.gridUnit * 2
            asynchronous: true
            source: "images/goldenglass.svg"
            sourceSize.width: size
            sourceSize.height: size
        }

        // Barra de progreso: pista y relleno redondeados.
        Rectangle {
            id: track
            width: Kirigami.Units.gridUnit * 12
            height: 6
            radius: height / 2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: logo.bottom
            anchors.topMargin: Kirigami.Units.gridUnit * 3
            color: "@SPLASH_TRACK@"

            Rectangle {
                height: parent.height
                radius: parent.radius
                color: "@SPLASH_FILL@"
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
