/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <KConfigWatcher>
#include <QObject>
#include <QQmlEngine>

/*
    MenuBarSettings: ajustes de la barra de menús para el Panel.qml del shell.
    Lee goldenglassrc [Plasma] MenubarBackground (de fábrica, el token
    plasma.menubar_background) y lo sigue en vivo: el módulo «Vidrio» y
    goldenglass-glass lo escriben con aviso de cambio. inactiveOpacity es el
    token plasma.menubar_inactive_opacity.

        MenuBarSettings { id: settings }
        visible: settings.background
*/
class MenuBarSettings : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(bool background READ background NOTIFY backgroundChanged)
    Q_PROPERTY(double inactiveOpacity READ inactiveOpacity CONSTANT)

public:
    explicit MenuBarSettings(QObject *parent = nullptr);

    bool background() const;
    double inactiveOpacity() const;

Q_SIGNALS:
    void backgroundChanged();

private:
    void load();

    KConfigWatcher::Ptr m_watcher;
    bool m_background;
};
