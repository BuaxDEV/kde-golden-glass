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
*/

import QtQuick

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

import "tokens.js" as T

PlasmaCore.Dialog {
    id: panel

    // cuadrícula y vistas de detalle; su raíz tiene «detail» (vista abierta)
    property Component content

    signal opened()

    readonly property var cc: T.tokens.control_center
    property rect screen: Plasmoid.containment.screenGeometry

    backgroundHints: PlasmaCore.Dialog.NoBackground
    location: PlasmaCore.Types.Floating
    flags: Qt.WindowStaysOnTopHint
    hideOnWindowDeactivate: true
    visible: false

    onVisibleChanged: {
        if (visible) {
            opened();
        } else {
            appear.stop();
            // al volver a abrirlo, la cuadrícula
            if (body.item) {
                body.item.detail = "";
            }
        }
    }

    function place() {
        screen = Plasmoid.containment.screenGeometry;
        x = screen.x;
        y = screen.y;
    }

    function toggle() {
        if (visible) {
            close();
            return;
        }
        place();
        visible = true;
        requestActivate();
        appear.restart();
    }

    function close() {
        visible = false;
    }

    mainItem: FocusScope {
        width: panel.screen.width
        height: panel.screen.height
        focus: true

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
            // aparece desde la esquina de la barra, como en macOS
            transformOrigin: Item.TopRight
            sourceComponent: panel.content

            // los clics entre tarjetas no cierran
            MouseArea {
                anchors.fill: parent
                z: -1
                acceptedButtons: Qt.AllButtons
            }
        }

        ParallelAnimation {
            id: appear
            NumberAnimation {
                target: body
                property: "opacity"
                from: 0
                to: 1
                duration: panel.cc.appear_ms
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: body
                property: "scale"
                from: panel.cc.appear_scale
                to: 1
                duration: panel.cc.appear_ms
                easing.type: Easing.OutCubic
            }
        }

        // Vidrio detrás de cada tarjeta (módulo org.goldenglass.glass de
        // goldenglass-kstyle). Sin él las tarjetas se ven igual, sin difuminar.
        Loader {
            anchors.fill: parent
            source: Qt.resolvedUrl("GlassBlur.qml")
            onLoaded: item.source = body
        }
    }
}
