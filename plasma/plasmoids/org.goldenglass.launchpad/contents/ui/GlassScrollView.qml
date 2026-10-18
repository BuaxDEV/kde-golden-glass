/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Vista desplazable como las de macOS:

      - Barra superpuesta: un tirador fino sobre el contenido, sin carril ni
        hueco reservado, que aparece al desplazarse y se desvanece al parar. Con
        el ratón en el borde engorda y muestra el carril; se puede arrastrar y
        un clic en el carril avanza una página.
      - Rueda del ratón suave: cada paso se anima en vez de saltar.
      - Touchpad: el contenido sigue a los dedos y al soltar sigue deslizándose
        con inercia (Flickable.flick).
      - Rebote elástico: pasado el extremo el contenido se estira con
        resistencia (la fórmula de UIScrollView) y vuelve con un resorte.
      - Borde difuminado (Liquid Glass): por arriba el contenido se desvanece
        entre fadeStart y topInset, para pasar bajo lo que haya encima (las
        etiquetas de Apps) en vez de cortarse en seco.

    El contenido empieza en topInset; su alto lo da el hijo (childrenRect).
    El ratón no arrastra el contenido (sí el dedo): así los hijos pueden
    arrastrarse a otro sitio, como las apps al dock.

        GlassScrollView {
            topInset: 40
            fadeStart: 12
            Column { width: parent.width; … }
        }
*/

import QtQuick
import QtQuick.Effects

import org.kde.kirigami as Kirigami

import "tokens.js" as T

