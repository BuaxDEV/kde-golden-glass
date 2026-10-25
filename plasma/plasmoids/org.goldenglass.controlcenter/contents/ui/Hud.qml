/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Volume and brightness HUD, as in macOS 27: a glass pill under the menu
    bar, against the right edge of the screen, with the icon and a segmented
    bar, no percentage. It springs in, stays osd.timeout_ms after the last
    change and fades out.

    OsdHost (org.goldenglass.glass) takes plasmashell's volume, microphone,
    media player and brightness OSDs off Plasma and hands each one to the HUD
    of one screen: the one with the active window, or the screen whose
    brightness changed. main.qml loads this file with a Loader: without the
    module only this file fails and Plasma's OSD stays.
*/

import QtQuick

import org.goldenglass.glass
import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.taskmanager as TaskManager

import "tokens.js" as T

Item {
    id: hud

    // Real height of the menu bar on this screen (GlassOverlay.menuBarHeight)
    property real menuBarHeight: 0
    // The Control Center is open on this screen: no HUD over it
    property bool controlCenterOpen: false

    readonly property var osd: T.tokens.osd
    readonly property rect screen: Plasmoid.containment ? Plasmoid.containment.screenGeometry : Qt.rect(0, 0, 0, 0)
    // a menu bar that hides itself takes nothing: the HUD keeps clear of it anyway
    readonly property real barEdge: Math.max(menuBarHeight, T.tokens.plasma.menubar_height)
    readonly property real padding: (osd.height - osd.icon) / 2

    property string icon: ""
    property int filledSegments: 0
    property bool closing: false

    function show(iconName, value, maximum) {
        icon = iconName;
        filledSegments = maximum > 0 ? Math.round(osd.segments * value / maximum) : 0;
        hideTimer.restart();
        if (window.visible && !closing) {
            return;
        }
        closeAnimation.stop();
        closing = false;
        window.visible = true;
        glass.active = true;
        openAnimation.restart();
    }

    function hide() {
        hideTimer.stop();
        if (!window.visible || closing) {
            return;
        }
        closing = true;
        openAnimation.stop();
        closeAnimation.restart();
    }

    onControlCenterOpenChanged: {
        if (controlCenterOpen) {
            hide();
        }
    }

    // only valid while the active window is on this screen
    TaskManager.TasksModel {
        id: windowsHere
        filterByScreen: true
        screenGeometry: hud.screen
    }

    OsdHost {
        screenRect: hud.screen
        activeScreen: windowsHere.activeTask.valid
        suppressed: hud.controlCenterOpen
        onProgressRequested: (icon, value, maximum) => hud.show(icon, value, maximum)
    }

    Timer {
        id: hideTimer
        interval: hud.osd.timeout_ms
        onTriggered: hud.hide()
    }

    PlasmaCore.Dialog {
        id: window

        // Not OnScreenDisplay: libplasma never sends KWin the position of an
        // OSD, which KWin then centres low on the screen (spike SP-09). A
        // critical notification keeps its x and y and, like an OSD, stays above
        // fullscreen windows. Nor WindowStaysOnTopHint: with it Dialog turns
        // any type into a panel.
        type: PlasmaCore.Dialog.CriticalNotification
        backgroundHints: PlasmaCore.Dialog.NoBackground
        location: PlasmaCore.Types.Floating
        // shows, never takes a click nor the focus
        flags: Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
        visible: false
        x: hud.screen.x + hud.screen.width - hud.osd.screen_margin - hud.osd.width
        y: hud.screen.y + hud.barEdge + hud.osd.margin_top

        mainItem: Item {
            width: hud.osd.width
            height: hud.osd.height

            // animations here: Dialog only takes Items as direct children
            ParallelAnimation {
                id: openAnimation
                NumberAnimation {
                    target: pill
                    property: "opacity"
                    to: 1
                    duration: Motion.fadeMs(hud.osd.open_ms)
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    target: pill
                    property: "scale"
                    to: 1
                    duration: Motion.moveMs(hud.osd.open_ms)
                    easing.type: Easing.OutBack
                    easing.overshoot: Motion.overshoot(hud.osd.open_overshoot)
                }
            }

            ParallelAnimation {
                id: closeAnimation
                NumberAnimation {
                    target: pill
                    property: "opacity"
                    to: 0
                    duration: Motion.fadeMs(hud.osd.close_ms)
                    easing.type: Easing.OutCubic
                }
                SequentialAnimation {
                    // KWin cannot blur halfway: the glass goes when the pill is almost gone
                    PauseAnimation {
                        duration: Motion.fadeMs(hud.osd.close_ms) * T.tokens.control_center.close_unblur_at
                    }
                    ScriptAction {
                        script: glass.active = false
                    }
                }
                onFinished: {
                    window.visible = false;
                    hud.closing = false;
                    // the next one springs again
                    pill.scale = hud.osd.open_scale;
                }
            }

            Rectangle {
                id: pill

                // GlassRegion asks KWin for blur behind it
                readonly property bool goldenGlassTile: true

                anchors.fill: parent
                radius: height / 2
                color: Qt.alpha(Kirigami.Theme.backgroundColor, Accessibility.reduceTransparency ? T.tokens.accessibility.reduce_transparency_alpha
                                                                                                 : hud.osd.alpha)
                border.width: 1
                border.color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.glass.border.alpha)
                opacity: 0
                scale: hud.osd.open_scale

                Kirigami.Icon {
                    id: glyph
                    x: hud.padding
                    anchors.verticalCenter: parent.verticalCenter
                    width: hud.osd.icon
                    height: hud.osd.icon
                    source: hud.icon + "-symbolic"
                    fallback: hud.icon
                }

                Row {
                    id: bar
                    readonly property real segmentWidth: (width - (hud.osd.segments - 1) * spacing) / hud.osd.segments

                    anchors.left: glyph.right
                    anchors.leftMargin: hud.padding
                    anchors.right: parent.right
                    anchors.rightMargin: hud.padding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: hud.osd.segment_gap

                    Repeater {
                        model: hud.osd.segments
                        delegate: Rectangle {
                            required property int index
                            width: bar.segmentWidth
                            height: hud.osd.bar_height
                            radius: height / 2
                            color: Qt.alpha(Kirigami.Theme.textColor, index < hud.filledSegments ? hud.osd.fill_alpha : hud.osd.track_alpha)
                        }
                    }
                }
            }

            GlassRegion {
                id: glass
                anchors.fill: parent
                source: pill
                updateInterval: T.tokens.control_center.glass_update_ms
            }
        }
    }
}
