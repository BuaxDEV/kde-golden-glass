/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Apps: icono en el dock que abre un panel centrado con todas las
    aplicaciones (buscador, categorías, sugeridas, cuadrícula o lista), como
    Apps de macOS 26/27. Se declara como lanzador
    (org.kde.plasma.launchermenu): la tecla Meta lo abre.

    Los datos salen de los modelos de Kicker (los del menú de Plasma): aquí se
    leen por nombre de rol con Instantiator y se reúnen en listas de entradas
    { name, icon, id, actions, model, row } para el panel.
*/

import QtQuick
import QtQml

import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid
import org.kde.plasma.private.kicker as Kicker

import "categories.js" as Categories

PlasmoidItem {
    id: root

    // El icono es la representación «completa»: no hay popup, sino panel.
    preferredRepresentation: fullRepresentation
    toolTipMainText: Plasmoid.title
    toolTipSubText: ""

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
        appletInterface: root
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
        appletInterface: root
        runners: ["krunner_services"]
        mergeResults: true
        query: root.query
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
            actions: () => reader.model.actionList || [],
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
                groups[key].sort(root.byName);
            }
            root.appsByCategory = groups;
            root.allApps = all.sort(root.byName);
        }
    }

    Timer {
        id: rebuildSuggestions
        interval: 50
        onTriggered: {
            const out = [];
            for (let i = 0; i < recentReader.count && out.length < panel.suggestedCount; ++i) {
                const item = recentReader.objectAt(i);
                if (item && item.entry.name) {
                    out.push(item.entry);
                }
            }
            root.suggestions = out;
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
            root.searchResults = out;
        }
    }

    // --- panel ----------------------------------------------------------------
    AppsPanel {
        id: panel
        plasmoidItem: root
        appsByCategory: root.appsByCategory
        allApps: root.allApps
        suggestions: root.suggestions
        searchResults: root.query.length > 0 ? root.searchResults : []
        onVisibleChanged: {
            if (visible) {
                rebuildSuggestions.restart();
            }
        }
    }

    function toggle() {
        panel.toggle();
    }

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.toggle();
        }
    }

    fullRepresentation: MouseArea {
        id: icon
        hoverEnabled: true
        onClicked: root.toggle()

        Kirigami.Icon {
            anchors.fill: parent
            source: Qt.resolvedUrl("../images/launchpad.svg")
            active: icon.containsMouse
        }
    }
}