Item {
    id: root

    default property alias contentData: holder.data
    readonly property alias flickable: flick
    readonly property alias contentY: flick.contentY
    // el contenido empieza aquí; por encima solo se ve al desplazarse
    property real topInset: 0
    // por arriba, el contenido es transparente hasta aquí y opaco desde topInset
    property real fadeStart: topInset
    property real bottomInset: 0

    readonly property var tok: T.tokens.scroll
    readonly property real maxY: Math.max(0, flick.contentHeight - flick.height)

    // --- posición -------------------------------------------------------------

    function clampY(y) {
        return Math.max(0, Math.min(maxY, y));
    }

    // Estiramiento pasado el extremo: crece cada vez menos (UIScrollView)
    function rubber(over) {
        const d = Math.max(1, flick.height);
        return (1 - 1 / (over * tok.rubber_band / d + 1)) * d;
    }
    function band(y) {
        if (y < 0) {
            return -rubber(-y);
        }
        if (y > maxY) {
            return maxY + rubber(y - maxY);
        }
        return y;
    }

    // Desplaza animando, como un paso de rueda
    function scrollTo(y) {
        flick.cancelFlick();
        wheelAnimation.stop();
        wheelAnimation.from = flick.contentY;
        wheelAnimation.to = clampY(y);
        wheelAnimation.start();
    }

    // Sin animación ni barra (p. ej. al abrir)
    function jumpTo(y) {
        flick.cancelFlick();
        wheelAnimation.stop();
        endGesture(false);
        quiet = true;
        flick.contentY = clampY(y);
        quiet = false;
    }

    // Desplaza lo justo para que se vea el tramo [y, y + h] del contenido
    function ensureVisible(y, h) {
        const top = flick.contentY + topInset;
        const bottom = flick.contentY + flick.height;
        const target = wheelAnimation.running ? wheelAnimation.to : flick.contentY;
        if (y < top) {
            scrollTo(target - (top - y) - Kirigami.Units.smallSpacing);
        } else if (y + h > bottom) {
            scrollTo(target + (y + h - bottom) + Kirigami.Units.smallSpacing);
        }
    }

    // --- rueda y touchpad -----------------------------------------------------

    property bool gesture: false
    property real virtualY: 0       // posición sin estirar durante el gesto
    property var samples: []        // [{ t, dy }] para la velocidad al soltar
    property bool systemMomentum: false
    property bool quiet: false

    function beginGesture() {
        wheelAnimation.stop();
        flick.cancelFlick();
        gesture = true;
        systemMomentum = false;
        virtualY = flick.contentY;
        samples = [];
    }

    function endGesture(fling) {
        if (!gesture) {
            return;
        }
        gesture = false;
        gestureTimeout.stop();
        if (flick.contentY < 0 || flick.contentY > maxY) {
            flick.returnToBounds();
            return;
        }
        if (fling === false || systemMomentum) {
            return;
        }
        // velocidad de los últimos 100 ms (si los dedos pararon, 0)
        const now = Date.now();
        const recent = samples.filter(s => now - s.t <= 100);
        if (recent.length < 2) {
            return;
        }
        const span = Math.max(16, now - recent[0].t) / 1000;
        const velocity = recent.reduce((sum, s) => sum + s.dy, 0) / span;
        if (Math.abs(velocity) >= tok.min_fling) {
            flick.flick(0, Math.max(-tok.max_velocity, Math.min(tok.max_velocity, velocity)));
        }
    }

    // event: WheelEvent (angleDelta, pixelDelta, phase, device)
    function wheel(event) {
        const touchpad = event.phase !== Qt.NoScrollPhase
            || (event.device && event.device.type === PointerDevice.TouchPad);
        if (!touchpad) {
            const steps = event.angleDelta.y / 120;
            if (steps !== 0) {
                const base = wheelAnimation.running ? wheelAnimation.to : flick.contentY;
                scrollTo(base - steps * tok.wheel_step);
            }
            return;
        }
        if (event.phase === Qt.ScrollEnd) {
            endGesture(true);
            return;
        }
        const dy = event.pixelDelta.y !== 0 ? event.pixelDelta.y : event.angleDelta.y / 8;
        if (event.phase === Qt.ScrollMomentum) {
            // inercia que ya da el sistema: seguirla sin estirar
            systemMomentum = true;
            flick.contentY = clampY(flick.contentY - dy);
            return;
        }
        if (!gesture || event.phase === Qt.ScrollBegin) {
            beginGesture();
        }
        virtualY -= dy;
        flick.contentY = band(virtualY);
        const now = Date.now();
        samples = samples.filter(s => now - s.t <= 150).concat([{ t: now, dy: dy }]);
        gestureTimeout.restart();
    }

    // sin ScrollEnd (algunos dispositivos): el gesto acaba al dejar de llegar eventos
    Timer {
        id: gestureTimeout
        interval: 160
        onTriggered: root.endGesture(true)
    }

    NumberAnimation {
        id: wheelAnimation
        target: flick
        property: "contentY"
        duration: root.tok.wheel_ms
        easing.type: Easing.OutCubic
    }

    // --- contenido ------------------------------------------------------------

    // Contenido con el borde de arriba difuminado (máscara de alfa)
    Item {
        id: viewport
        anchors.fill: parent
        layer.enabled: root.fadeStart < root.topInset
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: fadeMask
            // rampa suave de alfa 0 a 1: umbral 0.5 con dispersión 1
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }

        Flickable {
            id: flick
            anchors.fill: parent
            clip: true
            contentWidth: width
            contentHeight: root.topInset + holder.childrenRect.height + root.bottomInset
            // el ratón no arrastra (sí el dedo): los hijos se pueden arrastrar
            interactive: Kirigami.Settings.hasTransientTouchInput
            boundsBehavior: Flickable.DragAndOvershootBounds
            flickDeceleration: root.tok.deceleration
            maximumFlickVelocity: root.tok.max_velocity
            rebound: Transition {
                NumberAnimation {
                    properties: "x,y"
                    duration: root.tok.rebound_ms
                    easing.type: Easing.OutCubic
                }
            }
            onContentYChanged: {
                if (!root.quiet) {
                    bar.reveal();
                }
            }

            Item {
                id: holder
                y: root.topInset
                width: flick.width
                height: childrenRect.height
            }
        }
    }

    // transparente hasta fadeStart, opaca desde topInset
    Item {
        id: fadeMask
        anchors.fill: parent
        visible: false
        layer.enabled: true

        Rectangle {
            width: parent.width
            height: root.topInset
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: root.topInset > 0 ? root.fadeStart / root.topInset : 0; color: "transparent" }
                GradientStop { position: 1.0; color: "black" }
            }
        }
        Rectangle {
            y: root.topInset
            width: parent.width
            height: parent.height - root.topInset
            color: "black"
        }
    }

    // un clic durante la inercia la para, como en macOS (sin quitarle el clic a nadie)
    PointHandler {
        acceptedButtons: Qt.AllButtons
        onActiveChanged: {
            if (active && flick.flicking) {
                flick.cancelFlick();
                flick.returnToBounds();
            }
        }
    }

    // rueda y touchpad (no toma clics ni el paso del ratón)
    MouseArea {
        anchors.fill: parent
        z: 2
        acceptedButtons: Qt.NoButton
        onWheel: event => {
            root.wheel(event);
            event.accepted = true;
        }
    }

    // --- barra superpuesta ----------------------------------------------------

    Item {
        id: bar
        z: 1
        anchors.right: parent.right
        y: root.topInset
        width: root.tok.bar_hover_width + root.tok.bar_margin * 2
        height: root.height - root.topInset - root.tok.bar_margin
        visible: flick.contentHeight > flick.height + 1
        opacity: shown ? 1 : 0
        Behavior on opacity {
            NumberAnimation { duration: root.tok.bar_fade_ms; easing.type: Easing.OutCubic }
        }

        property bool shown: false
        readonly property bool expanded: barMouse.containsMouse || barMouse.dragging

        function reveal() {
            shown = true;
            hideTimer.restart();
        }

        Timer {
            id: hideTimer
            interval: root.tok.bar_hide_ms
            onTriggered: {
                if (bar.expanded || root.gesture || flick.moving || wheelAnimation.running) {
                    restart();
                } else {
                    bar.shown = false;
                }
            }
        }

        // carril: solo con el ratón encima
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: root.tok.bar_margin
            width: root.tok.bar_hover_width
            height: parent.height
            radius: width / 2
            color: Qt.alpha(Kirigami.Theme.textColor, root.tok.bar_track_alpha)
            opacity: bar.expanded ? 1 : 0
            Behavior on opacity {
                NumberAnimation { duration: root.tok.bar_fade_ms }
            }
        }

        Rectangle {
            id: thumb
            // proporción visible del contenido (lo que queda bajo topInset)
            readonly property real fraction: Math.min(1, (flick.height - root.topInset)
                                                         / Math.max(1, flick.contentHeight - root.topInset))
            readonly property real fullHeight: Math.max(root.tok.bar_min, bar.height * fraction)
            // al estirarse en un extremo, el tirador se encoge contra ese borde
            readonly property real over: flick.contentY < 0 ? -flick.contentY
                                       : flick.contentY > root.maxY ? flick.contentY - root.maxY : 0
            readonly property real travel: bar.height - fullHeight

            anchors.right: parent.right
            anchors.rightMargin: root.tok.bar_margin
            width: bar.expanded ? root.tok.bar_hover_width : root.tok.bar_width
            height: Math.max(width * 2, fullHeight * (1 - over / Math.max(1, flick.height)))
            y: root.maxY > 0 ? root.clampY(flick.contentY) / root.maxY * travel
                               + (flick.contentY > root.maxY ? fullHeight - height : 0) : 0
            radius: width / 2
            color: Qt.alpha(Kirigami.Theme.textColor, root.tok.bar_alpha)
            Behavior on width {
                NumberAnimation { duration: root.tok.bar_fade_ms; easing.type: Easing.OutCubic }
            }
        }

        MouseArea {
            id: barMouse
            anchors.fill: parent
            hoverEnabled: bar.shown
            property bool dragging: false
            property real grab: 0

            onContainsMouseChanged: if (containsMouse) bar.reveal()
            onPressed: mouse => {
                if (mouse.y >= thumb.y && mouse.y <= thumb.y + thumb.height) {
                    dragging = true;
                    grab = mouse.y - thumb.y;
                } else {
                    // clic en el carril: una página hacia ese lado
                    const page = flick.height - root.topInset;
                    root.scrollTo(flick.contentY + (mouse.y < thumb.y ? -page : page));
                }
                bar.reveal();
            }
            onPositionChanged: mouse => {
                if (dragging && thumb.travel > 0) {
                    root.jumpTo((mouse.y - grab) / thumb.travel * root.maxY);
                    bar.reveal();
                }
            }
            onReleased: dragging = false
            onCanceled: dragging = false
        }
    }
}
