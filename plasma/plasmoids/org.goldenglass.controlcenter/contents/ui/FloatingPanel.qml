/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Ventana del Centro de control, como en macOS 26: las tarjetas sueltas sobre
    el escritorio, bajo la barra de menús y pegadas al borde derecho de la
    pantalla. Es un PlasmaCore.Dialog sin fondo (el popup de Plasma no permite
    quitarlo) que cubre toda la pantalla, transparente: un clic fuera de las
    tarjetas, también en la barra de menús, lo cierra (la barra no toma el foco,
    así que perderlo no bastaría). GlassBlur pide a KWin vidrio solo detrás de
    cada tarjeta. También se cierra con Esc, con el icono o al irse el foco a
    otra pantalla.

    Animación de Liquid Glass: al abrir, el vidrio brota del icono de la barra
    con un resorte (crece más deprisa a lo alto que a lo ancho y se pasa un
    poco antes de asentarse); al cerrar, se encoge hacia el icono y se
    desvanece.
*/

import QtQuick

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

import "tokens.js" as T

PlasmaCore.Dialog {
    id: panel

    // cuadrícula y vistas de detalle; su raíz tiene «detail» (vista abierta)
    property Component content
    // icono de la barra: la animación nace de él
    property Item anchorItem

    signal opened()

    readonly property var cc: T.tokens.control_center
    property rect screen: Plasmoid.containment.screenGeometry
    property bool closing: false

    backgroundHints: PlasmaCore.Dialog.NoBackground
    location: PlasmaCore.Types.Floating
    // mientras se cierra, los clics pasan a lo que hay debajo
    flags: closing ? Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput : Qt.WindowStaysOnTopHint
    visible: false

    // al irse el foco a otra ventana (otra pantalla, una app): cerrar animando,
    // no de golpe como haría hideOnWindowDeactivate
    onActiveChanged: {
        if (!active && visible) {
            close();
        }
    }

    function place() {
        screen = Plasmoid.containment.screenGeometry;
        x = screen.x;
        y = screen.y;
    }

    // centro del icono, en coordenadas de body (si no se sabe, su esquina)
    function iconOriginX() {
        if (anchorItem) {
            const center = anchorItem.mapToGlobal(anchorItem.width / 2, 0).x - screen.x;
            if (center > 0 && center < screen.width) {
                return Math.min(Math.max(center - body.x, 0), body.width);
            }
        }
        return body.width;
    }

    function toggle() {
        if (visible && !closing) {
            close();
        } else {
            open();
        }
    }

    // también a medio cierre: sigue desde donde iba, con la cuadrícula
    function open() {
        closeAnimation.stop();
        closing = false;
        if (body.item) {
            body.item.detail = "";
        }
        place();
        visible = true;
        requestActivate();
        glass.track(true);
        origin.origin.x = iconOriginX();
        openAnimation.restart();
        opened();
    }

    function close() {
        if (!visible || closing) {
            return;
        }
        closing = true;
        openAnimation.stop();
        origin.origin.x = iconOriginX();
        closeAnimation.restart();
    }

    mainItem: FocusScope {
        width: panel.screen.width
        height: panel.screen.height
        focus: true
        // las tarjetas que se desvanecen ya no responden
        enabled: !panel.closing

        // animaciones aquí: Dialog solo admite Items como hijos directos
        ParallelAnimation {
            id: openAnimation
            NumberAnimation {
                target: body
                property: "opacity"
                to: 1
                duration: Motion.fadeMs(panel.cc.open_fade_ms)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: origin
                property: "xScale"
                to: 1
                duration: Motion.moveMs(panel.cc.open_ms)
                easing.type: Easing.OutBack
                easing.overshoot: Motion.overshoot(panel.cc.open_overshoot)
            }
            NumberAnimation {
                target: origin
                property: "yScale"
                to: 1
                duration: Motion.moveMs(panel.cc.open_ms_y)
                easing.type: Easing.OutBack
                easing.overshoot: Motion.overshoot(panel.cc.open_overshoot)
            }
        }

        ParallelAnimation {
            id: closeAnimation
            NumberAnimation {
                target: body
                property: "opacity"
                to: 0
                duration: Motion.fadeMs(panel.cc.close_ms)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: origin
                properties: "xScale,yScale"
                to: panel.cc.close_scale
                duration: Motion.moveMs(panel.cc.close_ms)
                easing.type: Easing.InCubic
            }
            SequentialAnimation {
                // KWin no difumina a medias: el vidrio se quita cuando las
                // tarjetas ya casi no se ven
                PauseAnimation {
                    duration: Motion.fadeMs(panel.cc.close_ms) * panel.cc.close_unblur_at
                }
                ScriptAction {
                    script: glass.track(false)
                }
            }
            onFinished: {
                panel.visible = false;
                panel.closing = false;
                // la próxima vez brota desde aquí
                origin.xScale = panel.cc.open_scale_x;
                origin.yScale = panel.cc.open_scale_y;
            }
        }

        // Esc: primero vuelve de una vista de detalle a la cuadrícula
        Keys.onEscapePressed: {
            if (body.item && body.item.detail !== "") {
                body.item.detail = "";
            } else {
                panel.close();
            }
        }

        // clic fuera de las tarjetas
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onPressed: panel.close()
        }

        Loader {
            id: body
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: T.tokens.plasma.menubar_height + panel.cc.floating_margin
            anchors.rightMargin: panel.cc.screen_margin
            sourceComponent: panel.content
            // cerrado: invisible y encogido, listo para brotar
            opacity: 0
            transform: Scale {
                id: origin
                origin.y: 0
                xScale: panel.cc.open_scale_x
                yScale: panel.cc.open_scale_y
            }

            // los clics entre tarjetas no cierran
            MouseArea {
                anchors.fill: parent
                z: -1
                acceptedButtons: Qt.AllButtons
            }
        }

        // Vidrio detrás de cada tarjeta (módulo org.goldenglass.glass de
        // goldenglass-kstyle). Sin él las tarjetas se ven igual, sin difuminar.
        Loader {
            id: glass
            anchors.fill: parent
            source: Qt.resolvedUrl("GlassBlur.qml")
            onLoaded: {
                item.source = body;
                item.updateInterval = panel.cc.glass_update_ms;
            }

            // con false, KWin deja de difuminar
            function track(on) {
                if (item) {
                    item.active = on;
                }
            }
        }
    }
}
