/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Un icono del dock: crece con la ampliación (size, lo calcula DockView),
    punto debajo si la app está abierta, rebote al arrancar (sin parar
    mientras arranca) y al pedir atención (unas veces y queda quieto), y el
    nombre encima al pasar el ratón; con ventanas, también sus miniaturas
    (previews). El contenido interactivo (clic, menú, soltar) lo pone quien lo
    usa, como hijo.
*/

import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore

import "tokens.js" as T

Item {
    id: tile

    property real size
    property real padding                   // relleno inferior de la placa (para el punto)
    property var iconSource
    property string fallback: "application-x-executable"
    property string label
    property bool running: false
    property bool launching: false          // IsStartup
    property bool demandsAttention: false
    property bool hovered: false
    property bool pressed: false
    property bool showIcon: true            // la Papelera dibuja el suyo
    // miniaturas de ventanas (Component) o null para solo el nombre
    property Component previews: null
    property bool tooltipEnabled: true
    default property alias content: inner.data

    readonly property real lift: bounceLift

    width: size
    height: size

    // --- rebote ----------------------------------------------------------------
    property real bounceLift: 0
    property int bouncesLeft: 0
    readonly property real bounceHeight: size * T.tokens.dock.bounce

    function bounce(times) {
        bouncesLeft = Math.max(bouncesLeft, times);
        if (!bounceAnimation.running) {
            bounceAnimation.start();
        }
    }

    onLaunchingChanged: {
        if (launching) {
            bounce(1);
        }
    }
    onDemandsAttentionChanged: {
        if (demandsAttention) {
            bounce(T.tokens.dock.attention_bounces);
        }
    }

    SequentialAnimation {
        id: bounceAnimation
        NumberAnimation {
            target: tile
            property: "bounceLift"
            to: tile.bounceHeight
            duration: T.tokens.dock.bounce_ms / 2
            easing.type: Easing.OutQuad
        }
        NumberAnimation {
            target: tile
            property: "bounceLift"
            to: 0
            duration: T.tokens.dock.bounce_ms / 2
            easing.type: Easing.InQuad
        }
        onFinished: {
            // mientras arranca, rebota sin parar; si pide atención, las veces que queden
            tile.bouncesLeft = Math.max(0, tile.bouncesLeft - 1);
            if (tile.launching || (tile.demandsAttention && tile.bouncesLeft > 0)) {
                start();
            }
        }
    }

    // --- icono, punto y contenido -------------------------------------------------
    Kirigami.Icon {
        id: icon
        visible: tile.showIcon
        x: 0
        y: -tile.bounceLift
        width: tile.size
        height: tile.size
        source: tile.iconSource
        fallback: tile.fallback
        active: tile.hovered
        // al pulsar, más oscuro (como macOS)
        opacity: tile.pressed ? 0.7 : 1
    }

    Rectangle {
        id: dot
        readonly property real dotSize: T.tokens.plasma.task_dot_size
        visible: tile.running
        width: dotSize
        height: dotSize
        radius: dotSize / 2
        anchors.horizontalCenter: parent.horizontalCenter
        y: tile.height + Math.max(0, (tile.padding - dotSize) / 2)
        color: Kirigami.Theme.textColor
        opacity: 0.8
    }

    Item {
        id: inner
        anchors.fill: parent
    }

    // --- nombre (y miniaturas) encima --------------------------------------------
    PlasmaCore.ToolTipArea {
        anchors.fill: parent
        active: tile.tooltipEnabled && !tile.pressed
        interactive: tile.previews !== null
        mainText: tile.previews === null ? tile.label : ""
        mainItem: tile.previews !== null ? previewLoader.item as Item : null
        location: PlasmaCore.Types.BottomEdge
    }

    Loader {
        id: previewLoader
        visible: false
        active: tile.previews !== null
        sourceComponent: tile.previews
    }
}
