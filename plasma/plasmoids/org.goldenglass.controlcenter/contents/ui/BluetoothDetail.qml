/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Bluetooth en detalle, como en macOS 26: interruptor y dispositivos
    emparejados; un clic conecta o desconecta.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.bluezqt as BluezQt
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import "tokens.js" as T

DetailView {
    id: view

    signal enableRequested(bool enable)
    signal settingsRequested()

    readonly property var pairedDevices: BluezQt.Manager.devices.filter(device => device.paired)

    title: i18n("Bluetooth")
    hasSwitch: true
    switchEnabled: BluezQt.Manager.adapters.length > 0 || BluezQt.Manager.bluetoothBlocked
    checked: BluezQt.Manager.bluetoothOperational
    footerText: i18n("Bluetooth Settings…")
    onToggled: enableRequested(!BluezQt.Manager.bluetoothOperational)
    onFooterClicked: settingsRequested()

    SectionLabel {
        visible: view.checked
        text: i18n("Devices")
    }
    Repeater {
        model: view.checked ? view.pairedDevices : []
        delegate: DetailRow {
            id: deviceRow
            required property var modelData
            property bool connecting: false
            // la llamada en curso; Connections es hijo del delegado: si este se
            // destruye antes de que acabe, la conexión desaparece con él
            property QtObject pendingCall: null

            text: modelData.name
            iconName: modelData.icon.length > 0 ? modelData.icon + "-symbolic" : "network-bluetooth-symbolic"
            active: modelData.connected
            subtitle: modelData.connected ? i18n("Connected") : ""
            busy: connecting
            onClicked: {
                connecting = true;
                pendingCall = modelData.connected ? modelData.disconnectFromDevice() : modelData.connectToDevice();
            }

            Connections {
                target: deviceRow.pendingCall
                function onFinished() {
                    deviceRow.connecting = false;
                    deviceRow.pendingCall = null;
                }
            }
        }
    }
    PlasmaComponents3.Label {
        visible: view.checked && view.pairedDevices.length === 0
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.smallSpacing
        text: i18n("No paired devices")
        opacity: T.tokens.text.secondary_alpha
        textFormat: Text.PlainText
    }
}
