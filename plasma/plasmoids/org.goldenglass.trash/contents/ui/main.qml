/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Papelera del dock, como la de macOS. La de Plasma pide el icono simbólico
    dentro de un panel; esta usa el icono a color del tema (vacía o llena).

      clic                 abre la papelera en Dolphin
      soltar archivos      los mueve a la papelera (gio trash: estándar
                           freedesktop, la misma papelera que usa KDE)
      clic derecho         Abrir · Vaciar papelera… (pide confirmación)

    El contenido se vigila en ~/.local/share/Trash/files (la papelera de la
    carpeta personal).
*/

import QtCore
import QtQuick
import QtQuick.Controls as QQC2
import Qt.labs.folderlistmodel

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: root

    readonly property string trashUrl: StandardPaths.writableLocation(StandardPaths.GenericDataLocation) + "/Trash/files"
    // FolderListModel lista el directorio actual si la carpeta no existe: se
    // crea antes de vigilarla y solo se cuenta si de verdad es esa carpeta.
    property bool trashReady: false
    readonly property int count: trashReady && String(trashFiles.folder) === trashUrl ? trashFiles.count : 0
    readonly property bool hasContents: count > 0

    preferredRepresentation: fullRepresentation
    toolTipMainText: i18n("Trash")
    toolTipSubText: hasContents ? i18np("%1 item", "%1 items", count) : i18n("Empty")
    Plasmoid.icon: hasContents ? "user-trash-full" : "user-trash"
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    FolderListModel {
        id: trashFiles
        folder: root.trashReady ? root.trashUrl : ""
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
            if (source === root.mkdirCommand) {
                root.trashReady = true;
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

    fullRepresentation: MouseArea {
        id: area
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton) {
                menu.popup();
            } else {
                root.open();
            }
        }

        Kirigami.Icon {
            anchors.fill: parent
            source: Plasmoid.icon
            active: area.containsMouse || drop.containsDrag
        }

        DropArea {
            id: drop
            anchors.fill: parent
            onDropped: event => {
                if (event.hasUrls) {
                    root.trash(event.urls);
                    event.acceptProposedAction();
                }
            }
        }

        PlasmaComponents3.Menu {
            id: menu
            popupType: QQC2.Popup.Window

            PlasmaComponents3.MenuItem {
                text: i18n("Open")
                icon.name: "document-open-folder"
                onTriggered: root.open()
            }
            PlasmaComponents3.MenuItem {
                text: i18n("Empty Trash…")
                icon.name: "trash-empty"
                enabled: root.hasContents
                onTriggered: root.emptyTrash()
            }
        }
    }
}
