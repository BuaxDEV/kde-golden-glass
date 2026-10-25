/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Tema de SDDM de GoldenGlass: como la pantalla de bloqueo (y el login de
    macOS 26/27). Fondo difuminado de día o de noche según la hora, fecha y
    hora grandes arriba, avatar, nombre y contraseña abajo; con varios
    usuarios, primero una fila de avatares. Reposo, Reiniciar y Apagar abajo;
    sesión y distribución de teclado discretas en las esquinas.

    Los valores (medidas a 1080 líneas, colores, fondo) vienen de theme.conf,
    que genera tools/login.py desde [login] de los tokens. Los textos son los
    de SddmComponents (TextConstants), que SDDM ya trae traducidos.
*/

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import SddmComponents 2.0 as Sddm

Rectangle {
    id: root

    width: 1920
    height: 1080
    color: "#101014"

    // --- valores del tema ------------------------------------------------------

    QtObject {
        id: st
        readonly property real scale: root.height / 1080
        readonly property string font: config.font
        readonly property color text: config.text
        readonly property real textAlpha: Number(config.textAlpha)
        readonly property color glass: withAlpha(config.glass, Number(config.glassAlpha))
        readonly property color glassBorder: withAlpha(config.glass, Number(config.glassBorderAlpha))
        readonly property color error: config.error

        function px(value) {
            return Math.round(Number(value) * scale);
        }

        function withAlpha(color, alpha) {
            const c = Qt.darker(color, 1.0); // texto → color
            return Qt.rgba(c.r, c.g, c.b, alpha);
        }
    }

    Sddm.TextConstants {
        id: tc
    }

    property date now: new Date()

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    readonly property bool night: {
        const hour = now.getHours();
        return hour >= Number(config.nightStart) || hour < Number(config.dayStart);
    }

    // --- fondo -------------------------------------------------------------------

    Image {
        id: wallpaper
        anchors.fill: parent
        visible: false
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        source: "file://" + config.wallpaperDir + (root.night ? "/images_dark/" : "/images/")
            + (root.width / root.height > 1.7 ? config.wallpaperWide : config.wallpaperTall)
        sourceSize.width: root.width
        sourceSize.height: root.height
    }

    MultiEffect {
        anchors.fill: parent
        source: wallpaper
        visible: wallpaper.status === Image.Ready
        autoPaddingEnabled: false
        blurEnabled: true
        blur: 1.0
        blurMax: Number(config.blur)
        saturation: 0.15
    }

    Rectangle {
        anchors.fill: parent
        color: "black"
        opacity: Number(config.dim)
    }

    // --- componentes -----------------------------------------------------------

    // Texto claro del tema (sobre vidrio oscuro o el fondo difuminado). Texto
    // plano: muestra nombres de usuario (GECOS), que cada usuario puede cambiar.
    component GlassLabel: Text {
        textFormat: Text.PlainText
        color: st.text
        opacity: st.textAlpha
        font.family: st.font
        renderType: Text.QtRendering
    }

    // Avatar redondo; sin imagen, silueta sobre vidrio.
    component Avatar: Item {
        id: avatar
        property string source
        property real size
        width: size
        height: size

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: st.glass
        }
        Image {
            id: photo
            anchors.fill: parent
            visible: false
            // SDDM da un URI file://; su silueta genérica (…/faces/.face.icon)
            // se sustituye por la nuestra de vidrio
            source: avatar.source.length > 0 && !avatar.source.endsWith("/faces/.face.icon")
                ? (avatar.source.startsWith("file://") ? avatar.source : "file://" + avatar.source) : ""
            sourceSize.width: avatar.size * 2
            sourceSize.height: avatar.size * 2
            fillMode: Image.PreserveAspectCrop
            smooth: true
        }
        Rectangle {
            id: circle
            anchors.fill: parent
            radius: width / 2
            visible: false
            layer.enabled: true
        }
        MultiEffect {
            anchors.fill: parent
            source: photo
            visible: photo.status === Image.Ready
            maskEnabled: true
            maskSource: circle
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }
        Image {
            anchors.centerIn: parent
            visible: photo.status !== Image.Ready
            width: avatar.size * 0.62
            height: width
            source: "icons/user.svg"
            sourceSize.width: width * 2
            sourceSize.height: height * 2
            opacity: 0.85
        }
        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: "transparent"
            border.width: Math.max(1, st.px(1.5))
            border.color: st.glassBorder
        }
    }

    // Botón de vidrio redondo con icono y texto debajo (Reposo, Reiniciar…).
    component ActionButton: Item {
        id: action
        property string icon
        property string label
        // nombre para el lector de pantalla (el botón de volver no lleva texto)
        property string accessibleName: label
        signal clicked
        width: Math.max(circleButton.width, caption.implicitWidth) + st.px(16)
        height: circleButton.height + st.px(8) + caption.implicitHeight
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: accessibleName
        Accessible.onPressAction: action.clicked()

        Rectangle {
            id: circleButton
            anchors.horizontalCenter: parent.horizontalCenter
            width: st.px(Number(config.actionSize) * 1.6)
            height: width
            radius: width / 2
            color: mouse.pressed ? st.glassBorder : (mouse.containsMouse || action.activeFocus ? st.glass : "transparent")
            border.width: action.activeFocus ? Math.max(1, st.px(1.5)) : 0
            border.color: st.glassBorder

            Image {
                anchors.centerIn: parent
                width: st.px(config.actionSize)
                height: width
                source: action.icon
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                opacity: st.textAlpha
            }
        }
        GlassLabel {
            id: caption
            anchors.top: circleButton.bottom
            anchors.topMargin: st.px(8)
            anchors.horizontalCenter: parent.horizontalCenter
            text: action.label
            font.pixelSize: st.px(14)
        }
        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: action.clicked()
        }
        Keys.onReturnPressed: action.clicked()
        Keys.onSpacePressed: action.clicked()
    }

    // Botón pequeño de vidrio con icono y texto (sesión, teclado).
    component CornerButton: Rectangle {
        id: corner
        property string icon
        property string label
        signal clicked
        height: st.px(30)
        width: row.implicitWidth + st.px(24)
        radius: height / 2
        color: cornerMouse.containsMouse || activeFocus ? st.glass : "transparent"
        border.width: activeFocus ? Math.max(1, st.px(1.5)) : 0
        border.color: st.glassBorder
        activeFocusOnTab: true
        Accessible.role: Accessible.Button
        Accessible.name: label

        Row {
            id: row
            anchors.centerIn: parent
            spacing: st.px(8)
            Image {
                anchors.verticalCenter: parent.verticalCenter
                width: st.px(18)
                height: width
                source: corner.icon
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                opacity: st.textAlpha
            }
            GlassLabel {
                anchors.verticalCenter: parent.verticalCenter
                text: corner.label
                font.pixelSize: st.px(14)
            }
        }
        MouseArea {
            id: cornerMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: corner.clicked()
        }
        Keys.onReturnPressed: corner.clicked()
        Keys.onSpacePressed: corner.clicked()
    }

    // --- reloj -------------------------------------------------------------------

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: st.px(config.clockTop)
        spacing: 0

        GlassLabel {
            anchors.horizontalCenter: parent.horizontalCenter
            text: {
                const date = Qt.locale().toString(root.now, "dddd d MMMM");
                return date.charAt(0).toUpperCase() + date.slice(1);
            }
            font.pixelSize: st.px(config.dateSize)
            font.weight: Font.DemiBold
        }
        GlassLabel {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Qt.locale().toString(root.now, Qt.locale().timeFormat(Locale.ShortFormat).replace(/\s*[aApP]+$/, ""))
            font.pixelSize: st.px(config.clockSize)
            font.weight: Font.Bold
        }
    }

    // --- usuarios ------------------------------------------------------------------

    // Con varios usuarios se elige primero en la fila (como macOS); con uno,
    // se va directo a la contraseña.
    property bool picking: userModel.count > 1
    property int userIndex: Math.max(0, userModel.lastIndex)
    property int sessionIndex: Math.max(0, sessionModel.lastIndex)

    // Datos del usuario elegido (los roles del modelo solo existen en los delegados).
    Repeater {
        id: userData
        model: userModel
        delegate: Item {
            required property int index
            required property string name
            required property string realName
            required property string icon
            readonly property string displayName: realName.length > 0 ? realName : name
        }
    }
    readonly property Item currentUser: userData.count > 0 ? userData.itemAt(userIndex) : null

    property bool failed: false

    function choose(index) {
        userIndex = index;
        picking = false;
        password.text = "";
        failed = false;
        Qt.callLater(() => password.forceActiveFocus());
    }

    function login() {
        if (!currentUser) {
            return;
        }
        failed = false;
        sddm.login(currentUser.name, password.text, sessionIndex);
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            password.text = "";
            root.failed = true;
            shake.restart();
            password.forceActiveFocus();
        }
    }

    // Fila de avatares
    Row {
        id: userRow
        visible: root.picking && primaryScreen
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: actions.top
        anchors.bottomMargin: st.px(96)
        spacing: st.px(36)

        Repeater {
            id: userEntries
            model: userModel
            delegate: Item {
                id: entry
                required property int index
                required property string name
                required property string realName
                required property string icon
                width: Math.max(st.px(config.avatarSmall) + st.px(24), entryName.implicitWidth)
                height: entryAvatar.height + st.px(10) + entryName.implicitHeight
                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: entryName.text

                Avatar {
                    id: entryAvatar
                    anchors.horizontalCenter: parent.horizontalCenter
                    size: st.px(config.avatarSmall)
                    source: entry.icon
                    scale: entryMouse.containsMouse || entry.activeFocus ? 1.08 : 1
                    Behavior on scale {
                        NumberAnimation {
                            duration: 120
                        }
                    }
                }
                GlassLabel {
                    id: entryName
                    anchors.top: entryAvatar.bottom
                    anchors.topMargin: st.px(10)
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: entry.realName.length > 0 ? entry.realName : entry.name
                    font.pixelSize: st.px(15)
                }
                MouseArea {
                    id: entryMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.choose(entry.index)
                }
                Keys.onReturnPressed: root.choose(entry.index)
                Keys.onSpacePressed: root.choose(entry.index)
            }
        }
    }

    // Usuario elegido: avatar, nombre y contraseña
    Column {
        id: loginBox
        visible: !root.picking && primaryScreen && root.currentUser !== null
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: actions.top
        anchors.bottomMargin: st.px(72)
        spacing: st.px(14)

        Avatar {
            anchors.horizontalCenter: parent.horizontalCenter
            size: st.px(config.avatarSize)
            source: root.currentUser ? root.currentUser.icon : ""
        }
        GlassLabel {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.currentUser ? root.currentUser.displayName : ""
            font.pixelSize: st.px(config.nameSize)
            font.weight: Font.DemiBold
        }

        Item {
            id: fieldRow
            anchors.horizontalCenter: parent.horizontalCenter
            width: st.px(config.fieldWidth)
            height: st.px(config.fieldHeight)

            TextField {
                id: password
                anchors.fill: parent
                echoMode: TextInput.Password
                passwordCharacter: "●"
                placeholderText: tc.password
                placeholderTextColor: st.withAlpha(st.text, 0.55)
                color: st.text
                font.family: st.font
                font.pixelSize: st.px(15)
                font.letterSpacing: echoMode === TextInput.Password && text.length > 0 ? st.px(2) : 0
                leftPadding: st.px(14)
                rightPadding: height
                verticalAlignment: TextInput.AlignVCenter
                selectByMouse: true
                focus: !root.picking
                Accessible.name: tc.password
                background: Rectangle {
                    radius: height / 2
                    color: st.glass
                    border.width: Math.max(1, st.px(1))
                    border.color: password.activeFocus ? st.withAlpha(st.text, 0.5) : st.glassBorder
                }
                onAccepted: root.login()
                onTextEdited: root.failed = false
                Keys.onEscapePressed: {
                    if (userModel.count > 1) {
                        root.picking = true;
                    } else {
                        text = "";
                    }
                }
            }

            // Bloq Mayús o, con texto, la flecha para entrar (dentro del campo)
            Image {
                anchors.right: parent.right
                anchors.rightMargin: (parent.height - width) / 2
                anchors.verticalCenter: parent.verticalCenter
                width: parent.height * 0.62
                height: width
                visible: password.text.length > 0 || keyboard.capsLock
                source: password.text.length > 0 ? "icons/arrow.svg" : "icons/capslock.svg"
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                opacity: st.textAlpha
                MouseArea {
                    anchors.fill: parent
                    enabled: password.text.length > 0
                    onClicked: root.login()
                }
            }

            SequentialAnimation {
                id: shake
                property real d: st.px(10)
                NumberAnimation { target: fieldRow; property: "anchors.horizontalCenterOffset"; to: -shake.d; duration: 50 }
                NumberAnimation { target: fieldRow; property: "anchors.horizontalCenterOffset"; to: shake.d; duration: 70 }
                NumberAnimation { target: fieldRow; property: "anchors.horizontalCenterOffset"; to: -shake.d * 0.6; duration: 70 }
                NumberAnimation { target: fieldRow; property: "anchors.horizontalCenterOffset"; to: shake.d * 0.3; duration: 60 }
                NumberAnimation { target: fieldRow; property: "anchors.horizontalCenterOffset"; to: 0; duration: 50 }
            }
        }

        GlassLabel {
            id: message
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.failed ? tc.loginFailed : (keyboard.capsLock ? tc.capslockWarning : "")
            color: root.failed ? st.error : st.text
            font.pixelSize: st.px(14)
            height: st.px(18)
        }
    }

    // Volver a la fila de usuarios
    ActionButton {
        visible: !root.picking && userModel.count > 1 && primaryScreen
        anchors.right: loginBox.left
        anchors.rightMargin: st.px(48)
        anchors.verticalCenter: loginBox.verticalCenter
        icon: "icons/back.svg"
        label: ""
        accessibleName: qsTr("Back")
        onClicked: root.picking = true
    }

    // --- acciones ------------------------------------------------------------------

    Row {
        id: actions
        visible: primaryScreen
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: st.px(config.bottomMargin)
        spacing: st.px(28)

        ActionButton {
            visible: sddm.canSuspend
            icon: "icons/sleep.svg"
            label: tc.suspend
            onClicked: sddm.suspend()
        }
        ActionButton {
            visible: sddm.canReboot
            icon: "icons/restart.svg"
            label: tc.reboot
            onClicked: sddm.reboot()
        }
        ActionButton {
            visible: sddm.canPowerOff
            icon: "icons/shutdown.svg"
            label: tc.shutdown
            onClicked: sddm.powerOff()
        }
    }

    // Sesión (abajo a la izquierda) y teclado (abajo a la derecha)
    CornerButton {
        id: sessionButton
        visible: primaryScreen && sessionModel.count > 1
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: st.px(24)
        icon: "icons/session.svg"
        label: sessionNames.count > 0 && sessionNames.itemAt(root.sessionIndex) ? sessionNames.itemAt(root.sessionIndex).text : tc.session
        onClicked: sessionMenu.open()

        Repeater {
            id: sessionNames
            model: sessionModel
            delegate: Item {
                required property string name
                property string text: name
            }
        }

        Menu {
            id: sessionMenu
            y: -height - st.px(8)
            Repeater {
                model: sessionModel
                delegate: MenuItem {
                    required property int index
                    required property string name
                    text: name
                    checkable: true
                    checked: index === root.sessionIndex
                    onTriggered: root.sessionIndex = index
                }
            }
        }
    }

    CornerButton {
        visible: primaryScreen && keyboard.layouts.length > 1
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: st.px(24)
        icon: "icons/keyboard.svg"
        label: keyboard.layouts.length > 0 ? keyboard.layouts[keyboard.currentLayout].shortName.toUpperCase() : ""
        onClicked: keyboard.currentLayout = (keyboard.currentLayout + 1) % keyboard.layouts.length
    }

    Component.onCompleted: {
        if (!picking) {
            Qt.callLater(() => password.forceActiveFocus());
        } else {
            Qt.callLater(() => {
                const entry = userEntries.itemAt(Math.max(0, userModel.lastIndex));
                if (entry) {
                    entry.forceActiveFocus();
                }
            });
        }
    }
}
