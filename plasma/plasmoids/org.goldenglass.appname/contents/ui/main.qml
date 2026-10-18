/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Nombre de la app activa en negrita, entre el logo y el menú global, como en
    la barra de menús de macOS. Cada pantalla muestra la última app usada en
    ella (el menú global va con allScreens=false, igual). Al pulsarlo: ocultar,
    ocultar otras, mostrar todo y salir.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.taskmanager as TaskManager

import "tokens.js" as T

PlasmoidItem {
    id: root

    property string appId: ""
    property string appName: ""

    preferredRepresentation: compactRepresentation
    toolTipMainText: ""
    toolTipSubText: ""
    Plasmoid.status: appName.length > 0 ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.HiddenStatus

    TaskManager.ActivityInfo {
        id: activityInfo
    }

    // Ventanas visibles de esta pantalla, escritorio y actividad, la última
    // activada primero (sin las minimizadas: tras «Ocultar» manda la de delante).
    TaskManager.TasksModel {
        id: screenTasks
        groupMode: TaskManager.TasksModel.GroupDisabled
        sortMode: TaskManager.TasksModel.SortLastActivated
        screenGeometry: Plasmoid.containment.screenGeometry
        activity: activityInfo.currentActivity
        filterByScreen: true
        filterByCurrentVirtualDesktop: true
        filterByActivity: true
        filterMinimized: true
        filterHidden: true
        onCountChanged: root.refresh()
        onDataChanged: root.refresh()
        onLayoutChanged: root.refresh()
        onModelReset: root.refresh()
    }

    // Todas las ventanas, para ocultar/mostrar/salir.
    TaskManager.TasksModel {
        id: allTasks
        groupMode: TaskManager.TasksModel.GroupDisabled
        filterByScreen: false
        filterByVirtualDesktop: false
        filterByActivity: false
    }

    function refresh() {
        const index = screenTasks.index(0, 0);
        if (screenTasks.count === 0 || !index.valid) {
            appId = "";
            appName = "";
            return;
        }
        appId = screenTasks.data(index, TaskManager.AbstractTasksModel.AppId) ?? "";
        // Sin coletillas del .desktop: «Spotify (Launcher)» → «Spotify».
        appName = (screenTasks.data(index, TaskManager.AbstractTasksModel.AppName) ?? "").replace(/\s*\([^)]*\)\s*$/, "");
    }

    // Llama a `action(index)` con cada ventana que cumple `match(appId)`.
    function forEachWindow(match, action) {
        for (let row = 0; row < allTasks.count; ++row) {
            const index = allTasks.index(row, 0);
            if (allTasks.data(index, TaskManager.AbstractTasksModel.IsWindow)
                && match(allTasks.data(index, TaskManager.AbstractTasksModel.AppId) ?? "")) {
                action(index);
            }
        }
    }

    function setMinimized(index, minimized) {
        const isMinimized = allTasks.data(index, TaskManager.AbstractTasksModel.IsMinimized);
        if (isMinimized !== minimized
            && allTasks.data(index, TaskManager.AbstractTasksModel.IsMinimizable)) {
            allTasks.requestToggleMinimized(index);
        }
    }

    function hideApp() {
        const id = appId;
        forEachWindow(other => other === id, index => setMinimized(index, true));
    }

    function hideOthers() {
        const id = appId;
        forEachWindow(other => other !== id, index => setMinimized(index, true));
    }

    function showAll() {
        forEachWindow(() => true, index => setMinimized(index, false));
    }

    function quitApp() {
        const id = appId;
        forEachWindow(other => other === id, index => allTasks.requestClose(index));
    }

    Component.onCompleted: refresh()

    compactRepresentation: MouseArea {
        id: compact
        // Mismo margen que los menús de la app (widgets/menubaritem).
        readonly property int padding: T.tokens.plasma.menubar_item_padding
        Layout.minimumWidth: nameLabel.implicitWidth + 2 * padding
        Layout.preferredWidth: Layout.minimumWidth
        onClicked: root.expanded = !root.expanded

        PlasmaComponents3.Label {
            id: nameLabel
            anchors.centerIn: parent
            text: root.appName
            textFormat: Text.PlainText
            font.weight: Font.Bold
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 13
        spacing: 0

        MenuEntry {
            text: i18n("Hide %1", root.appName)
            onTriggered: root.hideApp()
        }
        MenuEntry {
            text: i18n("Hide Others")
            onTriggered: root.hideOthers()
        }
        MenuEntry {
            text: i18n("Show All")
            onTriggered: root.showAll()
        }
        Kirigami.Separator {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
        }
        MenuEntry {
            text: i18n("Quit %1", root.appName)
            onTriggered: root.quitApp()
        }
    }

    component MenuEntry: PlasmaComponents3.ItemDelegate {
        signal triggered()
        Layout.fillWidth: true
        onClicked: {
            root.expanded = false;
            triggered();
        }
    }
}
