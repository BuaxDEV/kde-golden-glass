/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Glass pieces loose on the desktop, below the menu bar and against the
    right edge of the screen, as macOS draws the Control Center (and the
    Notification Center). tools/plasmoids.py (SHARED) copies this file with
    GlassBlur.qml and Motion.qml to the plasmoids that use it.

    A PlasmaCore.Dialog without background (Plasma's popup cannot drop it)
    that covers the whole screen, transparent: a click outside the pieces,
    also on the menu bar, closes it (the menu bar never takes the focus, so
    losing it is not enough). GlassBlur asks KWin for glass only behind each
    piece. Esc, toggle() and the focus moving to another screen close it too.

    Liquid Glass animation: on opening, the glass springs from its origin
    (taller faster than wider, overshooting a little before settling); on
    closing, it shrinks back towards it and fades out.

        GlassOverlay {
            tokens: T.tokens.control_center
            content: Component { ... }
            anchorItem: root.fullRepresentationItem
        }
*/

import QtQuick

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

PlasmaCore.Dialog {
    id: overlay

    // What the overlay shows. Its root may define resetContent() (back to its
    // first view, called on every open) and goBack(), which returns true when
    // Esc only stepped back inside the content instead of closing.
    property Component content
    // "icon": springs from anchorItem, the menu bar icon; "edge": from the
    // right edge of the screen
    property string origin: "icon"
    property Item anchorItem
    // Token section with the animation and the margins: open_fade_ms, open_ms,
    // open_ms_y, open_overshoot, open_scale_x, open_scale_y, close_ms,
    // close_scale, close_unblur_at, floating_margin, screen_margin and
    // glass_update_ms (see [control_center])
    required property var tokens

    signal opened()

    // Real height of the menu bar on this screen: what the panels take at the
    // top edge. plasma.menubar_height is only the height of new menu bars,
    // and a menu bar that hides itself takes nothing.
    readonly property real menuBarHeight: Plasmoid.containment ? Plasmoid.containment.availableScreenRect.y : 0
    property rect screen: Plasmoid.containment.screenGeometry
    property bool closing: false

    backgroundHints: PlasmaCore.Dialog.NoBackground
    location: PlasmaCore.Types.Floating
    // while closing, clicks reach whatever is below
    flags: closing ? Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput : Qt.WindowStaysOnTopHint
    visible: false

    // the focus went to another window (another screen, an app): close with
    // the animation, not at once as hideOnWindowDeactivate would
    onActiveChanged: {
        if (!active && visible) {
            close();
        }
    }

    function place() {
        screen = Plasmoid.containment.screenGeometry;
        x = screen.x;
        y = screen.y;
    }

    // where the spring starts, in body coordinates
    function originX() {
        if (origin === "icon" && anchorItem) {
            const center = anchorItem.mapToGlobal(anchorItem.width / 2, 0).x - screen.x;
            if (center > 0 && center < screen.width) {
                return Math.min(Math.max(center - body.x, 0), body.width);
            }
        }
        return body.width;
    }

    function resetContent() {
        if (body.item && typeof body.item.resetContent === "function") {
            body.item.resetContent();
        }
    }

    function toggle() {
        if (visible && !closing) {
            close();
        } else {
            open();
        }
    }

    // also while closing: it goes on from where it was, with the first view
    function open() {
        closeAnimation.stop();
        closing = false;
        resetContent();
        place();
        visible = true;
        requestActivate();
        glass.track(true);
        scaleOrigin.origin.x = originX();
        openAnimation.restart();
        opened();
    }

    function close() {
        if (!visible || closing) {
            return;
        }
        closing = true;
        openAnimation.stop();
        scaleOrigin.origin.x = originX();
        closeAnimation.restart();
    }

    mainItem: FocusScope {
        width: overlay.screen.width
        height: overlay.screen.height
        focus: true
        // pieces that are fading out no longer respond
        enabled: !overlay.closing

        // animations here: Dialog only takes Items as direct children
        ParallelAnimation {
            id: openAnimation
            NumberAnimation {
                target: body
                property: "opacity"
                to: 1
                duration: Motion.fadeMs(overlay.tokens.open_fade_ms)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: scaleOrigin
                property: "xScale"
                to: 1
                duration: Motion.moveMs(overlay.tokens.open_ms)
                easing.type: Easing.OutBack
                easing.overshoot: Motion.overshoot(overlay.tokens.open_overshoot)
            }
            NumberAnimation {
                target: scaleOrigin
                property: "yScale"
                to: 1
                duration: Motion.moveMs(overlay.tokens.open_ms_y)
                easing.type: Easing.OutBack
                easing.overshoot: Motion.overshoot(overlay.tokens.open_overshoot)
            }
        }

        ParallelAnimation {
            id: closeAnimation
            NumberAnimation {
                target: body
                property: "opacity"
                to: 0
                duration: Motion.fadeMs(overlay.tokens.close_ms)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: scaleOrigin
                properties: "xScale,yScale"
                to: overlay.tokens.close_scale
                duration: Motion.moveMs(overlay.tokens.close_ms)
                easing.type: Easing.InCubic
            }
            SequentialAnimation {
                // KWin cannot blur halfway: the glass goes when the pieces are
                // almost gone
                PauseAnimation {
                    duration: Motion.fadeMs(overlay.tokens.close_ms) * overlay.tokens.close_unblur_at
                }
                ScriptAction {
                    script: glass.track(false)
                }
            }
            onFinished: {
                overlay.visible = false;
                overlay.closing = false;
                // the next opening springs from here
                scaleOrigin.xScale = overlay.tokens.open_scale_x;
                scaleOrigin.yScale = overlay.tokens.open_scale_y;
            }
        }

        Keys.onEscapePressed: {
            const steppedBack = body.item && typeof body.item.goBack === "function" && body.item.goBack();
            if (!steppedBack) {
                overlay.close();
            }
        }

        // a click outside the pieces
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onPressed: overlay.close()
        }

        Loader {
            id: body
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: overlay.menuBarHeight + overlay.tokens.floating_margin
            anchors.rightMargin: overlay.tokens.screen_margin
            sourceComponent: overlay.content
            // closed: invisible and shrunk, ready to spring
            opacity: 0
            transform: Scale {
                id: scaleOrigin
                origin.y: 0
                xScale: overlay.tokens.open_scale_x
                yScale: overlay.tokens.open_scale_y
            }

            // clicks between the pieces do not close
            MouseArea {
                anchors.fill: parent
                z: -1
                acceptedButtons: Qt.AllButtons
            }
        }

        // Glass behind each piece (org.goldenglass.glass module of
        // goldenglass-kstyle). Without it the pieces look the same, unblurred.
        Loader {
            id: glass
            anchors.fill: parent
            source: Qt.resolvedUrl("GlassBlur.qml")
            onLoaded: {
                item.source = body;
                item.updateInterval = overlay.tokens.glass_update_ms;
            }

            // with false, KWin stops blurring
            function track(on) {
                if (item) {
                    item.active = on;
                }
            }
        }
    }
}
