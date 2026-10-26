/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Un icono del dock: crece con la ampliación (size, lo calcula DockView),
    punto debajo si la app está abierta, rebote al arrancar (sin parar
    mientras arranca) y al pedir atención (unas veces y queda quieto), y el
    nombre encima al pasar el ratón; con ventanas, también sus miniaturas
    (previews). El contenido interactivo (clic, menú, soltar) lo pone quien lo
    usa, como hijo. Al soltar una app en el dock, el icono anterior al sitio
    donde caerá deja un hueco a su derecha (trailingSpace).
*/

import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
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
    // a live unit in systemd and no window: a fainter dot and its own tooltip line
    property bool background: false
    property bool launching: false          // IsStartup
    property bool demandsAttention: false
    property bool hovered: false
    property bool pressed: false
    property bool showIcon: true            // la Papelera dibuja el suyo
    // miniaturas de ventanas (Component) o null para solo el nombre
    property Component previews: null
    property bool tooltipEnabled: true
    // hueco a la derecha del icono (lo anima DockView al arrastrar una app)
    property real trailingSpace: 0
    default property alias content: inner.data

    readonly property real lift: bounceLift

    width: size + trailingSpace
    height: size

    // --- rebote ----------------------------------------------------------------
    property real bounceLift: 0
    property int bouncesLeft: 0
    readonly property real bounceHeight: size * T.tokens.dock.bounce

    // sin animaciones (Motion.animated), con «Reducir movimiento» o con
    // bounce_ms a 0 cada tramo dura 0 ms y el rebote no arranca: una animación
    // de 0 ms termina dentro de start(), así que reiniciarla en onFinished
    // sería una recursión sin fin (SP-04). Con 1 ms o más termina en el
    // fotograma siguiente.
    readonly property bool bounceEnabled: Motion.moveMs(T.tokens.dock.bounce_ms / 2) >= 1

    function bounce(times) {
        if (!bounceEnabled) {
            return;
        }
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
            duration: Motion.moveMs(T.tokens.dock.bounce_ms / 2)
            easing.type: Easing.OutQuad
        }
        NumberAnimation {
            target: tile
            property: "bounceLift"
            to: 0
            duration: Motion.moveMs(T.tokens.dock.bounce_ms / 2)
            easing.type: Easing.InQuad
        }
        onFinished: {
            // mientras arranca, rebota sin parar; si pide atención, las veces que queden
            tile.bouncesLeft = Math.max(0, tile.bouncesLeft - 1);
            if (tile.bounceEnabled && (tile.launching || (tile.demandsAttention && tile.bouncesLeft > 0))) {
                start();
            }
        }
    }

    // --- icono, punto y contenido -------------------------------------------------
    ThemedIcon {
        id: icon
        visible: tile.showIcon
        x: 0
        y: -tile.bounceLift
        width: tile.size
        height: tile.size
        themedSource: tile.iconSource
        fallback: tile.fallback
        active: tile.hovered
        // al pulsar, más oscuro (como macOS)
        opacity: tile.pressed ? T.tokens.dock.press_alpha : 1
    }

    Rectangle {
        id: dot
        readonly property real dotSize: T.tokens.plasma.task_dot_size
        visible: tile.running || tile.background
        width: dotSize
        height: dotSize
        radius: dotSize / 2
        x: (tile.size - dotSize) / 2
        y: tile.height + Math.max(0, (tile.padding - dotSize) / 2)
        color: Kirigami.Theme.textColor
        opacity: tile.background && !tile.running ? T.tokens.dock.background_dot_alpha : T.tokens.dock.dot_alpha
    }

    Item {
        id: inner
        width: tile.size
        height: tile.size
    }

    // --- nombre (y miniaturas) encima --------------------------------------------
    // Ventana propia (Dialog de tipo Tooltip) y no PlasmaCore.ToolTipArea: en un
    // panel, libplasma coloca sus tooltips sobre el borde de la máscara de la
    // ventana, que en el dock es la placa, y taparían los iconos ampliados.
    // Dialog los pone sobre el elemento que se le da: tipAnchor, cuyo borde
    // superior es el del icono más ampliado, como el nombre en el Dock de macOS.
    property real maxSize: size             // tamaño del icono más ampliado
    readonly property bool tooltipShown: tooltip.visible

    // el contenido solo existe mientras se ve: las miniaturas mantienen un
    // stream de PipeWire por ventana (KWin la renderiza sin parar) y la lista
    // de ventanas se rehace al abrir
    property bool tipLoaded: false

    function showToolTip() {
        tipLoaded = true;
        tooltip.visible = true;
    }

    function hideToolTip() {
        showTimer.stop();
        tooltip.visible = false;
    }

    // un poco por encima del icono más ampliado: el globo no lo toca
    Item {
        id: tipAnchor
        width: tile.size
        height: tile.maxSize + Kirigami.Units.smallSpacing
        y: tile.height - height
    }

    Timer {
        id: showTimer
        interval: T.tokens.dock.label_delay_ms
        onTriggered: tile.showToolTip()
    }
    // con miniaturas, un margen para pasar el ratón del icono al tooltip
    Timer {
        id: hideTimer
        interval: T.tokens.dock.preview_hide_ms
        onTriggered: {
            if (!tile.hovered && !tooltipHover.hovered) {
                tooltip.visible = false;
            }
        }
    }

    onHoveredChanged: {
        if (hovered && tooltipEnabled) {
            hideTimer.stop();
            if (!tooltip.visible) {
                showTimer.restart();
            }
        } else if (!hovered) {
            showTimer.stop();
            if (previews !== null) {
                hideTimer.restart();
            } else {
                tooltip.visible = false;
            }
        }
    }
    onTooltipEnabledChanged: {
        if (!tooltipEnabled) {
            hideToolTip();
        }
    }
    onPressedChanged: {
        if (pressed) {
            hideToolTip();
        }
    }

    // la ampliación mueve el icono: se recoloca (Dialog solo lo hace al cambiar visualParent)
    function reposition() {
        if (tooltip.visible) {
            tooltip.visualParent = null;
            tooltip.visualParent = tipAnchor;
        }
    }
    onXChanged: Qt.callLater(reposition)
    onWidthChanged: Qt.callLater(reposition)

    PlasmaCore.Dialog {
        id: tooltip
        type: PlasmaCore.Dialog.Tooltip
        flags: Qt.WindowDoesNotAcceptFocus
        // Floating: globo con los cuatro bordes (con BottomEdge, Dialog quita
        // el de abajo, como si estuviera pegado al panel); se coloca igual encima
        location: PlasmaCore.Types.Floating
        visualParent: tipAnchor
        hideOnWindowDeactivate: true
        outputOnly: tile.previews === null
        visible: false
        onVisibleChanged: {
            if (!visible) {
                tile.tipLoaded = false;
            }
        }

        mainItem: Item {
            implicitWidth: content.implicitWidth
            implicitHeight: content.implicitHeight
            width: implicitWidth
            height: implicitHeight

            HoverHandler {
                id: tooltipHover
                onHoveredChanged: {
                    if (!hovered && !tile.hovered) {
                        hideTimer.restart();
                    }
                }
            }

            Loader {
                id: content
                active: tile.tipLoaded
                sourceComponent: tile.previews !== null ? tile.previews : labelComponent
                Connections {
                    target: content.item
                    ignoreUnknownSignals: true
                    function onActivated() {
                        tile.hideToolTip();
                    }
                }
            }
        }
    }

    Component {
        id: labelComponent
        Column {
            PlasmaComponents3.Label {
                text: tile.label
                textFormat: Text.PlainText
                leftPadding: Kirigami.Units.smallSpacing
                rightPadding: Kirigami.Units.smallSpacing
            }
            PlasmaComponents3.Label {
                visible: tile.background && !tile.running
                text: i18n("Running in the background")
                textFormat: Text.PlainText
                leftPadding: Kirigami.Units.smallSpacing
                rightPadding: Kirigami.Units.smallSpacing
                opacity: T.tokens.text.secondary_alpha
            }
        }
    }
}
