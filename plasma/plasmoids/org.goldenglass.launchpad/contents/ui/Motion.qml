/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Duraciones de las animaciones de los plasmoids: los *_ms de los tokens son
    duraciones a velocidad normal (factor 1) y pasan por aquí para seguir la
    «Velocidad de animación» global de Plasma (kdeglobals [KDE]
    AnimationDurationFactor). tools/plasmoids.py (SHARED) copia este archivo y
    su qmldir a los plasmoids que lo usan. En QML, sin import (el qmldir del
    directorio lo declara singleton):

        duration: Motion.ms(T.tokens.scroll.bar_fade_ms)

    El factor se lee de Kirigami.Units.longDuration, que Plasma calcula como
    max(1, round(200 × factor)) y actualiza en vivo cuando Ajustes del sistema
    cambia el factor (spike SP-04, docs/ARCHITECTURE.md «Movimiento»). Con el
    factor a 0 vale 1: entonces no hay animación y las duraciones son 0. Una
    animación de duración 0 termina dentro de start()/restart(): emite
    finished y ejecuta sus ScriptAction, así que los cierres de los paneles
    acaban igual. plasmashell 6.8.1 resuelve el singleton por el qmldir de
    contents/ui (probado en una sesión aislada con el dock y el Centro de
    control, también al cambiar el factor en vivo).

    Las esperas de interfaz que no son animaciones (Timer.interval,
    label_delay_ms, preview_hide_ms, bar_hide_ms, glass_update_ms) no pasan
    por aquí: no cambian con el factor.
*/

pragma Singleton

import QtQuick

import org.kde.kirigami as Kirigami

import "tokens.js" as T

QtObject {
    // velocidad global: 0.25 = cuatro veces más rápido, 2 = el doble de lento
    readonly property real factor: Kirigami.Units.longDuration / T.tokens.motion.kirigami_long_ms
    // false con «Velocidad de animación» al mínimo (sin animaciones)
    readonly property bool animated: Kirigami.Units.longDuration > 1
    // «Reduce motion»: no zooms, slides or bounces; panels only fade. Read
    // live from AccessibilitySettings, behind a Loader so that it stays false
    // without the org.goldenglass.glass module.
    readonly property Loader reduceLoader: Loader {
        source: "MotionReduce.qml"
    }
    readonly property bool reduced: reduceLoader.item ? reduceLoader.item.reduceMotion : false

    // fundidos y colores: duración × factor (0 sin animaciones)
    function ms(base) {
        return animated ? base * factor : 0;
    }

    // movimiento (escala, desplazamiento, resorte): 0 con «Reducir movimiento»
    function moveMs(base) {
        return reduced ? 0 : ms(base);
    }

    // fundido de una transición que además se mueve: con «Reducir
    // movimiento» el movimiento desaparece y queda un fundido de
    // motion.reduced_fade_ms, para que el cambio se siga viendo
    function fadeMs(base) {
        return ms(reduced ? T.tokens.motion.reduced_fade_ms : base);
    }

    // overshoot de Easing.OutBack (rebote al asentarse): 0 con «Reducir movimiento»
    function overshoot(value) {
        return reduced ? 0 : value;
    }
}
