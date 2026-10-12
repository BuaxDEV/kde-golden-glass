/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Papelera del dock, como la de macOS. La de Plasma pide el icono simbólico
    dentro de un panel; esta usa el icono a color del tema (vacía o llena).
    Todo el comportamiento está en TrashButton.qml, que comparte con el dock.
*/

import QtQuick

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    // la representación es un Component: su id no se ve desde aquí
    property Item trash

    preferredRepresentation: fullRepresentation
    toolTipMainText: i18n("Trash")
    toolTipSubText: trash && trash.hasContents ? i18np("%1 item", "%1 items", trash.count) : i18n("Empty")
    Plasmoid.icon: trash ? trash.iconName : "user-trash"
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    fullRepresentation: TrashButton {
        Component.onCompleted: root.trash = this
    }
}
