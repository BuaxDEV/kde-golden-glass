/*
    SPDX-FileCopyrightText: 2012 Marco Martin <mart@kde.org>

    SPDX-License-Identifier: GPL-2.0-or-later
*/

import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQml

import org.kde.plasma.core as PlasmaCore
import org.kde.ksvg as KSvg
import org.kde.taskmanager as TaskManager
import org.kde.kwindowsystem
import org.kde.kirigami as Kirigami
import org.kde.plasma.shell
import org.kde.plasma.workspace.keyboardlayout as Keyboards

import org.kde.plasma.plasmoid

Item {
    id: root

    property ContainmentItem containment

    // GoldenGlass: placa de vidrio del dock (org.goldenglass.dock), en
    // coordenadas de este panel. El dock la fija al cambiar de tamaño (la
    // ampliación la ensancha); el fondo, la región de blur (panelMask) y la
    // sombra la siguen, y el resto del panel queda transparente para los
    // iconos ampliados. Vacía = panel normal.
    property rect goldenglassDockSlab: Qt.rect(0, 0, 0, 0)
    readonly property bool goldenglassDock: goldenglassDockSlab.width > 0 && goldenglassDockSlab.height > 0
    // Sitio normal del fondo (el de Plasma). Con el dock, la contención se queda
    // aquí aunque el fondo se mueva a la placa: si siguiera al fondo, el dock
    // movería su propia placa en bucle.
    readonly property real panelItemX: rightEdge ? fixedLeftFloatingPadding + fixedRightFloatingPadding * (1 - floatingness) : leftFloatingPadding
    readonly property real panelItemY: bottomEdge ? fixedTopFloatingPadding + fixedBottomFloatingPadding * (1 - floatingness) : topFloatingPadding
    readonly property real panelItemWidth: verticalPanel ? panel.thickness : width - leftFloatingPadding - rightFloatingPadding
    readonly property real panelItemHeight: verticalPanel ? height - topFloatingPadding - bottomFloatingPadding : panel.thickness
    // El dock fija el grosor del panel: placa + hueco para los iconos ampliados
    // y el rebote (PanelView lo guarda en la configuración del panel).
    function goldenglassSetThickness(value) {
        if (value > 0 && panel.thickness !== value) {
            panel.thickness = value;
        }
    }

    // GoldenGlass: barra de menús de macOS 26/27 = el panel superior con el
    // menú del logo (org.goldenglass.systemmenu). Va sin fondo ni blur: el
    // texto se dibuja sobre el fondo de pantalla, salvo con «Mostrar fondo de
    // la barra de menús» (goldenglassrc [Plasma] MenubarBackground).
    readonly property bool goldenglassMenubar: containment?.plasmoid?.location === PlasmaCore.Types.TopEdge
        && (containment?.plasmoid?.applets ?? []).some(applet => applet.pluginName === "org.goldenglass.systemmenu")
    readonly property bool goldenglassNoBackground: containment?.plasmoid?.backgroundHints === PlasmaCore.Types.NoBackground
        || (goldenglassMenubar && !(goldenglassMenubarSettings.item?.background ?? false))
    // Ajustes en vivo y tokens (módulo QML de goldenglass-kstyle). Si no está,
    // falla solo este Loader: la barra queda sin fondo y sin atenuar.
    Loader {
        id: goldenglassMenubarSettings
        active: root.goldenglassMenubar
        source: Qt.resolvedUrl("GoldenGlassMenuBarSettings.qml")
    }

    // GoldenGlass: con varias pantallas, la barra de menús de las que no tienen
    // la ventana activa se atenúa, como en macOS. Sin ventana activa (escritorio)
    // no se atenúa ninguna.
    Loader {
        id: goldenglassDimming
        active: root.goldenglassMenubar && Qt.application.screens.length > 1 && goldenglassMenubarSettings.item !== null
        sourceComponent: Item {
            // activeTask no avisa si la ventana activa ya lo era al llenarse el
            // modelo: count obliga a recalcular entonces.
            readonly property bool inactive: activeTasks.count >= 0 && screenTasks.count >= 0
                && activeTasks.activeTask.valid && !screenTasks.activeTask.valid
            TaskManager.TasksModel {
                id: activeTasks
                filterByScreen: false
                filterByVirtualDesktop: false
                filterByActivity: false
            }
            TaskManager.TasksModel {
                id: screenTasks
                screenGeometry: panel.screenGeometry
                filterByScreen: true
                filterByVirtualDesktop: false
                filterByActivity: false
            }
        }
    }
    Binding {
        target: root.containment
        property: "opacity"
        when: root.containment && root.goldenglassMenubar
        value: goldenglassDimming.item?.inactive ? goldenglassMenubarSettings.item.inactiveOpacity : 1
        restoreMode: Binding.RestoreBindingOrValue
    }

    property bool floatingPrefix: floatingPanelSvg.usedPrefix === "floating"
    readonly property bool verticalPanel: containment?.plasmoid?.formFactor === PlasmaCore.Types.Vertical

    readonly property real spacingAtMinSize: Math.floor(Math.max(1, panel.thickness - Kirigami.Units.iconSizes.smallMedium)/2)
    KSvg.FrameSvgItem {
        id: thickPanelSvg
        visible: false
        prefix: 'thick'
        imagePath: "widgets/panel-background"
    }
    KSvg.FrameSvgItem {
        id: floatingPanelSvg
        visible: false
        prefix: ['floating', '']
        imagePath: "widgets/panel-background"
    }

    readonly property bool rightEdge: containment?.plasmoid?.location === PlasmaCore.Types.RightEdge
    readonly property bool bottomEdge: containment?.plasmoid?.location === PlasmaCore.Types.BottomEdge

    readonly property int bottomFloatingPadding: Math.round(fixedBottomFloatingPadding * floatingness)
    readonly property int leftFloatingPadding: Math.round(fixedLeftFloatingPadding * floatingness)
    readonly property int rightFloatingPadding: Math.round(fixedRightFloatingPadding * floatingness)
    readonly property int topFloatingPadding: Math.round(fixedTopFloatingPadding * floatingness)


    // NOTE: Many of the properties in this file are accessed directly in C++ PanelView!
    // If you change these, make sure to also correct the related code in panelview.cpp.
    readonly property int fixedBottomFloatingPadding: floating && (floatingPrefix ? floatingPanelSvg.fixedMargins.bottom : 8)
    readonly property int fixedLeftFloatingPadding: floating && (floatingPrefix ? floatingPanelSvg.fixedMargins.left   : 8)
    readonly property int fixedRightFloatingPadding: floating && (floatingPrefix ? floatingPanelSvg.fixedMargins.right  : 8)
    readonly property int fixedTopFloatingPadding: floating && (floatingPrefix ? floatingPanelSvg.fixedMargins.top    : 8)

    readonly property int topPadding: Math.round(Math.min(thickPanelSvg.fixedMargins.top + Kirigami.Units.smallSpacing, spacingAtMinSize));
    readonly property int bottomPadding: Math.round(Math.min(thickPanelSvg.fixedMargins.bottom + Kirigami.Units.smallSpacing, spacingAtMinSize));
    readonly property int leftPadding: Math.round(Math.min(thickPanelSvg.fixedMargins.left + Kirigami.Units.smallSpacing, spacingAtMinSize));
    readonly property int rightPadding: Math.round(Math.min(thickPanelSvg.fixedMargins.right + Kirigami.Units.smallSpacing, spacingAtMinSize));

    // GoldenGlass: before the containment arrives the frame has no edge prefix
    // and every border on, so Plasma would clip a thin menu bar to the dock's
    // corners and save that height. No minimum until the prefix is known.
    readonly property int minPanelHeight: containment ? translucentItem.minimumDrawingHeight : 0
    readonly property int minPanelWidth: translucentItem.minimumDrawingWidth

    // This value is read from panelview.cpp which needs it to decide which border should be enabled
    property real topShadowMargin: -floatingTranslucentItem.y
    property real leftShadowMargin: -floatingTranslucentItem.x
    property real rightShadowMargin: -(width - floatingTranslucentItem.width - floatingTranslucentItem.x)
    property real bottomShadowMargin: -(height - floatingTranslucentItem.height - floatingTranslucentItem.y)

    property var panelMask: floatingness === 0 ? (panelOpacity === 1 ? opaqueItem.mask : translucentItem.mask) : (panelOpacity === 1 ? floatingOpaqueItem.mask : floatingTranslucentItem.mask)

    // The point is read from panelview.cpp and is used as an offset for the mask
    readonly property point floatingTranslucentItemOffset: Qt.point(floatingTranslucentItem.x, floatingTranslucentItem.y)

    TaskManager.VirtualDesktopInfo {
        id: virtualDesktopInfo
    }

    TaskManager.ActivityInfo {
        id: activityInfo
    }

    // We need to have a little gap between the raw visibleWindowsModel count
    // and actually determining if a window is touching.
    // This is because certain dialog windows start off with a position of (screenwidth/2, screenheight/2)
    // and they register as "touching" in the split-second before KWin can place them correctly.
    // This avoids the panel flashing if it is auto-hide etc and such a window is shown.
    // Examples of such windows: properties of a file on desktop, or portal "open with" dialog
    property bool touchingWindow: false
    property bool touchingWindowDirect: visibleWindowsModel.count > 0
    readonly property bool touchingWindowOrKeyboard: touchingWindow || (bottomEdge && Keyboards.KWinVirtualKeyboard.visible)
    property bool showingDesktop: KWindowSystem.showingDesktop
    Timer {
        id: touchingWindowDebounceTimer
        interval: 10  // ms, I find that this value is enough while not causing unresponsiveness while dragging windows close
        onTriggered: root.touchingWindow = !KWindowSystem.showingDesktop && root.touchingWindowDirect
    }
    onTouchingWindowDirectChanged: touchingWindowDebounceTimer.start()
    onShowingDesktopChanged: touchingWindowDebounceTimer.start()

    TaskManager.TasksModel {
        id: visibleWindowsModel
        filterByCurrentVirtualDesktop: true
        filterByActivity: true
        filterByScreen: false
        filterByRegion: TaskManager.RegionFilterMode.Intersect
        filterHidden: true
        filterMinimized: true

        screenGeometry: panel.screenGeometry
        activity: activityInfo.currentActivity

        groupMode: TaskManager.TasksModel.GroupDisabled

        Binding on regionGeometry {
            delayed: true
            value: panel.width, panel.height, panel.x, panel.y, panel.dogdeGeometryByDistance(panel.visibilityMode === Panel.DodgeWindows ? -1 : 1) // +1 is for overlap detection, -1 is for snapping to panel
        }
    }

    Connections {
        target: root.containment?.plasmoid ?? null
        function onActivated() {
            if (root.containment.plasmoid.status === PlasmaCore.Types.AcceptingInputStatus) {
                root.containment.plasmoid.status = PlasmaCore.Types.PassiveStatus;
            } else {
                root.containment.plasmoid.status = PlasmaCore.Types.AcceptingInputStatus;
            }
        }
    }

    // Floatingness is a value in [0, 1] that's multiplied to the floating margin; 0: not floating, 1: floating, between 0 and 1: animation between the two states
    readonly property int floatingnessAnimationDuration: Kirigami.Units.longDuration
    property double floatingnessTarget: 0.0 // The animation is handled in panelview.cpp for efficiency
    property double floatingness: 0.0

    // PanelOpacity is a value in [0, 1] that's used as the opacity of the opaque elements over the transparent ones; values between 0 and 1 are used for animations
    property double panelOpacity
    Behavior on panelOpacity {
        NumberAnimation {
            duration: Kirigami.Units.longDuration
            easing.type: Easing.OutCubic
        }
    }

    KSvg.FrameSvgItem {
        id: translucentItem
        visible: root.floatingness === 0 && root.panelOpacity !== 1
        enabledBorders: panel.enabledBorders
        anchors.fill: floatingTranslucentItem
        imagePath: root.goldenglassNoBackground ? "" : "widgets/panel-background"
    }
    KSvg.FrameSvgItem {
        id: floatingTranslucentItem
        visible: root.floatingness !== 0 && root.panelOpacity !== 1
        x: root.goldenglassDock ? root.goldenglassDockSlab.x : root.panelItemX
        y: root.goldenglassDock ? root.goldenglassDockSlab.y : root.panelItemY
        width: root.goldenglassDock ? root.goldenglassDockSlab.width : root.panelItemWidth
        height: root.goldenglassDock ? root.goldenglassDockSlab.height : root.panelItemHeight

        imagePath: root.goldenglassNoBackground ? "" : "widgets/panel-background"
    }
    KSvg.FrameSvgItem {
        id: floatingOpaqueItem
        visible: root.floatingness !== 0 && root.panelOpacity !== 0
        opacity: root.panelOpacity
        anchors.fill: floatingTranslucentItem
        imagePath: root.goldenglassNoBackground ? "" : "solid/widgets/panel-background"
    }
    KSvg.FrameSvgItem {
        id: opaqueItem
        visible: root.panelOpacity !== 0 && root.floatingness === 0
        opacity: root.panelOpacity
        enabledBorders: panel.enabledBorders
        anchors.fill: floatingTranslucentItem
        imagePath: root.goldenglassNoBackground ? "" : "solid/widgets/panel-background"
    }

    Keys.onEscapePressed: {
        root.parent.focus = false
    }

    property bool isOpaque: panel.opacityMode === Panel.Opaque
    property bool isTransparent: panel.opacityMode === Panel.Translucent
    property bool isAdaptive: panel.opacityMode === Panel.Adaptive
    property bool floating: panel.floating
    property var stateTriggers: [floating, touchingWindowOrKeyboard, isOpaque, isAdaptive, isTransparent, containment, panel.floatingApplets]
    onStateTriggersChanged: {
        let opaqueApplets = false
        let floatingApplets = false
        if ((!floating || touchingWindowOrKeyboard) && (isOpaque || (touchingWindowOrKeyboard && isAdaptive))) {
            panelOpacity = 1
            opaqueApplets = true
            floatingnessTarget = 0
            floatingApplets = (panel.floatingApplets && !floating)
        } else if ((!floating || touchingWindowOrKeyboard) && (isTransparent || (!touchingWindowOrKeyboard && isAdaptive))) {
            panelOpacity = 0
            floatingnessTarget = 0
            floatingApplets = (panel.floatingApplets && !floating)
        } else if ((floating && !touchingWindowOrKeyboard) && (isTransparent || isAdaptive)) {
            panelOpacity = 0
            floatingnessTarget = 1
            floatingApplets = true
        } else if (floating && !touchingWindowOrKeyboard && isOpaque) {
            panelOpacity = 1
            opaqueApplets = true
            floatingnessTarget = 1
            floatingApplets = true
        }

        // Exceptions: panels with not NormalPanel visibilityMode
        // should never de-float, and we should not have transparent
        // panels when on X11 with compositing not active.
        if (panel.visibilityMode != Panel.NormalPanel && floating) {
            floatingnessTarget = 1
            floatingApplets = true
        }

        // Not using panelOpacity to check as it has a NumberAnimation, and it will thus
        // be still read as the initial value here, before the animation starts.
        if (containment) {
            if (opaqueApplets) {
                containment.plasmoid.containmentDisplayHints |= PlasmaCore.Types.ContainmentPrefersOpaqueBackground
            } else {
                containment.plasmoid.containmentDisplayHints &= ~PlasmaCore.Types.ContainmentPrefersOpaqueBackground
            }
            if (floatingApplets) {
                containment.plasmoid.containmentDisplayHints |= PlasmaCore.Types.ContainmentPrefersFloatingApplets
            } else {
                containment.plasmoid.containmentDisplayHints &= ~PlasmaCore.Types.ContainmentPrefersFloatingApplets
            }
        }
    }

    function adjustPrefix() {
        if (!containment) {
            return "";
        }
        var pre;
        switch (containment.plasmoid.location) {
        case PlasmaCore.Types.LeftEdge:
            pre = "west";
            break;
        case PlasmaCore.Types.TopEdge:
            pre = "north";
            break;
        case PlasmaCore.Types.RightEdge:
            pre = "east";
            break;
        case PlasmaCore.Types.BottomEdge:
            pre = "south";
            break;
        default:
            pre = "";
            break;
        }
        translucentItem.prefix = opaqueItem.prefix = floatingTranslucentItem.prefix = floatingOpaqueItem.prefix = [pre, ""];
    }

    onContainmentChanged: {
        if (!containment) {
            return;
        }
        containment.parent = containmentParent;
        containment.visible = true;
        containment.anchors.fill = containmentParent;
        containment.plasmoid.locationChanged.connect(adjustPrefix);
        adjustPrefix();
    }

    Binding {
        target: panel
        property: "length"
        when: root.containment
        value: {
            if (!root.containment) {
                return;
            }
            if (root.verticalPanel) {
                if (root.containment.Layout.fillHeight) {
                    if (panel.lengthMode == Panel.Custom) {
                        return panel.maximumHeight
                    } else {
                        return panel.screenGeometry.height
                    }
                }
                return root.containment.Layout.preferredHeight
            } else {
                if (root.containment.Layout.fillWidth) {
                    if (panel.lengthMode == Panel.Custom) {
                        return panel.maximumWidth
                    } else {
                        return panel.screenGeometry.width
                    }
                }
                return root.containment.Layout.preferredWidth
            }
        }
        restoreMode: Binding.RestoreBinding
    }

    Binding {
        target: panel
        property: "backgroundHints"
        when: root.containment
        value: {
            if (!root.containment) {
                return;
            }

            return root.goldenglassNoBackground ? PlasmaCore.Types.NoBackground : root.containment.plasmoid.backgroundHints;
        }
        restoreMode: Binding.RestoreBinding
    }

    KSvg.FrameSvgItem {

        Accessible.name: i18ndc("plasma_shell_org.kde.plasma.desktop", "@info:whatsthis Accessible name", "Panel Focus Indicator")

        x: root.verticalPanel || !panel.activeFocusItem
            ? translucentItem.x
            : Math.max(panel.activeFocusItem.Kirigami.ScenePosition.x, panel.activeFocusItem.Kirigami.ScenePosition.x)
        y: root.verticalPanel && panel.activeFocusItem
            ? Math.max(panel.activeFocusItem.Kirigami.ScenePosition.y, panel.activeFocusItem.Kirigami.ScenePosition.y)
            : translucentItem.y

        width: panel.activeFocusItem
            ? (root.verticalPanel ? translucentItem.width : Math.min(panel.activeFocusItem.width, panel.activeFocusItem.width))
            : 0
        height: panel.activeFocusItem
            ? (root.verticalPanel ?  Math.min(panel.activeFocusItem.height, panel.activeFocusItem.height) : translucentItem.height)
            : 0

        visible: panel.active && panel.activeFocusItem

        imagePath: "widgets/tabbar"
        prefix: {
            if (!root.containment) {
                return "";
            }
            var prefix = ""
            switch (root.containment.plasmoid.location) {
                case PlasmaCore.Types.LeftEdge:
                    prefix = "west-active-tab";
                    break;
                case PlasmaCore.Types.TopEdge:
                    prefix = "north-active-tab";
                    break;
                case PlasmaCore.Types.RightEdge:
                    prefix = "east-active-tab";
                    break;
                default:
                    prefix = "south-active-tab";
            }
            if (!hasElementPrefix(prefix)) {
                prefix = "active-tab";
            }
            return prefix;
        }
    }
    Item {
        id: containmentParent
        anchors.centerIn: root.goldenglassDock ? undefined : (root.isOpaque ? floatingOpaqueItem : floatingTranslucentItem)
        x: root.panelItemX + (root.panelItemWidth - width) / 2
        y: root.panelItemY + (root.panelItemHeight - height) / 2
        width: root.verticalPanel ? panel.thickness : root.width - root.fixedLeftFloatingPadding - root.fixedRightFloatingPadding
        height: root.verticalPanel ? root.height - root.fixedBottomFloatingPadding - root.fixedTopFloatingPadding : panel.thickness
    }
}
