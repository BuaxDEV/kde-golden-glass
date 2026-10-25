/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tarjeta del Centro de control: una pieza de vidrio suelta. KWin la
    difumina (GlassRegion) y lleva el fondo del vidrio de Plasma, más claro
    que el de los popups, como en macOS 26. Las píldoras y los botones
    redondos ponen radius a la mitad de su altura.

    Al pulsarla (pressed y pressPoint los pone quien la usa) reacciona como
    Liquid Glass: cede un poco, se ilumina desde el punto de contacto y al
    soltarla vuelve con un rebote. El vidrio de KWin la sigue.
*/

import QtQuick
import QtQuick.Shapes

import org.kde.kirigami as Kirigami

import "tokens.js" as T

Rectangle {
    id: tile

    // GlassRegion pide blur detrás de los elementos con esta propiedad a true
    property bool goldenGlassTile: true
    property bool pressed: false
    property point pressPoint: Qt.point(width / 2, height / 2)
    // 0 en reposo, 1 pulsada; al soltar pasa un poco por debajo de 0 (rebote)
    property real pressAmount: 0

    readonly property real glassAlpha: Accessibility.reduceTransparency ? T.tokens.accessibility.reduce_transparency_alpha
                                                                        : T.tokens.control_center.tile_alpha
    readonly property color glassColor: Qt.alpha(Kirigami.Theme.backgroundColor, glassAlpha)

    radius: T.tokens.control_center.tile_radius
    color: glassColor
    border.width: 1
    border.color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.glass.border.alpha)
    scale: 1 - (1 - T.tokens.control_center.press_scale) * pressAmount

    onPressedChanged: {
        if (pressed) {
            release.stop();
            press.restart();
        } else {
            press.stop();
            release.restart();
        }
    }

    NumberAnimation {
        id: press
        target: tile
        property: "pressAmount"
        to: 1
        duration: Motion.moveMs(T.tokens.control_center.press_ms)
        easing.type: Easing.OutCubic
    }
    NumberAnimation {
        id: release
        target: tile
        property: "pressAmount"
        to: 0
        duration: Motion.moveMs(T.tokens.control_center.release_ms)
        easing.type: Easing.OutBack
        easing.overshoot: Motion.overshoot(T.tokens.control_center.release_overshoot)
    }

    // Al pulsarla, el vidrio se aclara y brilla desde el punto de contacto
    // (recortado a la forma de la tarjeta). Solo existe mientras se ve.
    Loader {
        anchors.fill: parent
        active: tile.pressed || tile.pressAmount > 0
        sourceComponent: pressLight
    }

    Component {
        id: pressLight

        Item {
            opacity: Math.max(0, tile.pressAmount)

            Rectangle {
                anchors.fill: parent
                radius: tile.radius
                color: T.tokens.control_center.press_color
                opacity: T.tokens.control_center.press_brighten_alpha
            }

            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer

                ShapePath {
                    strokeWidth: -1
                    fillGradient: RadialGradient {
                        centerX: tile.pressPoint.x
                        centerY: tile.pressPoint.y
                        centerRadius: T.tokens.control_center.press_glow_radius
                        focalX: centerX
                        focalY: centerY
                        GradientStop {
                            position: 0
                            color: Qt.alpha(T.tokens.control_center.press_color, T.tokens.control_center.press_glow_alpha)
                        }
                        GradientStop {
                            position: 1
                            color: Qt.alpha(T.tokens.control_center.press_color, 0)
                        }
                    }
                    PathRectangle {
                        width: tile.width
                        height: tile.height
                        radius: tile.radius
                    }
                }
            }
        }
    }
}
