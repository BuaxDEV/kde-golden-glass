/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Apps: modelos de Kicker (categorías, recientes, búsqueda) y el panel
    centrado (AppsPanel). Lo usan el plasmoid Apps (org.goldenglass.launchpad)
    y el dock (org.goldenglass.dock), que lo copia al generarse
    (tools/plasmoids.py): un solo código para los dos.

    Los datos se leen por nombre de rol con Instantiator y se reúnen en listas
    de entradas { name, icon, id, url, actions, model, row } para el panel.

    Mientras el panel está abierto, el plasmoid pide atención
    (NeedsAttentionStatus): un panel autoocultable (el dock) aparece y no se
    esconde, y se puede soltar en él una app arrastrada desde el panel.
*/

import QtQuick
import QtQml

import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.plasma.private.kicker as Kicker

import "categories.js" as Categories

Item {
    id: launcher

    // el PlasmoidItem que lo contiene (Kicker lo necesita como appletInterface)
    required property var plasmoidItem
    readonly property bool opened: panel.visible
    // el dock que lo contiene (DockView: isAppPinned, pinApp, unpinApp) o null
    property var dock: null

    Binding {
        target: Plasmoid
        property: "status"
        value: PlasmaCore.Types.NeedsAttentionStatus
        when: panel.visible
    }

    // --- datos para el panel ------------------------------------------------
    // categoría macOS → [entradas], ordenadas por nombre
    property var appsByCategory: ({})
    // todas las apps, ordenadas por nombre (vista «por nombre»)
    property var allApps: []
    property var suggestions: []
    property var searchResults: []
    readonly property string query: panel.query

    // Categorías del menú de KDE, aplanadas (cada fila: una categoría)
    Kicker.RootModel {
        id: rootModel
        autoPopulate: false
        appletInterface: launcher.plasmoidItem
        appNameFormat: 0 // solo el nombre de la app
        flat: true
        sorted: true
        showSeparators: false
        showTopLevelItems: false
        showAllApps: false
        showAllAppsCategorized: true
        showRecentApps: false
        showRecentDocs: false
        showRecentFolders: false
        showPowerSession: false
        showFavoritesPlaceholder: false
        Component.onCompleted: refresh()
    }

    Kicker.RecentUsageModel {
        id: recentModel
        shownItems: Kicker.RecentUsageModel.OnlyApps
    }

    Kicker.RunnerModel {
        id: runnerModel
        appletInterface: launcher.plasmoidItem
        runners: ["krunner_services"]
        mergeResults: true
        query: launcher.query
    }

    // Lee una entrada de un modelo de Kicker por nombre de rol. Las acciones
    // (actionList) se leen solo al abrir el menú contextual: Kicker consulta la
    // containment del applet para calcularlas y, durante la carga inicial,
    // todavía no existe (plasmashell se cae).
    component Entry: QtObject {
        id: reader
        required property var model
        required property int index
        property var sourceModel
        readonly property var entry: ({
            name: model.display,
            icon: model.decoration,
            id: model.favoriteId || "",
            url: model.url ? String(model.url) : "",
            // la entrada puede sobrevivir a su lector (las listas se rehacen
            // con retraso): sin él, no hay acciones
            actions: () => {
                try {
                    return reader.model.actionList || [];
                } catch (e) {
                    return [];
                }
            },
            model: sourceModel,
            row: index,
        })
    }

    // Una lista de entradas por categoría del menú
    Instantiator {
        id: categoryReaders
        model: rootModel
        delegate: Instantiator {
            id: reader
            // «model» ya es una propiedad de Instantiator: los roles se piden por nombre
            required property int index
            required property var decoration
            readonly property string category: Categories.categoryFor(decoration)
            model: rootModel.modelForRow(index)
            delegate: Entry {
                sourceModel: reader.model
            }
            onObjectAdded: rebuild.restart()
            onObjectRemoved: rebuild.restart()
        }
        onObjectAdded: rebuild.restart()
        onObjectRemoved: rebuild.restart()
    }

    Instantiator {
        id: recentReader
        model: recentModel
        delegate: Entry {
            sourceModel: recentModel
        }
        onObjectAdded: rebuildSuggestions.restart()
        onObjectRemoved: rebuildSuggestions.restart()
    }

    Instantiator {
        id: resultsReader
        model: runnerModel.count > 0 ? runnerModel.modelForRow(0) : null
        delegate: Entry {
            sourceModel: resultsReader.model
        }
        onObjectAdded: rebuildResults.restart()
        onObjectRemoved: rebuildResults.restart()
    }

    function byName(a, b) {
        return a.name.localeCompare(b.name);
    }

    Timer {
        id: rebuild
        interval: 50
        onTriggered: {
            const groups = {};
            const all = [];
            const seen = new Set();
            for (let i = 0; i < categoryReaders.count; ++i) {
                const reader = categoryReaders.objectAt(i);
                if (!reader) {
                    continue;
                }
                for (let j = 0; j < reader.count; ++j) {
                    const item = reader.objectAt(j);
                    if (!item || !item.entry.name || seen.has(item.entry.id || item.entry.name)) {
                        continue;
                    }
                    seen.add(item.entry.id || item.entry.name);
                    (groups[reader.category] = groups[reader.category] || []).push(item.entry);
                    all.push(item.entry);
                }
            }
            for (const key in groups) {
                groups[key].sort(launcher.byName);
            }
            launcher.appsByCategory = groups;
            launcher.allApps = all.sort(launcher.byName);
        }
    }

    Timer {
        id: rebuildSuggestions
        interval: 50
        onTriggered: {
            const out = [];
            for (let i = 0; i < recentReader.count && out.length < panel.recentCount; ++i) {
                const item = recentReader.objectAt(i);
                if (item && item.entry.name) {
                    out.push(item.entry);
                }
            }
            launcher.suggestions = out;
        }
    }

    Timer {
        id: rebuildResults
        interval: 30
        onTriggered: {
            const out = [];
            for (let i = 0; i < resultsReader.count; ++i) {
                const item = resultsReader.objectAt(i);
                if (item && item.entry.name) {
                    out.push(item.entry);
                }
            }
            launcher.searchResults = out;
        }
    }

    // --- panel ----------------------------------------------------------------
    AppsPanel {
        id: panel
        plasmoidItem: launcher.plasmoidItem
        dock: launcher.dock
        appsByCategory: launcher.appsByCategory
        allApps: launcher.allApps
        suggestions: launcher.suggestions
        searchResults: launcher.query.length > 0 ? launcher.searchResults : []
        onVisibleChanged: {
            if (visible) {
                rebuildSuggestions.restart();
            }
        }
    }

    function toggle() {
        panel.toggle();
    }
}
