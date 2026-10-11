/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Centro de control, como el de macOS: conectividad, modo oscuro, No
    molestar, brillo, sonido, vidrio y lo que se está reproduciendo. Toda la
    lógica es la de los módulos de Plasma (networkmanagement, bluezqt,
    brightnesscontrolplugin, volume, notificationmanager, mpris).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.bluezqt as BluezQt
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami
import org.kde.notificationmanager as NotificationManager
import org.kde.plasma.networkmanagement as PlasmaNM
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid
import org.kde.plasma.private.brightnesscontrolplugin as Brightness
import org.kde.plasma.private.mpris as Mpris
import org.kde.plasma.private.volume as Volume

PlasmoidItem {
    id: root

    preferredRepresentation: compactRepresentation
    toolTipMainText: i18n("Control Center")
    toolTipSubText: ""

    // --- Vidrio (goldenglass-glass) -------------------------------------------
    property bool glassAvailable: false
    property real glassLevel: 0.5
    readonly property string glassCheck: "command -v goldenglass-glass"
    readonly property string glassGet: "goldenglass-glass --get"

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: (source, data) => {
            if (source === root.glassCheck) {
                root.glassAvailable = data["exit code"] === 0;
                if (root.glassAvailable) {
                    exec(root.glassGet);
                }
            } else if (source === root.glassGet && data["exit code"] === 0) {
                root.glassLevel = parseFloat(data["stdout"]);
            }
            disconnectSource(source);
        }
        function exec(command) {
            connectSource(command);
        }
    }

    onExpandedChanged: {
        if (expanded && glassAvailable) {
            executable.exec(glassGet);
        }
    }
    Component.onCompleted: executable.exec(glassCheck)

    // --- Red y Bluetooth ------------------------------------------------------
    PlasmaNM.EnabledConnections {
        id: enabledConnections
    }
    PlasmaNM.NetworkStatus {
        id: networkStatus
    }
    PlasmaNM.Handler {
        id: networkHandler
    }

    readonly property int connectedBluetoothDevices: BluezQt.Manager.devices.filter(device => device.connected).length

    function setBluetoothEnabled(enable) {
        BluezQt.Manager.bluetoothBlocked = !enable;
        BluezQt.Manager.adapters.forEach(adapter => {
            adapter.powered = enable;
        });
    }

    // --- No molestar ----------------------------------------------------------
    NotificationManager.Settings {
        id: notificationSettings
    }
    readonly property bool doNotDisturb: {
        const until = notificationSettings.notificationsInhibitedUntil;
        return (until !== undefined && !isNaN(until.getTime()) && until.getTime() > Date.now())
            || notificationSettings.notificationsInhibitedByApplication;
    }
    function setDoNotDisturb(enable) {
        if (enable) {
            const until = new Date();
            until.setFullYear(until.getFullYear() + 1);
            notificationSettings.notificationsInhibitedUntil = until;
        } else {
            notificationSettings.notificationsInhibitedUntil = undefined;
            notificationSettings.revokeApplicationInhibitions();
        }
        notificationSettings.save();
    }

    // --- Brillo y multimedia --------------------------------------------------
    Brightness.ScreenBrightnessControl {
        id: brightnessControl
        isSilent: false
    }
    Mpris.Mpris2Model {
        id: mpris
    }

    compactRepresentation: MouseArea {
        id: compact
        hoverEnabled: true
        Layout.minimumWidth: Kirigami.Units.iconSizes.small
        Layout.preferredWidth: height
        onClicked: root.expanded = !root.expanded

        Kirigami.Icon {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.small
            height: width
            source: Qt.resolvedUrl("../images/controlcenter-symbolic.svg")
            isMask: true
            color: Kirigami.Theme.textColor
            active: compact.containsMouse || root.expanded
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        Layout.preferredWidth: Kirigami.Units.gridUnit * 21
        spacing: Kirigami.Units.largeSpacing

        // Conectividad | modo oscuro + No molestar
        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing

            Tile {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true

                ToggleRow {
                    Layout.fillWidth: true
                    iconName: "network-wireless-symbolic"
                    title: i18n("Wi‑Fi")
                    available: enabledConnections.wirelessHwEnabled
                    checked: enabledConnections.wirelessEnabled && enabledConnections.wirelessHwEnabled
                    subtitle: !enabledConnections.wirelessHwEnabled ? i18n("Not available")
                            : !checked ? i18n("Off")
                            // «Wifi: Conectado a X» → «Conectado a X»
                            : networkStatus.activeConnections.split("\n")[0].replace(/^[^:]+:\s*/, "")
                    hasSettings: true
                    onToggled: networkHandler.enableWireless(!enabledConnections.wirelessEnabled)
                    onSettingsRequested: {
                        root.expanded = false;
                        KCMUtils.KCMLauncher.openSystemSettings("kcm_networkmanagement");
                    }
                }
                ToggleRow {
                    Layout.fillWidth: true
                    iconName: "network-bluetooth-symbolic"
                    title: i18n("Bluetooth")
                    available: BluezQt.Manager.adapters.length > 0 || BluezQt.Manager.bluetoothBlocked
                    checked: BluezQt.Manager.bluetoothOperational
                    subtitle: !available ? i18n("Not available")
                            : !checked ? i18n("Off")
                            : root.connectedBluetoothDevices > 0 ? i18np("%1 device connected", "%1 devices connected", root.connectedBluetoothDevices)
                            : i18n("On")
                    hasSettings: true
                    onToggled: root.setBluetoothEnabled(!BluezQt.Manager.bluetoothOperational)
                    onSettingsRequested: {
                        root.expanded = false;
                        KCMUtils.KCMLauncher.openSystemSettings("kcm_bluetooth");
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: Kirigami.Units.largeSpacing

                Tile {
                    Layout.fillWidth: true
                    ToggleRow {
                        Layout.fillWidth: true
                        iconName: "weather-clear-night-symbolic"
                        title: i18n("Dark Mode")
                        subtitle: checked ? i18n("On") : i18n("Off")
                        checked: Brightness.DarkModeControl.darkMode
                        onToggled: Brightness.DarkModeControl.darkMode = !Brightness.DarkModeControl.darkMode
                    }
                }
                Tile {
                    Layout.fillWidth: true
                    ToggleRow {
                        Layout.fillWidth: true
                        iconName: "notifications-disabled-symbolic"
                        title: i18n("Do Not Disturb")
                        subtitle: checked ? i18n("On") : i18n("Off")
                        checked: root.doNotDisturb
                        onToggled: root.setDoNotDisturb(!root.doNotDisturb)
                    }
                }
            }
        }

        // Brillo (una tarjeta por pantalla que lo permita, p. ej. DDC/CI)
        Repeater {
            model: brightnessControl.isBrightnessAvailable ? brightnessControl.displays : null
            delegate: SliderTile {
                id: brightnessTile
                required property string displayName
                required property string label
                required property int brightness
                required property int maxBrightness

                Layout.fillWidth: true
                title: brightnessControl.displays.rowCount() > 1 ? label : i18n("Display")
                iconName: "brightness-high-symbolic"
                from: 0
                to: maxBrightness
                onMoved: brightnessControl.setBrightness(displayName, Math.round(value))

                Binding on value {
                    value: brightnessTile.brightness
                    when: !brightnessTile.pressed
                }
            }
        }

        // Sonido
        SliderTile {
            id: soundTile
            readonly property var sink: Volume.PreferredDevice.sink
            visible: sink !== null
            Layout.fillWidth: true
            title: i18n("Sound")
            iconName: sink && (sink.muted || sink.volume === 0) ? "audio-volume-muted-symbolic" : "audio-volume-high-symbolic"
            iconClickable: true
            from: Volume.PulseAudio.MinimalVolume
            to: Volume.PulseAudio.NormalVolume
            onMoved: {
                sink.muted = false;
                sink.volume = Math.round(value);
            }
            onIconClicked: sink.muted = !sink.muted

            Binding on value {
                value: soundTile.sink ? soundTile.sink.volume : 0
                when: !soundTile.pressed
            }
        }

        // Vidrio (macOS 27): se aplica al soltar
        SliderTile {
            id: glassTile
            visible: root.glassAvailable
            Layout.fillWidth: true
            title: i18n("Glass")
            iconName: "preferences-desktop-theme-global-symbolic"
            from: 0
            to: 1
            onReleased: {
                root.glassLevel = value;
                executable.exec("goldenglass-glass --level " + value.toFixed(3));
            }

            Binding on value {
                value: root.glassLevel
                when: !glassTile.pressed
            }
        }

        // Lo que se está reproduciendo
        NowPlaying {
            Layout.fillWidth: true
            visible: player !== null && player !== undefined
            player: mpris.currentPlayer
        }
    }
}
