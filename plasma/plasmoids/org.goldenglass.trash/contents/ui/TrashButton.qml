/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Papelera como la de macOS, con el icono a color del tema (vacía o llena):

      clic                 abre la papelera en Dolphin
      soltar archivos      los mueve a la papelera (gio trash: estándar
                           freedesktop, la misma papelera que usa KDE)
      clic derecho         Abrir · Vaciar papelera… (pide confirmación)

    El contenido se vigila en ~/.local/share/Trash/files (la papelera de la
    carpeta personal). La usan el plasmoid Papelera (org.goldenglass.trash) y
    el dock (org.goldenglass.dock), que la copia al generarse.
*/

import QtCore
import QtQuick
import Qt.labs.folderlistmodel

import org.kde.kirigami as Kirigami
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as P5Support

MouseArea {
    id: button

    readonly property string trashUrl: StandardPaths.writableLocation(StandardPaths.GenericDataLocation) + "/Trash/files"
    // FolderListModel lista el directorio actual si la carpeta no existe: se
    // crea antes de vigilarla y solo se cuenta si de verdad es esa carpeta.
    property bool trashReady: false
    readonly property int count: trashReady && String(trashFiles.folder) === trashUrl ? trashFiles.count : 0
    readonly property bool hasContents: count > 0
    readonly property string iconName: hasContents ? "user-trash-full" : "user-trash"
    readonly property bool dropping: drop.containsDrag
    // el dock dibuja el icono él mismo (ampliación): puede ocultar este
    property bool showIcon: true

    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: mouse => {
        if (mouse.button === Qt.RightButton) {
            menu.open(mouse.x, mouse.y);
        } else {
            open();
        }
    }

    FolderListModel {
        id: trashFiles
        folder: button.trashReady ? button.trashUrl : ""
        showDirs: true
        showDotAndDotDot: false
        showHidden: true
        showOnlyReadable: false
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: source => {
            if (source === button.mkdirCommand) {
                button.trashReady = true;
            }
            disconnectSource(source);
        }
    }

    readonly property string mkdirCommand: "mkdir -p " + shellQuote(decodeURIComponent(trashUrl.slice("file://".length)))
    Component.onCompleted: executable.connectSource(mkdirCommand)

    function shellQuote(text) {
        return "'" + String(text).replace(/'/g, "'\\''") + "'";
    }

    function open() {
        Qt.openUrlExternally("trash:/");
    }

    function trash(urls) {
        const paths = urls.filter(u => String(u).startsWith("file://"))
                          .map(u => shellQuote(decodeURIComponent(String(u).slice("file://".length))));
        if (paths.length > 0) {
            executable.connectSource("gio trash -- " + paths.join(" "));
        }
    }

    function emptyTrash() {
        executable.connectSource("kdialog --title " + shellQuote(i18n("Trash"))
            + " --warningcontinuecancel " + shellQuote(i18n("Are you sure you want to permanently erase the items in the Trash?"))
            + " --continue-label " + shellQuote(i18n("Empty Trash"))
            + " && ktrash6 --empty");
    }

    Kirigami.Icon {
        anchors.fill: parent
        visible: button.showIcon
        source: button.iconName
        active: button.containsMouse || drop.containsDrag
    }

    DropArea {
        id: drop
        anchors.fill: parent
        onDropped: event => {
            if (event.hasUrls) {
                button.trash(event.urls);
                event.acceptProposedAction();
            }
        }
    }

    // QMenu (PlasmaExtras.Menu) y no un Menu de Qt Quick: como ventana propia,
    // el de Qt Quick no tiene blur de KWin detrás y su vidrio es ilegible; el
    // QMenu lo dibuja el kstyle GoldenGlass, que sí lo pide.
    PlasmaExtras.Menu {
        id: menu
        visualParent: button

        PlasmaExtras.MenuItem {
            text: i18n("Open")
            icon: "document-open-folder"
            onClicked: button.open()
        }
        PlasmaExtras.MenuItem {
            text: i18n("Empty Trash…")
            icon: "trash-empty"
            enabled: button.hasContents
            onClicked: button.emptyTrash()
        }
    }
}
