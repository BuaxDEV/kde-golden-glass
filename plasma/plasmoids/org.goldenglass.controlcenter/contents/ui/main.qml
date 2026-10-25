/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Control Center, as in macOS 26: a 4-column grid with pills (Wi‑Fi,
    Bluetooth, KDE Connect, Focus), Now Playing, round buttons (screen
    mirroring, screenshot, dark mode, night light) and, full width, Display,
    Sound and Glass. As in macOS, the tiles lie loose on the desktop, each one
    of glass (GlassOverlay), without a Plasma popup: the menu bar icon is the
    "full" representation. All the logic is that of the Plasma modules
    (networkmanagement, bluezqt, brightnesscontrolplugin, volume,
    notificationmanager, mpris, kdeconnect) and of KWin (night light).
*/

import QtQuick
import QtQuick.Layouts

import org.kde.bluezqt as BluezQt
import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.networkmanagement as PlasmaNM
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid
import org.kde.plasma.private.brightnesscontrolplugin as Brightness
import org.kde.plasma.private.mpris as Mpris
import org.kde.plasma.private.volume as Volume
import org.kde.plasma.workspace.dbus as DBus

import "tokens.js" as T

PlasmoidItem {
    id: root

    readonly property var cc: T.tokens.control_center

    // El icono es la representación «completa»: Plasma no abre su popup
    preferredRepresentation: fullRepresentation
    toolTipMainText: i18n("Control Center")
    toolTipSubText: ""

    // --- Órdenes (goldenglass-glass, kwriteconfig6, spectacle) ---------------
    property bool glassAvailable: false
    property real glassLevel: T.tokens.glass.default_level
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

    function refreshGlassLevel() {
        if (glassAvailable) {
            executable.exec(glassGet);
        }
    }
    Component.onCompleted: executable.exec(glassCheck)

    // --- Abrir y cerrar -------------------------------------------------------
    GlassOverlay {
        id: panel
        tokens: root.cc
        content: panelContent
        anchorItem: root.fullRepresentationItem
        onOpened: root.refreshGlassLevel()
    }

    function toggle() {
        panel.toggle();
    }

    function close() {
        panel.close();
    }

    // --- Volume and brightness HUD ----------------------------------------------
    // Under the menu bar of this screen, in place of Plasma's OSD. Hud.qml needs
    // the org.goldenglass.glass module: without it only that file fails and
    // Plasma's OSD stays.
    Loader {
        id: hud
        source: "Hud.qml"
    }
    Binding {
        target: hud.item
        when: hud.item !== null
        property: "menuBarHeight"
        value: panel.menuBarHeight
    }
    Binding {
        target: hud.item
        when: hud.item !== null
        property: "controlCenterOpen"
        value: panel.visible
    }

    // atajo de teclado del plasmoide
    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.toggle();
        }
    }

    // --- Red y Bluetooth ------------------------------------------------------
    PlasmaNM.EnabledConnections {
        id: enabledConnections
    }
    PlasmaNM.Handler {
        id: networkHandler
    }
    // Nombre de la red Wi‑Fi activa, como en macOS («SOAP02»)
    property string wifiName: ""
    PlasmaNM.NetworkModel {
        id: networkModel
    }
    Instantiator {
        id: networkWatcher
        model: networkModel
        delegate: QtObject {
            readonly property bool activeWifi: model.ConnectionState === PlasmaNM.Enums.Activated
                                               && model.Type === PlasmaNM.Enums.Wireless
            readonly property string ssid: model.Ssid
            onActiveWifiChanged: root.updateWifiName()
            onSsidChanged: root.updateWifiName()
        }
        onObjectAdded: root.updateWifiName()
        onObjectRemoved: root.updateWifiName()
    }
    function updateWifiName() {
        for (let i = 0; i < networkWatcher.count; ++i) {
            const connection = networkWatcher.objectAt(i);
            if (connection && connection.activeWifi) {
                wifiName = connection.ssid;
                return;
            }
        }
        wifiName = "";
    }

    readonly property var connectedBluetoothDevices: BluezQt.Manager.devices.filter(device => device.connected)

    function setBluetoothEnabled(enable) {
        BluezQt.Manager.bluetoothBlocked = !enable;
        BluezQt.Manager.adapters.forEach(adapter => {
            adapter.powered = enable;
        });
    }

    // --- Do Not Disturb -------------------------------------------------------
    DoNotDisturb {
        id: doNotDisturbState
    }

    // --- Luz nocturna (KWin) --------------------------------------------------
    // Como Night Shift: el botón la enciende o apaga de verdad (kwinrc), no
    // solo la suspende. Si otro la suspendió, reanudarla cuenta como encender.
    DBus.Properties {
        id: nightLight
        busType: DBus.BusType.Session
        service: "org.kde.KWin.NightLight"
        path: "/org/kde/KWin/NightLight"
        iface: "org.kde.KWin.NightLight"
    }
    readonly property bool nightLightAvailable: nightLight.properties.available === true
    readonly property bool nightLightOn: nightLight.properties.enabled === true && nightLight.properties.inhibited !== true
    function toggleNightLight() {
        if (nightLightOn) {
            executable.exec("kwriteconfig6 --file kwinrc --group NightColor --key Active false --notify");
        } else if (nightLight.properties.enabled === true && Brightness.NightLightInhibitor.inhibited) {
            Brightness.NightLightInhibitor.toggleInhibition();
        } else {
            executable.exec("kwriteconfig6 --file kwinrc --group NightColor --key Active true --notify");
        }
    }

    // --- Sonido ----------------------------------------------------------------
    // Tope del volumen: el de Plasma (150 % con «Subir el volumen máximo»)
    Volume.GlobalConfig {
        id: volumeConfig
    }
    readonly property int maxVolume: volumeConfig.raiseMaximumVolume ? Volume.PulseAudio.MaximalVolume
                                                                     : Volume.PulseAudio.NormalVolume

    // --- Brillo y multimedia --------------------------------------------------
    Brightness.ScreenBrightnessControl {
        id: brightnessControl
        isSilent: false
    }
    Mpris.Mpris2Model {
        id: mpris
    }

    // selector de pantallas de KScreen (el de Meta+P)
    function showScreenMirroring() {
        root.close();
        DBus.SessionBus.asyncCall({
            service: "org.kde.kscreen.osdService",
            path: "/org/kde/kscreen/osdService",
            iface: "org.kde.kscreen.osdService",
            member: "showActionSelector",
        });
    }

    function openSettings(module) {
        root.close();
        KCMUtils.KCMLauncher.openSystemSettings(module);
    }

    // Menu bar icon; while open, with the highlight of the macOS menus
    fullRepresentation: MouseArea {
        id: icon
        hoverEnabled: true
        Layout.minimumWidth: Kirigami.Units.iconSizes.small
        Layout.preferredWidth: height
        onClicked: root.toggle()

        Rectangle {
            anchors.centerIn: parent
            width: parent.width + 2 * root.cc.icon_highlight_padding
            // inset from the bar the icon is in (its panel window), whatever its height
            height: Math.min(parent.height, Window.height - 2 * root.cc.icon_highlight_inset)
            radius: root.cc.icon_highlight_radius
            color: Qt.alpha(Kirigami.Theme.textColor, root.cc.icon_highlight_alpha)
            visible: panel.visible
        }

        Kirigami.Icon {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.small
            height: width
            source: Qt.resolvedUrl("../images/controlcenter-symbolic.svg")
            isMask: true
            color: Kirigami.Theme.textColor
        }
    }

    // Content of the GlassOverlay: the grid or, after clicking a module, its
    // detail view (as in macOS 26)
    Component {
        id: panelContent

        Item {
            id: contentRoot

            // "" = cuadrícula; wifi, bluetooth, focus, display, sound, nowplaying
            property string detail: ""

            implicitWidth: detail !== "" ? detailView.implicitWidth : gridView.implicitWidth
            implicitHeight: detail !== "" ? detailView.implicitHeight : gridView.implicitHeight

            // every opening starts at the grid
            function resetContent() {
                detail = "";
            }

            // Esc goes back from a detail view to the grid before closing
            function goBack() {
                if (detail === "") {
                    return false;
                }
                detail = "";
                return true;
            }

            // la vista que entra (detalle o cuadrícula) brota con el mismo
            // resorte que el Centro de control al abrirse; con la ventana
            // oculta (al reabrir vuelve a la cuadrícula) cambia sin animar
            onDetailChanged: {
                switchView.stop();
                const shown = detail !== "" ? detailView : gridView;
                if (Window.window && Window.window.visible) {
                    switchView.target = shown;
                    switchView.restart();
                } else {
                    shown.opacity = 1;
                    shown.scale = 1;
                }
            }

            Loader {
                id: detailView
                active: contentRoot.detail !== ""
                transformOrigin: Item.Top
                sourceComponent: ({
                    wifi: wifiDetail,
                    bluetooth: bluetoothDetail,
                    focus: focusDetail,
                    display: displayDetail,
                    sound: soundDetail,
                    nowplaying: nowPlayingDetail,
                })[contentRoot.detail] ?? null
            }
            ParallelAnimation {
                id: switchView
                property Item target
                NumberAnimation {
                    target: switchView.target
                    property: "opacity"
                    from: 0
                    to: 1
                    duration: Motion.fadeMs(root.cc.open_fade_ms)
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: switchView.target
                    property: "scale"
                    from: root.cc.switch_scale
                    to: 1
                    duration: Motion.moveMs(root.cc.open_ms)
                    easing.type: Easing.OutBack
                    easing.overshoot: Motion.overshoot(root.cc.open_overshoot)
                }
            }

            ColumnLayout {
                id: gridView
                visible: contentRoot.detail === ""
                transformOrigin: Item.Top
                spacing: root.cc.gap

                GridLayout {
                    id: grid
                    readonly property bool hasKdeConnect: kdeConnect.status === Loader.Ready

                    columns: 4
                    rowSpacing: root.cc.gap
                    columnSpacing: root.cc.gap

                    PillToggle {
                        Layout.row: 0
                        Layout.column: 0
                        Layout.columnSpan: 2
                        iconName: "network-wireless-symbolic"
                        title: i18n("Wi‑Fi")
                        available: enabledConnections.wirelessHwEnabled
                        checked: enabledConnections.wirelessEnabled && enabledConnections.wirelessHwEnabled
                        subtitle: !enabledConnections.wirelessHwEnabled ? i18n("Not available")
                                : !checked ? i18n("Off")
                                : root.wifiName.length > 0 ? root.wifiName : i18n("Not connected")
                        hasDetail: true
                        onToggled: networkHandler.enableWireless(!enabledConnections.wirelessEnabled)
                        onDetailRequested: contentRoot.detail = "wifi"
                    }

                    NowPlaying {
                        Layout.row: 0
                        Layout.column: 2
                        Layout.rowSpan: 2
                        Layout.columnSpan: 2
                        player: mpris.currentPlayer ?? null
                        onDetailRequested: contentRoot.detail = "nowplaying"
                    }

                    PillToggle {
                        Layout.row: 1
                        Layout.column: 0
                        Layout.columnSpan: 2
                        iconName: "network-bluetooth-symbolic"
                        title: i18n("Bluetooth")
                        available: BluezQt.Manager.adapters.length > 0 || BluezQt.Manager.bluetoothBlocked
                        checked: BluezQt.Manager.bluetoothOperational
                        subtitle: !available ? i18n("Not available")
                                : !checked ? i18n("Off")
                                : root.connectedBluetoothDevices.length === 1 ? root.connectedBluetoothDevices[0].name
                                : root.connectedBluetoothDevices.length > 1 ? i18np("%1 device", "%1 devices", root.connectedBluetoothDevices.length)
                                : i18n("On")
                        hasDetail: true
                        onToggled: root.setBluetoothEnabled(!BluezQt.Manager.bluetoothOperational)
                        onDetailRequested: contentRoot.detail = "bluetooth"
                    }

                    // KDE Connect en el hueco de AirDrop; sin él, Enfoque ocupa su sitio
                    Loader {
                        id: kdeConnect
                        Layout.row: 2
                        Layout.column: 0
                        Layout.columnSpan: 2
                        visible: grid.hasKdeConnect
                        source: Qt.resolvedUrl("KdeConnectPill.qml")
                    }
                    Connections {
                        target: kdeConnect.item
                        function onActivated() {
                            root.close();
                        }
                    }

                    CircleButton {
                        Layout.row: 2
                        Layout.column: 2
                        tile: true
                        isToggle: false
                        diameter: root.cc.cell
                        glyphSize: root.cc.round_icon
                        iconName: Qt.resolvedUrl("../images/screen-mirroring-symbolic.svg")
                        toolTip: i18n("Screen Mirroring")
                        onClicked: root.showScreenMirroring()
                    }
                    CircleButton {
                        Layout.row: 2
                        Layout.column: 3
                        tile: true
                        isToggle: false
                        diameter: root.cc.cell
                        glyphSize: root.cc.round_icon
                        iconName: Qt.resolvedUrl("../images/screenshot-symbolic.svg")
                        toolTip: i18n("Screenshot")
                        onClicked: {
                            root.close();
                            executable.exec("spectacle --launchonly");
                        }
                    }

                    CircleButton {
                        Layout.row: 3
                        Layout.column: 0
                        tile: true
                        diameter: root.cc.cell
                        glyphSize: root.cc.round_icon
                        iconName: Qt.resolvedUrl("../images/dark-mode-symbolic.svg")
                        toolTip: i18n("Dark Mode")
                        active: Brightness.DarkModeControl.darkMode
                        onClicked: Brightness.DarkModeControl.darkMode = !Brightness.DarkModeControl.darkMode
                    }
                    CircleButton {
                        Layout.row: 3
                        Layout.column: 1
                        visible: root.nightLightAvailable
                        tile: true
                        diameter: root.cc.cell
                        glyphSize: root.cc.round_icon
                        iconName: "redshift-status-on"
                        toolTip: i18n("Night Light")
                        active: root.nightLightOn
                        onClicked: root.toggleNightLight()
                    }

                    PillToggle {
                        Layout.row: grid.hasKdeConnect ? 3 : 2
                        Layout.column: grid.hasKdeConnect ? 2 : 0
                        Layout.columnSpan: 2
                        iconName: "weather-clear-night-symbolic"
                        title: i18n("Focus")
                        subtitle: checked ? i18n("Do Not Disturb") : ""
                        checked: doNotDisturbState.active
                        hasDetail: true
                        onToggled: doNotDisturbState.setActive(!doNotDisturbState.active)
                        onDetailRequested: contentRoot.detail = "focus"
                    }
                }

                // Pantalla: un slider por pantalla que lo permita (p. ej. DDC/CI),
                // con su nombre debajo del título si hay varias
                SliderTile {
                    Layout.fillWidth: true
                    visible: displays.count > 0
                    title: i18n("Display")
                    hasDetail: true
                    onDetailRequested: contentRoot.detail = "display"

                    Repeater {
                        id: displays
                        model: brightnessControl.isBrightnessAvailable ? brightnessControl.displays : null
                        delegate: ColumnLayout {
                            id: display
                            required property string displayName
                            required property string label
                            required property int brightness
                            required property int maxBrightness

                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            PlasmaComponents3.Label {
                                Layout.fillWidth: true
                                visible: displays.count > 1
                                text: display.label
                                opacity: T.tokens.text.secondary_alpha
                                font: Kirigami.Theme.smallFont
                                elide: Text.ElideRight
                                textFormat: Text.PlainText
                            }
                            SliderRow {
                                id: brightnessRow
                                Layout.fillWidth: true
                                iconFrom: "brightness-low-symbolic"
                                iconTo: "brightness-high-symbolic"
                                from: 0
                                to: display.maxBrightness
                                onMoved: brightnessControl.setBrightness(display.displayName, Math.round(value))

                                Binding on value {
                                    value: display.brightness
                                    when: !brightnessRow.pressed
                                }
                            }
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
                    hasDetail: true
                    onDetailRequested: contentRoot.detail = "sound"

                    SliderRow {
                        id: soundRow
                        Layout.fillWidth: true
                        iconFrom: soundTile.sink && (soundTile.sink.muted || soundTile.sink.volume === 0) ? "audio-volume-muted-symbolic" : "audio-volume-low-symbolic"
                        iconTo: "audio-volume-high-symbolic"
                        iconClickable: true
                        trailingIcon: "audio-speakers-symbolic"
                        trailingToolTip: i18n("Sound Output")
                        from: Volume.PulseAudio.MinimalVolume
                        to: root.maxVolume
                        onMoved: {
                            soundTile.sink.muted = false;
                            soundTile.sink.volume = Math.round(value);
                        }
                        onIconClicked: soundTile.sink.muted = !soundTile.sink.muted
                        onTrailingClicked: contentRoot.detail = "sound"

                        Binding on value {
                            value: soundTile.sink ? soundTile.sink.volume : 0
                            when: !soundRow.pressed
                        }
                    }
                }

                // Vidrio (macOS 27): se aplica al soltar
                SliderTile {
                    visible: root.glassAvailable
                    Layout.fillWidth: true
                    title: i18n("Glass")

                    SliderRow {
                        id: glassRow
                        Layout.fillWidth: true
                        // «Reduce transparency» keeps the level but makes the glass opaque
                        enabled: !Accessibility.reduceTransparency
                        iconFrom: Qt.resolvedUrl("../images/glass-low-symbolic.svg")
                        iconTo: Qt.resolvedUrl("../images/glass-high-symbolic.svg")
                        from: 0
                        to: 1
                        onReleased: {
                            root.glassLevel = value;
                            executable.exec("goldenglass-glass --level " + value.toFixed(3));
                        }

                        Binding on value {
                            value: root.glassLevel
                            when: !glassRow.pressed
                        }
                    }
                }
            }
        }
    }

    // --- Vistas de detalle ----------------------------------------------------
    Component {
        id: wifiDetail
        WifiDetail {
            handler: networkHandler
            enabledConnections: enabledConnections
            networkModel: networkModel
            onSettingsRequested: root.openSettings("kcm_networkmanagement")
        }
    }
    Component {
        id: bluetoothDetail
        BluetoothDetail {
            onEnableRequested: enable => root.setBluetoothEnabled(enable)
            onSettingsRequested: root.openSettings("kcm_bluetooth")
        }
    }
    Component {
        id: focusDetail
        FocusDetail {
            doNotDisturb: doNotDisturbState.active
            onUntilRequested: until => doNotDisturbState.setActiveUntil(until)
            onSettingsRequested: root.openSettings("kcm_notifications")
        }
    }
    Component {
        id: displayDetail
        DisplayDetail {
            brightnessControl: brightnessControl
            nightLightAvailable: root.nightLightAvailable
            nightLightOn: root.nightLightOn
            onNightLightToggled: root.toggleNightLight()
            onMirroringRequested: root.showScreenMirroring()
            onSettingsRequested: root.openSettings("kcm_kscreen")
        }
    }
    Component {
        id: soundDetail
        SoundDetail {
            maxVolume: root.maxVolume
            onSettingsRequested: root.openSettings("kcm_pulseaudio")
        }
    }
    Component {
        id: nowPlayingDetail
        NowPlayingDetail {
            player: mpris.currentPlayer ?? null
            onRaised: root.close()
        }
    }
}
