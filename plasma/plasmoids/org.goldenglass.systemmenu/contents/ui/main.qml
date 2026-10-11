/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Menú del logo, como el menú Apple de macOS: acerca de, ajustes, tienda,
    forzar salida, reposo, reiniciar, apagar, bloquear y cerrar sesión.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.coreaddons as KCoreAddons
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid
import org.kde.plasma.private.sessions as Sessions

PlasmoidItem {
    id: root

    preferredRepresentation: compactRepresentation
    // Sin tooltip: en macOS el logo no lo tiene.
    toolTipMainText: ""
    toolTipSubText: ""

    property bool discoverAvailable: false
    readonly property string discoverCheck: "command -v plasma-discover"

    function run(command) {
        root.expanded = false;
        executable.exec(command);
    }

    Sessions.SessionManagement {
        id: session
    }

    KCoreAddons.KUser {
        id: user
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: (source, data) => {
            if (source === root.discoverCheck) {
                root.discoverAvailable = data["exit code"] === 0;
            }
            disconnectSource(source);
        }
        function exec(command) {
            connectSource(command);
        }
    }

    Component.onCompleted: executable.exec(root.discoverCheck)

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
            source: Plasmoid.icon
            active: compact.containsMouse || root.expanded
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 15
        Layout.preferredWidth: Kirigami.Units.gridUnit * 16
        spacing: 0

        MenuEntry {
            text: i18n("About This Computer")
            onTriggered: root.run("kinfocenter")
        }
        MenuSeparator {}
        MenuEntry {
            text: i18n("System Settings…")
            onTriggered: root.run("systemsettings")
        }
        MenuEntry {
            text: i18n("App Store…")
            visible: root.discoverAvailable
            onTriggered: root.run("plasma-discover")
        }
        MenuSeparator {}
        MenuEntry {
            // KWin convierte el cursor en una calavera: el siguiente clic cierra
            // a la fuerza esa ventana.
            text: i18n("Force Quit…")
            onTriggered: root.run("dbus-send --session --type=method_call --dest=org.kde.KWin /KWin org.kde.KWin.killWindow")
        }
        MenuSeparator {}
        MenuEntry {
            text: i18n("Sleep")
            visible: session.canSuspend
            onTriggered: {
                root.expanded = false;
                session.suspend();
            }
        }
        MenuEntry {
            text: i18n("Restart…")
            visible: session.canReboot
            onTriggered: {
                root.expanded = false;
                session.requestReboot(Sessions.SessionManagement.ConfirmationMode.ForcePrompt);
            }
        }
        MenuEntry {
            text: i18n("Shut Down…")
            visible: session.canShutdown
            onTriggered: {
                root.expanded = false;
                session.requestShutdown(Sessions.SessionManagement.ConfirmationMode.ForcePrompt);
            }
        }
        MenuSeparator {}
        MenuEntry {
            text: i18n("Lock Screen")
            visible: session.canLock
            onTriggered: {
                root.expanded = false;
                session.lock();
            }
        }
        MenuEntry {
            text: i18n("Log Out %1…", user.fullName.length > 0 ? user.fullName : user.loginName)
            visible: session.canLogout
            onTriggered: {
                root.expanded = false;
                session.requestLogout(Sessions.SessionManagement.ConfirmationMode.ForcePrompt);
            }
        }
    }

    component MenuEntry: PlasmaComponents3.ItemDelegate {
        signal triggered()
        Layout.fillWidth: true
        onClicked: triggered()
    }

    component MenuSeparator: Kirigami.Separator {
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        Layout.topMargin: Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
    }
}
