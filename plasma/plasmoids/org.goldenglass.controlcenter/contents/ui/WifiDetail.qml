/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Wi‑Fi en detalle, como en macOS 26: interruptor, redes conocidas y otras
    redes. Un clic conecta (o desconecta la red activa); una red protegida
    nueva pide la contraseña en la propia fila. La lógica de conexión es la del
    applet de redes de Plasma (ConnectionItemDelegate de plasma-nm).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.networkmanagement as PlasmaNM

DetailView {
    id: view

    required property var handler
    required property var enabledConnections
    required property var networkModel

    signal settingsRequested()

    // red que está pidiendo contraseña (SpecificPath del punto de acceso)
    property string passwordFor: ""

    title: i18n("Wi‑Fi")
    hasSwitch: true
    switchEnabled: enabledConnections.wirelessHwEnabled
    checked: enabledConnections.wirelessEnabled && enabledConnections.wirelessHwEnabled
    footerText: i18n("Wi‑Fi Settings…")
    onToggled: handler.enableWireless(!enabledConnections.wirelessEnabled)
    onFooterClicked: settingsRequested()

    Component.onCompleted: handler.requestScan()

    PlasmaNM.AppletProxyModel {
        id: connections
        sourceModel: view.networkModel
    }

    function signalIcon(strength) {
        return strength >= 80 ? "network-wireless-signal-excellent-symbolic"
             : strength >= 55 ? "network-wireless-signal-good-symbolic"
             : strength >= 30 ? "network-wireless-signal-ok-symbolic"
             : strength >= 5 ? "network-wireless-signal-weak-symbolic"
             : "network-wireless-signal-none-symbolic";
    }

    component Network: ColumnLayout {
        id: network

        required property var model
        required property bool known

        readonly property bool wireless: model.Type === PlasmaNM.Enums.Wireless
        readonly property bool secure: model.SecurityType !== PlasmaNM.Enums.NoneSecurity
        // contraseña que se puede pedir aquí; las de empresa las pide NetworkManager
        readonly property bool simplePassword: model.SecurityType === PlasmaNM.Enums.StaticWep
                                               || model.SecurityType === PlasmaNM.Enums.WpaPsk
                                               || model.SecurityType === PlasmaNM.Enums.Wpa2Psk
                                               || model.SecurityType === PlasmaNM.Enums.SAE
        readonly property bool askingPassword: view.passwordFor === model.SpecificPath

        visible: view.checked && wireless && (model.Uuid.length > 0) === known
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        DetailRow {
            text: network.model.ItemUniqueName
            iconName: view.signalIcon(network.model.Signal)
            active: network.model.ConnectionState === PlasmaNM.Enums.Activated
            busy: network.model.ConnectionState === PlasmaNM.Enums.Activating
            trailingIcon: network.secure ? "object-locked-symbolic" : ""
            onClicked: {
                const m = network.model;
                if (m.ConnectionState === PlasmaNM.Enums.Activated) {
                    view.handler.deactivateConnection(m.ConnectionPath, m.DevicePath);
                } else if (m.Uuid.length > 0) {
                    view.handler.activateConnection(m.ConnectionPath, m.DevicePath, m.SpecificPath);
                } else if (network.simplePassword) {
                    view.passwordFor = network.askingPassword ? "" : m.SpecificPath;
                } else {
                    view.handler.addAndActivateConnection(m.DevicePath, m.SpecificPath);
                }
            }
        }

        PlasmaComponents3.TextField {
            id: password
            visible: network.askingPassword
            Layout.fillWidth: true
            Layout.leftMargin: Kirigami.Units.smallSpacing
            Layout.rightMargin: Kirigami.Units.smallSpacing
            echoMode: TextInput.Password
            placeholderText: i18n("Password")
            onVisibleChanged: if (visible) forceActiveFocus()
            onAccepted: {
                view.handler.addAndActivateConnection(network.model.DevicePath, network.model.SpecificPath, text);
                text = "";
                view.passwordFor = "";
            }
        }
    }

    SectionLabel {
        visible: view.checked
        text: i18n("Known Networks")
    }
    Repeater {
        model: connections
        delegate: Network {
            known: true
        }
    }

    SectionLabel {
        visible: view.checked
        text: i18n("Other Networks")
    }
    Repeater {
        model: connections
        delegate: Network {
            known: false
        }
    }
}
