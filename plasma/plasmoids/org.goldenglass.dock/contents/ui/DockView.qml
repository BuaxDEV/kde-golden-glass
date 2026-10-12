/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Contenido del dock: Apps · apps fijadas y abiertas · [| recientes] · | ·
    Papelera, en una fila apoyada en la placa de vidrio.

    Ampliación: cada icono crece según su distancia al cursor, medida sobre la
    fila sin ampliar (así la posición del cursor no depende de la propia
    ampliación y no hay realimentación). Curva de coseno que llega a 0 a
    «spread» iconos; la fila se ensancha alrededor de su centro. El plasmoid
    reserva el ancho máximo para que el panel no cambie de tamaño al ampliar.

    La placa (slab) la dibuja el Panel.qml de GoldenGlass: aquí solo se le
    pasa su geometría (goldenglassDockSlab).
*/

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.plasmoid
import org.kde.plasma.private.kicker as Kicker
import org.kde.taskmanager as TaskManager

import "tokens.js" as T

Item {
    id: dock

    required property var plasmoidItem
    required property var apps

    // --- medidas -------------------------------------------------------------------
    readonly property real iconSize: Plasmoid.configuration.iconSize
    readonly property bool magnification: Plasmoid.configuration.magnification
    readonly property real maxSize: magnification ? Math.max(iconSize, Plasmoid.configuration.magnificationSize) : iconSize
    readonly property real pad: T.tokens.plasma.dock_padding
    readonly property real gap: T.tokens.dock.gap
    readonly property real spread: T.tokens.dock.spread
    readonly property real separatorWidth: gap + 1

    // Contenido: Apps, tareas, [separador, recientes], separador, Papelera
    readonly property int taskCount: tasksRepeater.count
    readonly property int recentCount: Plasmoid.configuration.showRecent ? recents.length : 0
    readonly property int separatorCount: recentCount > 0 ? 2 : 1
    readonly property int iconCount: 2 + taskCount + recentCount
    readonly property real baseWidth: iconCount * iconSize + separatorCount * separatorWidth
        + (iconCount + separatorCount - 1) * gap

    // centro de un elemento en la fila sin ampliar: «slot» iconos y «separators»
    // separadores antes que él
    function centerOf(slot, separators) {
        return slot * (iconSize + gap) + separators * (separatorWidth + gap) + iconSize / 2;
    }

    // --- ampliación ----------------------------------------------------------------
    property real cursor: -1                 // posición del cursor en la fila sin ampliar
    // icono que se arrastra: un Item vuelve solo a null si el delegado se
    // destruye a medio arrastre (p. ej. se cierra la app), y no queda «arrastrando»
    property Item dragItem: null
    readonly property bool dragging: dragItem !== null
    property real amount: hover.hovered && magnification && !dragging ? 1 : 0
    Behavior on amount {
        NumberAnimation {
            duration: T.tokens.dock.magnification_ms
            easing.type: Easing.OutCubic
        }
    }

    HoverHandler {
        id: hover
        onPointChanged: {
            if (hovered) {
                dock.cursor = dock.baseWidth / 2 + (point.position.x - dock.width / 2);
            }
        }
    }

    function sizeAt(center) {
        if (amount <= 0 || maxSize <= iconSize) {
            return iconSize;
        }
        const d = Math.abs(cursor - center) / (iconSize + gap);
        const f = d >= spread ? 0 : (Math.cos(d / spread * Math.PI) + 1) / 2;
        return iconSize + (maxSize - iconSize) * f * amount;
    }

    // grosor del panel: placa + hueco para el icono más ampliado rebotando (al
    // hacer clic está ampliado y salta desde ese tamaño)
    // (lo aplica el Panel.qml de GoldenGlass; igual que _dock_height de
    // tools/lookandfeel.py, que da el valor inicial)
    readonly property int panelThickness: {
        const headroom = Math.ceil(maxSize * (1 + T.tokens.dock.bounce)) - iconSize;
        const h = Math.ceil(iconSize + 2 * pad + headroom);
        return h + h % 2;
    }
    onPanelThicknessChanged: Qt.callLater(publishSlab)

    // ancho reservado: la fila ampliada como mucho (integral de la curva: spread
    // iconos de más) y la placa
    Layout.preferredWidth: Math.ceil(baseWidth + (maxSize - iconSize) * (spread + 0.5) + 2 * pad)
    Layout.minimumWidth: Layout.preferredWidth
    Layout.maximumWidth: Layout.preferredWidth
    Layout.fillHeight: true

    // --- tareas --------------------------------------------------------------------
    TaskManager.VirtualDesktopInfo {
        id: virtualDesktopInfo
    }
    TaskManager.ActivityInfo {
        id: activityInfo
    }

    TaskManager.TasksModel {
        id: tasksModel
        // como el Dock: todas las apps de todos los escritorios, una por app
        groupMode: TaskManager.TasksModel.GroupApplications
        groupInline: false
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: false
        launchInPlace: true
        filterByVirtualDesktop: false
        filterByScreen: false
        filterByActivity: true
        filterHidden: true
        activity: activityInfo.currentActivity
        virtualDesktop: virtualDesktopInfo.currentDesktop
        screenGeometry: Plasmoid.containment.screenGeometry
        launcherList: Plasmoid.configuration.launchers
        onLauncherListChanged: Plasmoid.configuration.launchers = launcherList
    }

    function isPinned(model) {
        return model.IsLauncher === true || model.HasLauncher === true;
    }

    // id de escritorio de una URL de lanzador: applications:x.desktop, file:///…/x.desktop
    function desktopId(url) {
        const text = String(url || "");
        const name = text.startsWith("applications:") ? text.slice("applications:".length) : text.split("/").pop();
        return name.endsWith(".desktop") ? name : "";
    }

    function activateTask(modelIndex, model) {
        if (model.IsLauncher === true) {
            tasksModel.requestNewInstance(modelIndex);
            return;
        }
        if (model.IsGroupParent === true) {
            // la ventana usada más recientemente; si la app ya está delante, la siguiente
            const windows = windowsOf(modelIndex, model).sort((a, b) => b.lastActivated - a.lastActivated);
            const next = windows.length > 1 && windows[0].active ? windows[windows.length - 1] : windows[0];
            if (next) {
                tasksModel.requestActivate(next.index);
            }
            return;
        }
        tasksModel.requestActivate(modelIndex);
    }

    // ventanas de una tarea (o de un grupo): { index, title, winId, active, lastActivated }
    function windowsOf(modelIndex, model) {
        const roles = TaskManager.AbstractTasksModel;
        const entry = (idx, persistent) => ({
            index: persistent,
            title: tasksModel.data(idx, Qt.DisplayRole) || "",
            winId: (tasksModel.data(idx, roles.WinIdList) || [])[0] || "",
            active: tasksModel.data(idx, roles.IsActive) === true,
            lastActivated: Number(tasksModel.data(idx, roles.LastActivated) || 0),
        });
        const row = modelIndex.row;
        if (model.IsGroupParent === true) {
            const out = [];
            const count = tasksModel.rowCount(modelIndex);
            for (let i = 0; i < count; ++i) {
                out.push(entry(tasksModel.makeModelIndex(row, i), tasksModel.makePersistentModelIndex(row, i)));
            }
            return out;
        }
        if (model.IsWindow === true) {
            return [entry(modelIndex, tasksModel.makePersistentModelIndex(row))];
        }
        return [];
    }

    // --- apps recientes ------------------------------------------------------------
    Kicker.RecentUsageModel {
        id: recentModel
        shownItems: Kicker.RecentUsageModel.OnlyApps
    }
    Instantiator {
        id: recentReader
        model: Plasmoid.configuration.showRecent ? recentModel : null
        delegate: QtObject {
            required property int index
            required property var model
            readonly property var entry: ({
                row: index,
                name: model.display,
                icon: model.decoration,
                id: dock.desktopId(model.favoriteId || ""),
            })
        }
        onObjectAdded: rebuildRecents.restart()
        onObjectRemoved: rebuildRecents.restart()
    }

    property var recents: []
    Timer {
        id: rebuildRecents
        interval: 100
        onTriggered: {
            const inDock = new Set();
            for (let i = 0; i < tasksRepeater.count; ++i) {
                const item = tasksRepeater.itemAt(i);
                if (item) {
                    inDock.add(item.appKey);
                    inDock.add(item.launcherKey);
                }
            }
            const out = [];
            for (let i = 0; i < recentReader.count && out.length < T.tokens.dock.recent_count; ++i) {
                const item = recentReader.objectAt(i);
                const key = item ? item.entry.id.replace(/\.desktop$/, "") : "";
                if (key && !inDock.has(key)) {
                    out.push(item.entry);
                }
            }
            dock.recents = out;
        }
    }
    Connections {
        target: tasksModel
        function onCountChanged() {
            rebuildRecents.restart();
        }
    }

    // --- placa y fila ----------------------------------------------------------------
    Item {
        id: slab
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        width: row.width + 2 * dock.pad
        height: dock.iconSize + 2 * dock.pad
    }

    Row {
        id: row
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: slab.bottom
        anchors.bottomMargin: dock.pad
        spacing: dock.gap

        // Apps
        DockIcon {
            size: dock.sizeAt(dock.centerOf(0, 0))
            y: row.height - height
            padding: dock.pad
            maxSize: dock.maxSize
            iconSource: "goldenglass-apps"
            fallback: "view-app-grid"
            label: i18n("Apps")
            hovered: appsArea.containsMouse
            pressed: appsArea.pressed
            MouseArea {
                id: appsArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: dock.apps.toggle()
            }
        }

        // Apps fijadas y abiertas
        Repeater {
            id: tasksRepeater
            model: tasksModel
            delegate: DockIcon {
                id: task
                required property int index
                required property var model
                readonly property var modelIndex: tasksModel.makeModelIndex(index)
                readonly property string appKey: String(model.AppId || "").replace(/\.desktop$/, "")
                readonly property string launcherKey: dock.desktopId(model.LauncherUrlWithoutIcon).replace(/\.desktop$/, "")

                size: dock.sizeAt(dock.centerOf(1 + index, 0))
                y: row.height - height
                padding: dock.pad
                maxSize: dock.maxSize
                iconSource: model.decoration
                label: model.AppName || model.display || ""
                running: model.IsWindow === true || model.IsGroupParent === true
                launching: model.IsStartup === true
                demandsAttention: model.IsDemandingAttention === true
                hovered: taskArea.containsMouse
                pressed: taskArea.pressed && !dock.dragging
                tooltipEnabled: !dock.dragging && !taskMenu.opened
                previews: running ? previewsComponent : null

                Component {
                    id: previewsComponent
                    WindowPreviews {
                        tasks: tasksModel
                        appName: task.label
                        appIcon: task.iconSource
                        windows: dock.windowsOf(task.modelIndex, task.model)
                    }
                }

                MouseArea {
                    id: taskArea
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
                    property real pressX: 0
                    property bool moved: false

                    onPressed: mouse => {
                        pressX = mouse.x;
                        moved = false;
                    }
                    // arrastrar a izquierda o derecha reordena las apps fijadas
                    onPositionChanged: mouse => {
                        if (!pressed || !(pressedButtons & Qt.LeftButton) || !dock.isPinned(task.model)) {
                            return;
                        }
                        if (!moved && Math.abs(mouse.x - pressX) > Kirigami.Units.gridUnit) {
                            moved = true;
                            dock.dragItem = task;
                        }
                        if (moved) {
                            // al arrastrar no hay ampliación: todos los iconos miden lo mismo
                            // (el primero de la fila es Apps). No vale launcherCount: solo
                            // cuenta las fijadas que no están abiertas.
                            const p = mapToItem(row, mouse.x, mouse.y);
                            const target = Math.max(0, Math.min(tasksRepeater.count - 1,
                                Math.floor(p.x / (dock.iconSize + dock.gap)) - 1));
                            if (target !== task.index) {
                                tasksModel.move(task.index, target);
                            }
                        }
                    }
                    onReleased: {
                        if (moved) {
                            // antes de syncLaunchers: puede recrear este delegado
                            dock.dragItem = null;
                            tasksModel.syncLaunchers();
                        }
                    }
                    onCanceled: dock.dragItem = null
                    onClicked: mouse => {
                        if (moved) {
                            return;
                        }
                        if (mouse.button === Qt.RightButton) {
                            taskMenu.open(mouse.x, mouse.y);
                        } else if (mouse.button === Qt.MiddleButton) {
                            tasksModel.requestNewInstance(task.modelIndex);
                        } else {
                            dock.activateTask(task.modelIndex, task.model);
                        }
                    }
                }

                // soltar archivos sobre una app: se abren con ella
                DropArea {
                    anchors.fill: parent
                    onDropped: drop => {
                        if (drop.hasUrls) {
                            tasksModel.requestOpenUrls(task.modelIndex, drop.urls);
                            drop.acceptProposedAction();
                        }
                    }
                }

                TaskMenu {
                    id: taskMenu
                    tasks: tasksModel
                    modelIndex: task.modelIndex
                    model: task.model
                    desktopId: dock.desktopId(task.model.LauncherUrlWithoutIcon)
                    pinned: dock.isPinned(task.model)
                    running: task.running
                }

                // para la animación de minimizar (la «lámpara» de KWin)
                function publishGeometry() {
                    const p = mapToGlobal(0, 0);
                    tasksModel.requestPublishDelegateGeometry(modelIndex, Qt.rect(p.x, p.y, width, height), task);
                }
                Timer {
                    id: publishTimer
                    interval: 300
                    onTriggered: if (dock.amount === 0) task.publishGeometry()
                }
                // también con una ventana más en el grupo (misma x) o al recentrarse la fila
                readonly property int childCount: model.ChildCount || 0
                onChildCountChanged: publishTimer.restart()
                onXChanged: publishTimer.restart()
                onWidthChanged: publishTimer.restart()
                Connections {
                    target: row
                    function onXChanged() { publishTimer.restart(); }
                }
                Component.onCompleted: publishTimer.restart()
            }
        }

        // Recientes
        DockSeparator {
            visible: dock.recentCount > 0
            width: dock.separatorWidth
            height: dock.iconSize
            y: row.height - height
        }
        Repeater {
            model: dock.recentCount > 0 ? dock.recents : []
            delegate: DockIcon {
                id: recent
                required property int index
                required property var modelData
                size: dock.sizeAt(dock.centerOf(1 + dock.taskCount + index, 1))
                y: row.height - height
                padding: dock.pad
                maxSize: dock.maxSize
                iconSource: modelData.icon
                label: modelData.name
                hovered: recentArea.containsMouse
                pressed: recentArea.pressed
                MouseArea {
                    id: recentArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: recentModel.trigger(recent.modelData.row, "", null)
                }
            }
        }

        // Papelera
        DockSeparator {
            width: dock.separatorWidth
            height: dock.iconSize
            y: row.height - height
        }
        DockIcon {
            id: trashIcon
            size: dock.sizeAt(dock.centerOf(1 + dock.taskCount + dock.recentCount, dock.separatorCount))
            y: row.height - height
            padding: dock.pad
            maxSize: dock.maxSize
            iconSource: trash.iconName
            label: i18n("Trash")
            hovered: trash.containsMouse || trash.dropping
            pressed: trash.pressed
            TrashButton {
                id: trash
                anchors.fill: parent
                showIcon: false
            }
        }
    }

    // --- geometría de la placa para el Panel.qml de GoldenGlass ------------------------
    property Item panelRoot: null

    function findPanelRoot() {
        for (let p = dock.parent; p; p = p.parent) {
            if (p.goldenglassDockSlab !== undefined) {
                return p;
            }
        }
        return null;
    }

    function publishSlab() {
        if (!panelRoot) {
            panelRoot = findPanelRoot();
        }
        if (!panelRoot) {
            return; // otro shell: el panel dibuja su fondo normal
        }
        panelRoot.goldenglassSetThickness(panelThickness);
        const r = slab.mapToItem(panelRoot, 0, 0, slab.width, slab.height);
        panelRoot.goldenglassDockSlab = Qt.rect(Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height));
    }

    Connections {
        target: slab
        function onXChanged() { dock.publishSlab(); }
        function onYChanged() { dock.publishSlab(); }
        function onWidthChanged() { dock.publishSlab(); }
        function onHeightChanged() { dock.publishSlab(); }
    }
    onParentChanged: Qt.callLater(publishSlab)
    onWidthChanged: publishSlab()
    onHeightChanged: publishSlab()
    Component.onCompleted: Qt.callLater(publishSlab)
    Component.onDestruction: {
        if (panelRoot) {
            panelRoot.goldenglassDockSlab = Qt.rect(0, 0, 0, 0);
        }
    }
}
