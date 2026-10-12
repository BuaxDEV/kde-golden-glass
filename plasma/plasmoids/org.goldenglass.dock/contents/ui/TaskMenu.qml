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
    para calcularlas y, durante la carga, todavía no existe. Solo las de la
    app (_kicker_jumpListAction): Kicker añade también documentos recientes,
    Editar aplicación…, Desinstalar…, que en el dock sobran.

    Es un QMenu (PlasmaExtras.Menu) y no un Menu de Qt Quick: como ventana
    propia, el de Qt Quick no tiene blur de KWin detrás y su vidrio es
    ilegible; el QMenu lo dibuja el kstyle GoldenGlass, que sí lo pide.
*/

import QtQuick

import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.private.kicker as Kicker

Item {
    id: root

    // TasksModel del dock. No se llama tasksModel: en el delegado,
    // «tasksModel: tasksModel» resolvería a esta misma propiedad (undefined)
    // y no al id de DockView.
    required property var tasks
    required property var modelIndex
    required property var model
    required property string desktopId
    required property bool pinned
    required property bool running

    property var actions: []
    readonly property bool opened: menu.status !== PlasmaExtras.Menu.Closed

    // abre el menú en (x, y) del elemento que lo contiene
    function open(x: real, y: real): void {
        const entry = reader.objectAt(0);
        actions = entry ? entry.actionList().filter(a => a.actionId === "_kicker_jumpListAction" && a.text) : [];
        // al pulsar, QAction cambia la marca sola: se rehace al abrir
        keepItem.checked = pinned;
        menu.visualParent = parent;
        menu.open(x, y);
    }

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

    // acciones de la app, delante de su separador
    Instantiator {
        model: root.actions
        delegate: PlasmaExtras.MenuItem {
            required property var modelData
            text: modelData.text
            icon: typeof modelData.icon === "string" ? modelData.icon : ""
            onClicked: favorites.trigger(0, modelData.actionId, modelData.actionArgument)
        }
        onObjectAdded: (index, object) => menu.addMenuItem(object, actionsSeparator)
        onObjectRemoved: (index, object) => menu.removeMenuItem(object)
    }

    PlasmaExtras.Menu {
        id: menu

        PlasmaExtras.MenuItem {
            id: actionsSeparator
            separator: true
            visible: root.actions.length > 0
        }

        PlasmaExtras.MenuItem {
            text: i18n("New Window")
            icon: "window-new"
            visible: root.running && root.model.CanLaunchNewInstance === true
            onClicked: root.tasks.requestNewInstance(root.modelIndex)
        }
        PlasmaExtras.MenuItem {
            text: i18n("Open")
            icon: "media-playback-start"
            visible: !root.running
            onClicked: root.tasks.requestNewInstance(root.modelIndex)
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            id: keepItem
            text: i18n("Keep in Dock")
            checkable: true
            onClicked: {
                if (root.pinned) {
                    root.tasks.requestRemoveLauncher(root.model.LauncherUrlWithoutIcon);
                } else {
                    root.tasks.requestAddLauncher(root.model.LauncherUrl);
                }
            }
        }

        PlasmaExtras.MenuItem {
            separator: true
            visible: root.running
        }
        PlasmaExtras.MenuItem {
            text: i18n("Quit")
            icon: "application-exit"
            visible: root.running
            onClicked: root.tasks.requestClose(root.modelIndex)
        }
    }
}
