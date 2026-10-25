/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Panel de Apps, como el de macOS 27: una pieza de vidrio centrada en la
    pantalla, algo por encima del centro, con esquinas amplias y sombra:

      ⊞  Búsqueda en Spotlight                                 ⋯
      ─────────────────────────────────────────────────────────
      [Utilidades] [Herramientas para desarrolladores] [Redes s…   (hasta el borde)
       ▢    ▢    ▢    ▢    ▢    ▢    ▢          ← recientes
      ─────────────────────────────────────────────────────────
       ▢    ▢    ▢    ▢    ▢    ▢    ▢          ← todas, de la A a la Z
       …

    Las etiquetas filtran por categoría (otra pulsación quita el filtro) y
    «⋯» cambia entre cuadrícula y lista. Es un PlasmaCore.Dialog sin fondo:
    el vidrio lo dibuja el panel y GlassBlur pide a KWin el blur solo detrás de
    él, con su radio; la opacidad sigue el nivel de vidrio (goldenglassrc).

    El desplazamiento es el de macOS (GlassScrollView): barra superpuesta,
    rueda suave, inercia, rebote y las apps se difuminan bajo las etiquetas.

    Al abrir crece un poco desde el centro con un resorte suave y aparece; al
    cerrar se encoge y se desvanece. Se cierra con Escape, al lanzar una app,
    con un clic fuera o al irse el foco a otra ventana.

    El foco se queda en el buscador: escribir filtra, las flechas mueven la
    selección (solo se ve al usar el teclado o al buscar), Return abre, Tab
    cambia de etiqueta y Escape borra la búsqueda, luego la etiqueta y luego
    cierra. Si lo escrito no es una app, «Buscar en Spotlight» pasa la consulta
    a KRunner.

    Las apps se pueden arrastrar (su .desktop, como en Kickoff): al dock, que
    las fija donde se sueltan, al escritorio o a Dolphin. En el dock, el menú
    contextual trae además «Mantener en el Dock».
*/

import QtQuick
import QtQuick.Effects
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
    property var dock: null         // DockView si el panel es del dock
    property var appsByCategory: ({})
    property var allApps: []
    property var suggestions: []
    property var searchResults: []

    readonly property alias query: searchField.text
    readonly property var tok: T.tokens.apps
    readonly property int recentCount: tok.recent
    readonly property bool listMode: Plasmoid.configuration.viewMode === "list"
    readonly property int columns: listMode ? 1 : tok.columns
    // margen transparente alrededor del vidrio: sitio para la sombra
    readonly property int shadowRoom: tok.shadow_blur + tok.shadow_offset

    property string filter: ""     // categoría elegida ("" = ninguna)
    property int current: 0         // selección, en el orden de navegación
    property bool keyboardUsed: false
    readonly property bool showSelection: keyboardUsed || query.length > 0
    property bool closing: false

    // nivel del slider de vidrio (goldenglassrc), leído al abrir
    property real glassLevel: T.tokens.glass.default_level
    readonly property string glassLevelCommand: "kreadconfig6 --file goldenglassrc --group Glass --key Level --default "
                                                + T.tokens.glass.default_level
    // opacidad del vidrio para ese nivel, interpolada entre las muescas (como plasma_theme.glass_alpha)
    readonly property real glassAlpha: {
        const notches = Object.values(T.tokens.glass.notch).sort((a, b) => a.position - b.position);
        const level = Math.min(Math.max(glassLevel, notches[0].position), notches[notches.length - 1].position);
        for (let i = 0; i + 1 < notches.length; ++i) {
            const a = notches[i], b = notches[i + 1];
            if (level <= b.position) {
                return a.alpha + (level - a.position) / (b.position - a.position) * (b.alpha - a.alpha);
            }
        }
        return notches[notches.length - 1].alpha;
    }

    readonly property bool menuOpen: contextMenu.status !== PlasmaExtras.Menu.Closed
                                     || moreMenu.status !== PlasmaExtras.Menu.Closed

    backgroundHints: PlasmaCore.Dialog.NoBackground
    location: PlasmaCore.Types.Floating
    // mientras se cierra, los clics pasan a lo que hay debajo
    flags: closing ? Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput : Qt.WindowStaysOnTopHint
    visible: false

    // al irse el foco a otra ventana: cerrar animando. Un menú abierto es otra
    // ventana: no cierra el panel al tomar el foco.
    onActiveChanged: {
        if (!active && visible && !menuOpen) {
            close();
        }
    }

    // --- datos ----------------------------------------------------------------

    function label(id) {
        switch (id) {
        case "utilities": return i18n("Utilities");
        case "developer": return i18n("Developer Tools");
        case "social": return i18n("Social Networking");
        case "productivity": return i18n("Productivity & Finance");
        case "entertainment": return i18n("Entertainment");
        case "creativity": return i18n("Creativity");
        case "reading": return i18n("Information & Reading");
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

    readonly property var chips: Categories.order.filter(c => (appsByCategory[c] || []).length > 0)

    // Secciones visibles, separadas por una línea fina: { id, items, bridge, offset }
    readonly property var sections: {
        const out = [];
        const q = query.trim();
        if (q.length > 0) {
            const items = searchResults.filter(entry => !filter || categoryOfId[entry.id] === filter);
            if (items.length > 0) {
                out.push({ id: "results", items: items });
            }
            out.push({ id: "bridge", items: [{ bridge: true, name: q }], bridge: true });
        } else if (filter) {
            out.push({ id: filter, items: appsByCategory[filter] || [] });
        } else {
            if (suggestions.length > 0) {
                out.push({ id: "recent", items: suggestions.slice(0, recentCount) });
            }
            out.push({ id: "all", items: allApps });
        }
        let offset = 0;
        for (const s of out) {
            s.offset = offset;
            offset += s.items.length;
        }
        return out;
    }
    readonly property int total: sections.length > 0 ? sections[sections.length - 1].offset + sections[sections.length - 1].items.length : 0

    onSectionsChanged: current = Math.min(current, Math.max(0, total - 1))
    onQueryChanged: current = 0
    onFilterChanged: {
        current = 0;
        scroll.jumpTo(0);
    }

    function entryAt(index) {
        for (const s of sections) {
            if (index >= s.offset && index < s.offset + s.items.length) {
                return s.items[index - s.offset];
            }
        }
        return null;
    }

    // Flechas sobre secciones de cuadrícula consecutivas (la del puente es de 1).
    function move(dx, dy) {
        if (total === 0) {
            return;
        }
        if (!showSelection) {
            keyboardUsed = true; // la primera flecha solo muestra la selección
            return;
        }
        if (dx !== 0) {
            current = Math.max(0, Math.min(total - 1, current + dx));
            return;
        }
        let si = sections.findIndex(s => current >= s.offset && current < s.offset + s.items.length);
        const s = sections[si];
        const cols = s.bridge ? 1 : columns;
        const pos = current - s.offset;
        const col = pos % cols;
        const lastRow = Math.floor((s.items.length - 1) / cols);
        if (dy > 0) {
            if (pos + cols < s.items.length) {
                current += cols;
            } else if (Math.floor(pos / cols) < lastRow) {
                current = s.offset + s.items.length - 1;
            } else if (si + 1 < sections.length) {
                const n = sections[si + 1];
                current = n.offset + Math.min(col, n.items.length - 1);
            }
        } else {
            if (pos - cols >= 0) {
                current -= cols;
            } else if (si > 0) {
                const p = sections[si - 1];
                const pcols = p.bridge ? 1 : columns;
                const start = Math.floor((p.items.length - 1) / pcols) * pcols;
                current = p.offset + Math.min(start + col, p.items.length - 1);
            }
        }
    }

    // Tab: etiqueta siguiente; tras la última, sin filtro
    function cycleFilter(step) {
        const ring = [""].concat(chips);
        const i = ring.indexOf(filter);
        filter = ring[(i + step + ring.length) % ring.length];
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

    // URL del .desktop de una entrada ("" si no es una app)
    function launcherUrl(entry) {
        if (!entry || entry.bridge) {
            return "";
        }
        if (String(entry.url || "").endsWith(".desktop")) {
            return String(entry.url);
        }
        const id = String(entry.id || "");
        if (id.startsWith("applications:")) {
            return id;
        }
        return id.endsWith(".desktop") ? "applications:" + id : "";
    }

    // Arrastrar una app. Lo lleva dragSource y no el delegado: la lista se
    // rehace y el delegado podría destruirse a medio arrastre (como Kickoff).
    // application/x-goldenglass-app: la Papelera del dock no la acepta.
    function performDrag(handler, entry, icon) {
        if (!handler.active) {
            dragSource.Drag.active = false;
            dragSource.Drag.imageSource = "";
            return;
        }
        const url = launcherUrl(entry);
        icon.grabToImage(result => {
            if (!handler.active) {
                return;
            }
            dragSource.Drag.imageSource = result.url;
            dragSource.Drag.hotSpot = Qt.point(icon.width / 2, icon.height / 2);
            dragSource.Drag.mimeData = {
                "text/uri-list": url,
                "application/x-goldenglass-app": url,
            };
            dragSource.Drag.active = true;
        });
    }

    function openSpotlight(text) {
        const quoted = "'" + text.replace(/'/g, "'\\''") + "'";
        executable.connectSource("dbus-send --session --type=method_call --dest=org.kde.krunner /App "
                                 + "org.kde.krunner.App.query string:" + quoted);
    }

    // --- abrir y cerrar -------------------------------------------------------

    function place() {
        const geo = Plasmoid.containment.screenGeometry;
        x = geo.x + Math.round((geo.width - tok.width) / 2) - shadowRoom;
        y = geo.y + Math.round((geo.height - tok.height) * 0.42) - shadowRoom; // algo por encima del centro, como Spotlight
    }

    function toggle() {
        if (visible && !closing) {
            close();
        } else {
            open();
        }
    }

    // también a medio cierre: vuelve a crecer desde donde iba
    function open() {
        closeAnimation.stop();
        closing = false;
        searchField.text = "";
        filter = "";
        current = 0;
        keyboardUsed = false;
        scroll.jumpTo(0);
        executable.connectSource(glassLevelCommand);
        place();
        visible = true;
        requestActivate();
        searchField.forceActiveFocus();
        glass.track(true);
        openAnimation.restart();
    }

    function close() {
        if (!visible || closing) {
            return;
        }
        contextMenu.close();
        moreMenu.close();
        closing = true;
        openAnimation.stop();
        closeAnimation.restart();
    }

    // --- interfaz -------------------------------------------------------------

    mainItem: FocusScope {
        width: panel.tok.width + panel.shadowRoom * 2
        height: panel.tok.height + panel.shadowRoom * 2
        // el panel que se desvanece ya no responde
        enabled: !panel.closing

        // (Dialog solo admite Items como hijos directos: lo demás va aquí)
        Item {
            id: dragSource
            Drag.dragType: Drag.Automatic
            // nunca Move: el destino podría borrar el .desktop
            Drag.supportedActions: Qt.CopyAction | Qt.LinkAction
            Drag.proposedAction: Qt.CopyAction
        }

        P5Support.DataSource {
            id: executable
            engine: "executable"
            connectedSources: []
            onNewData: (source, data) => {
                if (source === panel.glassLevelCommand && data["exit code"] === 0) {
                    const level = parseFloat(data["stdout"]);
                    if (!isNaN(level)) {
                        panel.glassLevel = level;
                    }
                }
                disconnectSource(source);
            }
        }

        ParallelAnimation {
            id: openAnimation
            NumberAnimation {
                target: card
                property: "opacity"
                to: 1
                duration: panel.tok.open_fade_ms
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: zoom
                properties: "xScale,yScale"
                to: 1
                duration: panel.tok.open_ms
                easing.type: Easing.OutBack
                easing.overshoot: panel.tok.open_overshoot
            }
        }

        ParallelAnimation {
            id: closeAnimation
            NumberAnimation {
                target: card
                property: "opacity"
                to: 0
                duration: panel.tok.close_ms
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: zoom
                properties: "xScale,yScale"
                to: panel.tok.close_scale
                duration: panel.tok.close_ms
                easing.type: Easing.InCubic
            }
            SequentialAnimation {
                // KWin no difumina a medias: el vidrio se quita cuando el panel
                // ya casi no se ve
                PauseAnimation {
                    duration: panel.tok.close_ms * panel.tok.close_unblur_at
                }
                ScriptAction {
                    script: glass.track(false)
                }
            }
            onFinished: {
                panel.visible = false;
                panel.closing = false;
                // la próxima vez crece desde aquí
                zoom.xScale = panel.tok.open_scale;
                zoom.yScale = panel.tok.open_scale;
            }
        }

        Keys.onEscapePressed: panel.close()

        // clic en el margen de la sombra: es fuera del panel
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onPressed: panel.close()
        }

        // Menús como QMenu (PlasmaExtras.Menu): un Menu de Qt Quick dentro de
        // la ventana del panel queda recortado por sus bordes y, como ventana
        // propia, sin blur de KWin detrás (vidrio ilegible). El QMenu es una
        // ventana emergente que dibuja el kstyle GoldenGlass, que sí pide el blur.
        PlasmaExtras.Menu {
            id: contextMenu
            property var entry: null
            property string url: ""

            function show(entry, item, x, y) {
                contextMenu.entry = entry;
                url = panel.launcherUrl(entry);
                // al pulsar, QAction cambia la marca sola: se rehace al abrir
                keepItem.checked = panel.dock !== null && url !== "" && panel.dock.isAppPinned(url);
                visualParent = item;
                open(x, y); // donde está el cursor, como en macOS
            }

            PlasmaExtras.MenuItem {
                text: i18n("Open")
                icon: "system-run"
                onClicked: panel.launch(contextMenu.entry)
            }
            PlasmaExtras.MenuItem {
                id: keepItem
                text: i18n("Keep in Dock")
                checkable: true
                visible: panel.dock !== null && contextMenu.url !== ""
                onClicked: {
                    if (panel.dock.isAppPinned(contextMenu.url)) {
                        panel.dock.unpinApp(contextMenu.url);
                    } else {
                        panel.dock.pinApp(contextMenu.url, -1);
                    }
                }
            }
            PlasmaExtras.MenuItem {
                separator: true
            }
        }
        // acciones de la app, tras «Abrir» y el separador
        Instantiator {
            model: contextMenu.entry ? contextMenu.entry.actions().filter(a => a.actionId && a.text) : []
            delegate: PlasmaExtras.MenuItem {
                required property var modelData
                text: modelData.text
                icon: typeof modelData.icon === "string" ? modelData.icon : ""
                onClicked: {
                    const e = contextMenu.entry;
                    e.model.trigger(e.row, modelData.actionId, modelData.actionArgument);
                    panel.close();
                }
            }
            onObjectAdded: (index, object) => contextMenu.addMenuItem(object)
            onObjectRemoved: (index, object) => contextMenu.removeMenuItem(object)
        }

        // El panel: vidrio, sombra y contenido. Crece y se desvanece entero.
        Item {
            id: card
            x: panel.shadowRoom
            y: panel.shadowRoom
            width: panel.tok.width
            height: panel.tok.height
            // cerrado: invisible y encogido, listo para crecer
            opacity: 0
            transform: Scale {
                id: zoom
                origin.x: card.width / 2
                origin.y: card.height / 2
                xScale: panel.tok.open_scale
                yScale: panel.tok.open_scale
            }

            RectangularShadow {
                anchors.fill: glassShape
                radius: glassShape.radius
                blur: panel.tok.shadow_blur
                offset: Qt.vector2d(0, panel.tok.shadow_offset)
                color: Qt.rgba(0, 0, 0, panel.tok.shadow_alpha)
            }

            Rectangle {
                id: glassShape
                // GlassRegion pide blur detrás de los elementos con esta propiedad a true
                property bool goldenGlassTile: true
                anchors.fill: parent
                radius: panel.tok.radius
                color: Qt.alpha(Kirigami.Theme.backgroundColor, panel.glassAlpha)
                border.width: 1
                border.color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.glass.border.alpha)
            }

            // los clics dentro del panel no lo cierran
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.AllButtons
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Buscador sin caja: glifo de Apps, texto grande y «⋯»
                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: panel.tok.header_height
                    Layout.leftMargin: panel.tok.margin
                    Layout.rightMargin: panel.tok.margin - Kirigami.Units.smallSpacing
                    spacing: Kirigami.Units.largeSpacing * 2

                    Kirigami.Icon {
                        Layout.preferredWidth: panel.tok.search_icon
                        Layout.preferredHeight: panel.tok.search_icon
                        source: "view-app-grid-symbolic"
                        isMask: true
                        color: Kirigami.Theme.textColor
                        opacity: 0.8
                    }

                    PlasmaComponents3.TextField {
                        id: searchField
                        Layout.fillWidth: true
                        leftPadding: 0
                        rightPadding: 0
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize * panel.tok.search_scale
                        placeholderText: i18n("Spotlight Search")
                        placeholderTextColor: Qt.alpha(Kirigami.Theme.textColor, 0.5)
                        background: Item {}
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
                            case Qt.Key_Enter:
                                if (panel.showSelection) {
                                    panel.launch(panel.entryAt(panel.current));
                                }
                                break;
                            case Qt.Key_Backspace:
                                if (text.length > 0 || !panel.filter) {
                                    return; // borrar texto
                                }
                                panel.filter = ""; // sin texto, borrar quita la etiqueta
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
                        id: moreButton
                        text: i18n("More")
                        // «⋯» horizontal, como macOS. Dibujado aquí: algunos temas
                        // (WhiteSur) traen view-more-horizontal en vertical.
                        contentItem: Item {
                            implicitWidth: Kirigami.Units.iconSizes.smallMedium
                            implicitHeight: Kirigami.Units.iconSizes.smallMedium
                            Row {
                                anchors.centerIn: parent
                                spacing: 3
                                Repeater {
                                    model: 3
                                    Rectangle {
                                        width: 4
                                        height: 4
                                        radius: 2
                                        color: Kirigami.Theme.textColor
                                        opacity: 0.8
                                    }
                                }
                            }
                        }
                        onClicked: {
                            // al pulsar, QAction cambia la marca sola: se rehace al abrir
                            gridItem.checked = !panel.listMode;
                            listItem.checked = panel.listMode;
                            moreMenu.openRelative();
                        }

                        PlasmaExtras.Menu {
                            id: moreMenu
                            visualParent: moreButton
                            placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup
                            PlasmaExtras.MenuItem {
                                id: gridItem
                                text: i18n("Show as Grid")
                                checkable: true
                                onClicked: Plasmoid.configuration.viewMode = "grid"
                            }
                            PlasmaExtras.MenuItem {
                                id: listItem
                                text: i18n("Show as List")
                                checkable: true
                                onClicked: Plasmoid.configuration.viewMode = "list"
                            }
                        }
                    }
                }

                Separator {
                    Layout.fillWidth: true
                    Layout.leftMargin: panel.tok.margin
                    Layout.rightMargin: panel.tok.margin
                }

                // Etiquetas de categoría sobre el contenido: al desplazarse, las
                // apps pasan por debajo y se difuminan (borde de Liquid Glass)
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    GlassScrollView {
                        id: scroll
                        anchors.fill: parent
                        topInset: chipBar.y + chipBar.height + Kirigami.Units.largeSpacing * 2
                        fadeStart: topInset - T.tokens.scroll.edge_fade

                        Column {
                            id: content
                            x: panel.tok.margin
                            width: scroll.width - panel.tok.margin * 2

                            Repeater {
                                model: panel.sections
                                delegate: Section {
                                    required property var modelData
                                    required property int index
                                    owner: panel
                                    section: modelData
                                    first: index === 0
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

                    // la fila llega hasta el borde derecho
                    ListView {
                        id: chipBar
                        y: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing
                        width: parent.width
                        height: panel.tok.chip_height
                        leftMargin: panel.tok.margin
                        rightMargin: panel.tok.margin
                        orientation: ListView.Horizontal
                        spacing: Kirigami.Units.largeSpacing
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: panel.chips
                        currentIndex: panel.chips.indexOf(panel.filter)
                        highlightFollowsCurrentItem: false
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0) {
                                positionViewAtIndex(currentIndex, ListView.Contain);
                            }
                        }

                        delegate: QQC2.AbstractButton {
                            id: chip
                            required property string modelData
                            readonly property bool selected: panel.filter === modelData
                            height: chipBar.height
                            leftPadding: panel.tok.chip_padding
                            rightPadding: panel.tok.chip_padding
                            focusPolicy: Qt.NoFocus
                            hoverEnabled: true
                            onClicked: panel.filter = selected ? "" : modelData

                            background: Rectangle {
                                radius: panel.tok.chip_radius
                                color: Qt.alpha(Kirigami.Theme.textColor,
                                                chip.selected ? panel.tok.chip_selected_alpha
                                                : chip.hovered ? panel.tok.chip_hover_alpha : panel.tok.chip_alpha)
                            }
                            contentItem: PlasmaComponents3.Label {
                                text: panel.label(chip.modelData)
                                verticalAlignment: Text.AlignVCenter
                                textFormat: Text.PlainText
                            }
                        }
                    }
                }
            }
        }

        // Vidrio detrás del panel (módulo org.goldenglass.glass de
        // goldenglass-kstyle). Sin él el panel se ve igual, sin difuminar.
        Loader {
            id: glass
            anchors.fill: parent
            source: Qt.resolvedUrl("GlassBlur.qml")
            onLoaded: {
                item.source = card;
                item.updateInterval = panel.tok.glass_update_ms;
            }

            // con false, KWin deja de difuminar
            function track(on) {
                if (item) {
                    item.active = on;
                }
            }
        }
    }

    // Desplaza la vista (animando) para que se vea `item` (el seleccionado).
    function ensureVisible(item) {
        scroll.ensureVisible(scroll.topInset + item.mapToItem(content, 0, 0).y, item.height);
    }

    function showContextMenu(entry, item, x, y) {
        contextMenu.show(entry, item, x, y);
    }

    // --- componentes ----------------------------------------------------------
    // Los componentes en línea no ven los id del documento: el panel se pasa
    // como «owner».

    // Línea fina, como las de macOS entre la cabecera, los recientes y el resto
    component Separator: Rectangle {
        implicitHeight: 1
        color: Qt.alpha(Kirigami.Theme.textColor, T.tokens.apps.separator_alpha)
    }

    component Section: Column {
        id: sectionItem
        property var owner
        property var section
        property bool first: false

        // separador entre secciones, sin título
        Item {
            visible: !sectionItem.first
            width: parent.width
            height: Kirigami.Units.largeSpacing * 2 + Kirigami.Units.smallSpacing
            Separator {
                width: parent.width
                y: Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing
            }
        }

        Grid {
            width: parent.width
            columns: sectionItem.section.bridge ? 1 : owner.columns

            Repeater {
                model: sectionItem.section.items
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

        height: row ? owner.tok.list_row_height : owner.tok.row_height
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton && !entry.bridge) {
                owner.showContextMenu(entry, item, mouse.x, mouse.y);
            } else {
                owner.launch(entry);
            }
        }
        onIsCurrentChanged: if (isCurrent && owner.showSelection) owner.ensureVisible(item)

        // arrastrar la app (al dock, al escritorio…); con el dedo, la vista se desplaza
        DragHandler {
            id: dragHandler
            target: null
            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad | PointerDevice.Stylus
            enabled: owner.launcherUrl(item.entry) !== ""
            onActiveChanged: owner.performDrag(dragHandler, item.entry, item.row ? listIcon : gridIcon)
        }

        // selección con el teclado (o el primer resultado al buscar)
        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: owner.tok.selected_radius
            visible: item.isCurrent && owner.showSelection
            color: Qt.alpha(Kirigami.Theme.textColor, owner.tok.selected_alpha)
        }

        // Cuadrícula: icono grande con el nombre debajo
        ColumnLayout {
            visible: !item.row
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: Kirigami.Units.smallSpacing
            width: parent.width - Kirigami.Units.smallSpacing * 2
            spacing: 0

            Kirigami.Icon {
                id: gridIcon
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: owner.tok.icon_size
                Layout.preferredHeight: owner.tok.icon_size
                source: item.entry.icon || ""
                // al pulsar se oscurece, como en Launchpad
                layer.enabled: item.pressed && item.containsMouse && !dragHandler.active
                layer.effect: MultiEffect {
                    brightness: T.tokens.apps.press_brightness
                }
            }
            PlasmaComponents3.Label {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: item.entry.name
                textFormat: Text.PlainText
                font.weight: Font.Medium
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
                id: listIcon
                Layout.preferredWidth: owner.tok.list_icon_size
                Layout.preferredHeight: owner.tok.list_icon_size
                source: item.entry.bridge ? "search" : (item.entry.icon || "")
                layer.enabled: item.pressed && item.containsMouse && !dragHandler.active
                layer.effect: MultiEffect {
                    brightness: T.tokens.apps.press_brightness
                }
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
