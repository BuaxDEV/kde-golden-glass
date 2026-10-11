/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Panel de Apps: diálogo de Plasma centrado en la pantalla (fondo de vidrio,
    blur y sombra del Plasma Style), como Apps de macOS 26/27:

      [ buscador                               ] [⊞/☰] [⋯]
      ( Todas ) ( Utilidades ) ( Productividad y finanzas ) …
      Sugeridas
      ▢ ▢ ▢ ▢ ▢ ▢
      Utilidades                                   Mostrar más
      ▢ ▢ ▢ ▢ ▢ ▢
      …

    El foco se queda en el buscador: escribir filtra, las flechas mueven la
    selección, Return abre, Tab cambia de etiqueta y Escape borra la búsqueda,
    luego la etiqueta y luego cierra. Si lo escrito no es una app, «Buscar en
    Spotlight» pasa la consulta a KRunner.
*/

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.kirigami as Kirigami
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

import "categories.js" as Categories
import "tokens.js" as T

PlasmaCore.Dialog {
    id: panel

    property var plasmoidItem
    property var appsByCategory: ({})
    property var allApps: []
    property var suggestions: []
    property var searchResults: []

    readonly property alias query: searchField.text
    readonly property var tok: T.tokens.apps
    readonly property int suggestedCount: tok.suggested
    readonly property bool listMode: Plasmoid.configuration.viewMode === "list"
    readonly property bool byName: Plasmoid.configuration.sortMode === "name"
    readonly property int columns: listMode ? 1 : tok.columns
    readonly property int perSection: listMode ? 5 : tok.columns * tok.section_rows

    property string filter: ""     // categoría elegida ("" = todas)
    property var expanded: ({})     // categoría → «Mostrar más» abierto
    property int current: 0         // selección, en el orden de navegación

    location: PlasmaCore.Types.Floating
    flags: Qt.WindowStaysOnTopHint
    // un menú abierto es otra ventana: que no cierre el panel al tomar el foco
    hideOnWindowDeactivate: !contextMenu.opened && !sortMenu.opened

    // --- datos ----------------------------------------------------------------

    function label(id) {
        switch (id) {
        case "": return i18n("All");
        case "utilities": return i18n("Utilities");
        case "productivity": return i18n("Productivity & Finance");
        case "social": return i18n("Social");
        case "creativity": return i18n("Creativity");
        case "reading": return i18n("Information & Reading");
        case "entertainment": return i18n("Entertainment");
        default: return i18n("Other");
        }
    }

    readonly property var categoryOfId: {
        const map = {};
        for (const cat in appsByCategory) {
            for (const entry of appsByCategory[cat]) {
                map[entry.id] = cat;
            }
        }
        return map;
    }

    readonly property var chips: [""].concat(Categories.order.filter(c => (appsByCategory[c] || []).length > 0))

    // Secciones visibles: { id, title, items, shown, more, bridge }
    readonly property var sections: {
        const out = [];
        const q = query.trim();
        const inFilter = entry => !filter || categoryOfId[entry.id] === filter;
        if (q.length > 0) {
            const items = searchResults.filter(inFilter);
            if (items.length > 0) {
                out.push({ id: "results", title: i18n("Applications"), items: items, shown: items, more: false });
            }
            out.push({ id: "bridge", title: "", items: [], shown: [{ bridge: true, name: q }], more: false, bridge: true });
        } else if (byName) {
            const items = allApps.filter(inFilter);
            out.push({ id: "all", title: filter ? label(filter) : i18n("All Applications"), items: items, shown: items, more: false });
        } else {
            if (!filter && suggestions.length > 0) {
                const items = suggestions.slice(0, tok.suggested);
                out.push({ id: "suggested", title: i18n("Suggested"), items: items, shown: items, more: false });
            }
            for (const cat of Categories.order) {
                const items = appsByCategory[cat] || [];
                if (items.length === 0 || (filter && cat !== filter)) {
                    continue;
                }
                const open = filter || expanded[cat];
                out.push({ id: cat, title: label(cat), items: items,
                           shown: open ? items : items.slice(0, perSection), more: !filter && items.length > perSection });
            }
        }
        let offset = 0;
        for (const s of out) {
            s.offset = offset;
            offset += s.shown.length;
        }
        return out;
    }
    readonly property int total: sections.length > 0 ? sections[sections.length - 1].offset + sections[sections.length - 1].shown.length : 0

    onSectionsChanged: current = Math.min(current, Math.max(0, total - 1))
    onQueryChanged: current = 0
    onFilterChanged: current = 0

    function entryAt(index) {
        for (const s of sections) {
            if (index >= s.offset && index < s.offset + s.shown.length) {
                return s.shown[index - s.offset];
            }
        }
        return null;
    }

    // Flechas sobre secciones de cuadrícula consecutivas (la del puente es de 1).
    function move(dx, dy) {
        if (total === 0) {
            return;
        }
        if (dx !== 0) {
            current = Math.max(0, Math.min(total - 1, current + dx));
            return;
        }
        let si = sections.findIndex(s => current >= s.offset && current < s.offset + s.shown.length);
        const s = sections[si];
        const cols = s.bridge ? 1 : columns;
        const pos = current - s.offset;
        const col = pos % cols;
        const lastRow = Math.floor((s.shown.length - 1) / cols);
        if (dy > 0) {
            if (pos + cols < s.shown.length) {
                current += cols;
            } else if (Math.floor(pos / cols) < lastRow) {
                current = s.offset + s.shown.length - 1;
            } else if (si + 1 < sections.length) {
                const n = sections[si + 1];
                current = n.offset + Math.min(col, n.shown.length - 1);
            }
        } else {
            if (pos - cols >= 0) {
                current -= cols;
            } else if (si > 0) {
                const p = sections[si - 1];
                const pcols = p.bridge ? 1 : columns;
                const start = Math.floor((p.shown.length - 1) / pcols) * pcols;
                current = p.offset + Math.min(start + col, p.shown.length - 1);
            }
        }
    }

    function cycleFilter(step) {
        const i = chips.indexOf(filter);
        filter = chips[(i + step + chips.length) % chips.length];
    }

    function toggleExpanded(id) {
        const next = Object.assign({}, expanded);
        next[id] = !next[id];
        expanded = next;
    }

    // --- acciones -------------------------------------------------------------

    function launch(entry) {
        if (!entry) {
            return;
        }
        if (entry.bridge) {
            openSpotlight(entry.name);
        } else {
            entry.model.trigger(entry.row, "", null);
        }
        close();
    }

    function openSpotlight(text) {
        const quoted = "'" + text.replace(/'/g, "'\\''") + "'";
        executable.connectSource("dbus-send --session --type=method_call --dest=org.kde.krunner /App "
                                 + "org.kde.krunner.App.query string:" + quoted);
    }

    // --- abrir y cerrar -------------------------------------------------------

    function place() {
        const geo = Plasmoid.containment.screenGeometry;
        x = geo.x + Math.round((geo.width - width) / 2);
        y = geo.y + Math.round((geo.height - height) * 0.42); // algo por encima del centro, como Spotlight
    }
    onWidthChanged: place()
    onHeightChanged: place()

    function toggle() {
        if (visible) {
            close();
            return;
        }
        searchField.text = "";
        filter = "";
        expanded = {};
        current = 0;
        place();
        visible = true;
        requestActivate();
        searchField.forceActiveFocus();
    }

    function close() {
        contextMenu.dismiss();
        visible = false;
    }

    // --- interfaz -------------------------------------------------------------

    mainItem: FocusScope {
        width: panel.tok.width
        height: panel.tok.height

        // (Dialog solo admite Items como hijos directos: lo demás va aquí)
        P5Support.DataSource {
            id: executable
            engine: "executable"
            connectedSources: []
            onNewData: source => disconnectSource(source)
        }

        // Menús como ventanas emergentes propias (Qt ≥ 6.8): dentro de la
        // ventana del panel quedarían recortados por sus bordes y sin el blur
        // de KWin detrás (el vidrio del menú sería ilegible).
        PlasmaComponents3.Menu {
            id: contextMenu
            popupType: QQC2.Popup.Window
            margins: Kirigami.Units.smallSpacing // si Qt lo dibuja dentro del panel, que no se salga
            property var entry: null

            function show(entry, item) {
                contextMenu.entry = entry;
                popup(); // donde está el cursor, como en macOS
            }

            PlasmaComponents3.MenuItem {
                text: i18n("Open")
                icon.name: "system-run"
                onTriggered: panel.launch(contextMenu.entry)
            }
            PlasmaComponents3.MenuSeparator {}
            Instantiator {
                model: contextMenu.entry ? contextMenu.entry.actions().filter(a => a.actionId && a.text) : []
                delegate: PlasmaComponents3.MenuItem {
                    required property var modelData
                    text: modelData.text
                    icon.name: typeof modelData.icon === "string" ? modelData.icon : ""
                    onTriggered: {
                        const e = contextMenu.entry;
                        e.model.trigger(e.row, modelData.actionId, modelData.actionArgument);
                        panel.close();
                    }
                }
                onObjectAdded: (index, object) => contextMenu.insertItem(2 + index, object)
                onObjectRemoved: (index, object) => contextMenu.removeItem(object)
            }
        }


        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                PlasmaExtras.SearchField {
                    id: searchField
                    Layout.fillWidth: true
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 2.2
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.35
                    placeholderText: i18n("Search")
                    focus: true

                    Keys.onPressed: event => {
                        switch (event.key) {
                        case Qt.Key_Up: panel.move(0, -1); break;
                        case Qt.Key_Down: panel.move(0, 1); break;
                        case Qt.Key_Left: panel.move(-1, 0); break;
                        case Qt.Key_Right: panel.move(1, 0); break;
                        case Qt.Key_Tab: panel.cycleFilter(1); break;
                        case Qt.Key_Backtab: panel.cycleFilter(-1); break;
                        case Qt.Key_Return:
                        case Qt.Key_Enter: panel.launch(panel.entryAt(panel.current)); break;
                        case Qt.Key_Backspace:
                            if (text.length > 0 || !panel.filter) {
                                return; // borrar texto
                            }
                            panel.filter = ""; // sin texto, Supr quita la etiqueta
                            break;
                        case Qt.Key_Escape:
                            if (text.length > 0) {
                                text = "";
                            } else if (panel.filter) {
                                panel.filter = "";
                            } else {
                                panel.close();
                            }
                            break;
                        default:
                            return;
                        }
                        event.accepted = true;
                    }
                }

                PlasmaComponents3.ToolButton {
                    icon.name: panel.listMode ? "view-list-icons" : "view-list-details"
                    display: QQC2.AbstractButton.IconOnly
                    text: panel.listMode ? i18n("Show as Grid") : i18n("Show as List")
                    PlasmaComponents3.ToolTip.text: text
                    PlasmaComponents3.ToolTip.visible: hovered
                    onClicked: Plasmoid.configuration.viewMode = panel.listMode ? "grid" : "list"
                }

                PlasmaComponents3.ToolButton {
                    id: sortButton
                    icon.name: "overflow-menu"
                    display: QQC2.AbstractButton.IconOnly
                    text: i18n("Sort")
                    onClicked: sortMenu.popup(sortButton, 0, sortButton.height)

                    PlasmaComponents3.Menu {
                        id: sortMenu
                        popupType: QQC2.Popup.Window
                        margins: Kirigami.Units.smallSpacing // si Qt lo dibuja dentro del panel, que no se salga
                        PlasmaComponents3.MenuItem {
                            text: i18n("By Category")
                            checkable: true
                            checked: !panel.byName
                            onTriggered: Plasmoid.configuration.sortMode = "category"
                        }
                        PlasmaComponents3.MenuItem {
                            text: i18n("By Name")
                            checkable: true
                            checked: panel.byName
                            onTriggered: Plasmoid.configuration.sortMode = "name"
                        }
                    }
                }
            }

            // Etiquetas de categoría
            ListView {
                id: chipBar
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 1.6
                orientation: ListView.Horizontal
                spacing: Kirigami.Units.smallSpacing
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: panel.chips
                currentIndex: panel.chips.indexOf(panel.filter)
                highlightFollowsCurrentItem: false
                onCurrentIndexChanged: positionViewAtIndex(Math.max(0, currentIndex), ListView.Contain)

                delegate: QQC2.AbstractButton {
                    id: chip
                    required property string modelData
                    readonly property bool selected: panel.filter === modelData
                    height: chipBar.height
                    leftPadding: Kirigami.Units.largeSpacing
                    rightPadding: Kirigami.Units.largeSpacing
                    focusPolicy: Qt.NoFocus
                    hoverEnabled: true
                    onClicked: panel.filter = modelData

                    background: Rectangle {
                        radius: height / 2
                        color: chip.selected ? Kirigami.Theme.highlightColor
                                             : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                       Kirigami.Theme.textColor.b, chip.hovered ? 0.14 : 0.08)
                    }
                    contentItem: PlasmaComponents3.Label {
                        text: panel.label(chip.modelData)
                        color: chip.selected ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                        verticalAlignment: Text.AlignVCenter
                        textFormat: Text.PlainText
                    }
                }
            }

            PlasmaComponents3.ScrollView {
                id: scroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                PlasmaComponents3.ScrollBar.horizontal.policy: PlasmaComponents3.ScrollBar.AlwaysOff

                Column {
                    id: content
                    width: scroll.availableWidth
                    spacing: Kirigami.Units.largeSpacing

                    Repeater {
                        model: panel.sections
                        delegate: Section {
                            required property var modelData
                            owner: panel
                            section: modelData
                            width: content.width
                        }
                    }

                    PlasmaComponents3.Label {
                        visible: panel.total === 0 && panel.query.length === 0
                        width: content.width
                        topPadding: Kirigami.Units.gridUnit * 4
                        horizontalAlignment: Text.AlignHCenter
                        text: i18n("No applications")
                        opacity: 0.6
                    }
                }
            }
        }
    }

    // Desplaza la vista para que se vea `item` (el seleccionado).
    function ensureVisible(item) {
        const flick = scroll.contentItem;
        const p = item.mapToItem(content, 0, 0);
        if (p.y < flick.contentY) {
            flick.contentY = Math.max(0, p.y - Kirigami.Units.smallSpacing);
        } else if (p.y + item.height > flick.contentY + flick.height) {
            flick.contentY = p.y + item.height - flick.height + Kirigami.Units.smallSpacing;
        }
    }

    function showContextMenu(entry, item) {
        contextMenu.show(entry, item);
    }

    // --- componentes ----------------------------------------------------------
    // Los componentes en línea no ven los id del documento: el panel se pasa
    // como «owner».

    component Section: Column {
        id: sectionItem
        property var owner
        property var section
        spacing: Kirigami.Units.smallSpacing

        RowLayout {
            width: parent.width
            visible: sectionItem.section.title.length > 0

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 5
                text: sectionItem.section.title
                opacity: 0.75
                textFormat: Text.PlainText
            }
            PlasmaComponents3.ToolButton {
                visible: sectionItem.section.more
                text: owner.expanded[sectionItem.section.id] ? i18n("Show Less") : i18n("Show More")
                onClicked: owner.toggleExpanded(sectionItem.section.id)
            }
        }

        Grid {
            width: parent.width
            columns: sectionItem.section.bridge ? 1 : owner.columns

            Repeater {
                model: sectionItem.section.shown
                delegate: AppItem {
                    required property var modelData
                    required property int index
                    owner: sectionItem.owner
                    entry: modelData
                    flatIndex: sectionItem.section.offset + index
                    width: sectionItem.section.bridge || owner.listMode ? sectionItem.width
                                                                       : sectionItem.width / owner.columns
                }
            }
        }
    }

    component AppItem: MouseArea {
        id: item
        property var owner
        property var entry
        property int flatIndex
        readonly property bool isCurrent: owner.current === flatIndex
        readonly property bool row: owner.listMode || entry.bridge === true

        height: row ? Kirigami.Units.gridUnit * 2 : owner.tok.icon_size + Kirigami.Units.gridUnit * 2.4
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton && !entry.bridge) {
                owner.showContextMenu(entry, item);
            } else {
                owner.launch(entry);
            }
        }
        onIsCurrentChanged: if (isCurrent) owner.ensureVisible(item)

        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: Kirigami.Units.cornerRadius * 2
            color: item.isCurrent ? Qt.rgba(Kirigami.Theme.highlightColor.r, Kirigami.Theme.highlightColor.g,
                                            Kirigami.Theme.highlightColor.b, 0.28)
                 : item.containsMouse ? Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                                Kirigami.Theme.textColor.b, 0.08)
                 : "transparent"
        }

        // Cuadrícula: icono grande con el nombre debajo
        ColumnLayout {
            visible: !item.row
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.smallSpacing * 2
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: owner.tok.icon_size
                Layout.preferredHeight: owner.tok.icon_size
                source: item.entry.icon || ""
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: item.entry.name
                elide: Text.ElideRight
                maximumLineCount: 1
                textFormat: Text.PlainText
            }
        }

        // Lista (y el puente a Spotlight): icono pequeño y nombre
        RowLayout {
            visible: item.row
            anchors.fill: parent
            anchors.leftMargin: Kirigami.Units.largeSpacing
            anchors.rightMargin: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            Kirigami.Icon {
                Layout.preferredWidth: owner.tok.list_icon_size
                Layout.preferredHeight: owner.tok.list_icon_size
                source: item.entry.bridge ? "search" : (item.entry.icon || "")
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                text: item.entry.bridge ? i18n("Search “%1” in Spotlight", item.entry.name) : item.entry.name
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }
    }
}
