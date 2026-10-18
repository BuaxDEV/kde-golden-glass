/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later

    Sonido en detalle, como en macOS 26: volumen y salidas; un clic en una
    salida la hace la predeterminada.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.private.volume as Volume

DetailView {
    id: view

    readonly property var sink: Volume.PreferredDevice.sink

    signal settingsRequested()

    title: i18n("Sound")
    footerText: i18n("Sound Settings…")
    onFooterClicked: settingsRequested()

    SliderRow {
        id: volumeRow
        Layout.fillWidth: true
        Layout.leftMargin: Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        iconFrom: view.sink && (view.sink.muted || view.sink.volume === 0) ? "audio-volume-muted-symbolic" : "audio-volume-low-symbolic"
        iconTo: "audio-volume-high-symbolic"
        iconClickable: true
        from: Volume.PulseAudio.MinimalVolume
        to: Volume.PulseAudio.NormalVolume
        onMoved: {
            view.sink.muted = false;
            view.sink.volume = Math.round(value);
        }
        onIconClicked: view.sink.muted = !view.sink.muted

        Binding on value {
            value: view.sink ? view.sink.volume : 0
            when: !volumeRow.pressed
        }
    }

    SectionLabel {
        text: i18n("Output")
    }
    Repeater {
        model: Volume.SinkModel {}
        delegate: DetailRow {
            required property var model
            // la salida «nula» de PipeWire no es un dispositivo
            visible: model.Name !== "auto_null"
            text: model.Description
            iconName: model.FormFactor === "headset" || model.FormFactor === "headphone" ? "audio-headset-symbolic"
                    : model.IconName && model.IconName.length > 0 ? model.IconName + "-symbolic"
                    : "audio-speakers-symbolic"
            active: model.PulseObject === view.sink
            onClicked: model.PulseObject.default = true
        }
    }
}
