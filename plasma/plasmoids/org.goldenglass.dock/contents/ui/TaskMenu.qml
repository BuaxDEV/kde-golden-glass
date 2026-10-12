/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Menú contextual de una app del dock, como el de macOS:

      [acciones de la app (las del .desktop)]
      Nueva ventana · Abrir
      Mantener en el Dock
      Salir

    Las acciones salen de Kicker (SimpleFavoritesModel, como el menú de
    Plasma) y se leen solo al abrir el menú: Kicker consulta la contención
    para calcularlas y, durante la carga, todavía no existe.
*/

import QtQuick
import QtQuick.Controls as QQC2

import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.private.kicker as Kicker

PlasmaComponents3.Menu {
    id: root

    required property var tasksModel
    required property var modelIndex
    required property var model
    required property string desktopId
    required property bool pinned
    required property bool running

    property var actions: []

    popupType: QQC2.Popup.Window

    Kicker.SimpleFavoritesModel {
        id: favorites
        favorites: root.desktopId ? [root.desktopId] : []
    }
    Instantiator {
        id: reader
        model: favorites
        delegate: QtObject {
            required property var model
            function actionList() {
                return model.actionList || [];
            }
        }
    }

    onAboutToShow: {
        const entry = reader.objectAt(0);
        actions = entry ? entry.actionList().filter(a => a.actionId && a.text && a.type !== "title") : [];
    }

    Instantiator {
        model: root.actions
        delegate: PlasmaComponents3.MenuItem {
            required property var modelData
            text: modelData.text
            icon.name: typeof modelData.icon === "string" ? modelData.icon : ""
            onTriggered: favorites.trigger(0, modelData.actionId, modelData.actionArgument)
        }
        onObjectAdded: (index, object) => root.insertItem(index, object)
        onObjectRemoved: (index, object) => root.removeItem(object)
    }

    PlasmaComponents3.MenuSeparator {
        visible: root.actions.length > 0
        height: visible ? implicitHeight : 0
    }

    PlasmaComponents3.MenuItem {
        text: i18n("New Window")
        icon.name: "window-new"
        visible: root.running && root.model.CanLaunchNewInstance === true
        height: visible ? implicitHeight : 0
        onTriggered: root.tasksModel.requestNewInstance(root.modelIndex)
    }
    PlasmaComponents3.MenuItem {
        text: i18n("Open")
        icon.name: "media-playback-start"
        visible: !root.running
        height: visible ? implicitHeight : 0
        onTriggered: root.tasksModel.requestNewInstance(root.modelIndex)
    }

    PlasmaComponents3.MenuSeparator {}

    PlasmaComponents3.MenuItem {
        text: i18n("Keep in Dock")
        checkable: true
        checked: root.pinned
        onTriggered: {
            if (root.pinned) {
                root.tasksModel.requestRemoveLauncher(root.model.LauncherUrlWithoutIcon);
            } else {
                root.tasksModel.requestAddLauncher(root.model.LauncherUrl);
            }
        }
    }

    PlasmaComponents3.MenuSeparator {
        visible: root.running
        height: visible ? implicitHeight : 0
    }
    PlasmaComponents3.MenuItem {
        text: i18n("Quit")
        icon.name: "application-exit"
        visible: root.running
        height: visible ? implicitHeight : 0
        onTriggered: root.tasksModel.requestClose(root.modelIndex)
    }
}
