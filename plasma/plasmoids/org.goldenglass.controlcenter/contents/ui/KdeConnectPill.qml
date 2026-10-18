/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    KDE Connect en el hueco de AirDrop: encendido si hay algún dispositivo
    emparejado al alcance. Abre los ajustes de KDE Connect. main.qml lo carga
    con un Loader: sin KDE Connect instalado, el import falla y la píldora no
    aparece, sin romper el resto.
*/

import QtQuick

import org.kde.kdeconnect as KDEConnect

PillToggle {
    id: pill

    signal activated()

    KDEConnect.DevicesModel {
        id: devices
        displayFilter: KDEConnect.DevicesModel.Paired | KDEConnect.DevicesModel.Reachable
    }

    iconName: "kdeconnect-tray-symbolic"
    title: i18n("Connect")
    checked: devices.count > 0
    subtitle: devices.count === 0 ? i18n("No devices")
            : devices.count === 1 ? devices.data(devices.index(0, 0), Qt.DisplayRole)
            : i18np("%1 device", "%1 devices", devices.count)
    hasDetail: true

    function open() {
        KDEConnect.OpenConfig.openConfiguration();
        activated();
    }
    onToggled: open()
    onDetailRequested: open()
}
