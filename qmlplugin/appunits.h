/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QQmlEngine>
#include <QSharedPointer>
#include <QStringList>
#include <QVariantList>

class AppUnitsBackend;

/*
    AppUnits: the apps that systemd --user runs right now, for the Dock's
    background apps (docs/ARCHITECTURE.md, «Apps en segundo plano»). Plasma
    starts every app in a unit named after its desktop file; libtaskmanager only
    knows about windows, so this is how the Dock learns that an app with no
    window is still running.

        AppUnits { id: units; ignored: Plasmoid.configuration.backgroundIgnore }
        Repeater { model: units.apps }   // {key, name, icon, agent}
        onClicked: units.stop(modelData.key)

    key is the desktop file id without ".desktop", like TasksModel's AppId.
    Only apps with a visible desktop entry are listed (Type=Application, not
    NoDisplay, not Hidden, not a TerminalEmulator, not in ignored). available is
    false without systemd on the session bus, and apps stays empty.
*/
class AppUnits : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(bool available READ available NOTIFY availableChanged)
    Q_PROPERTY(QVariantList apps READ apps NOTIFY appsChanged)
    Q_PROPERTY(QStringList ignored READ ignored WRITE setIgnored NOTIFY ignoredChanged)

public:
    explicit AppUnits(QObject *parent = nullptr);
    ~AppUnits() override;

    bool available() const;
    QVariantList apps() const;
    QStringList ignored() const;
    void setIgnored(const QStringList &ignored);

    // the units the app runs in
    Q_INVOKABLE QStringList units(const QString &key) const;
    // StopUnit on each of them: systemd sends SIGTERM to the whole cgroup
    Q_INVOKABLE void stop(const QString &key);
    // every unit of the app comes from XDG autostart: the user did not launch it
    Q_INVOKABLE bool isAgent(const QString &key) const;

Q_SIGNALS:
    void availableChanged();
    void appsChanged();
    void ignoredChanged();

private:
    void updateApps();

    QSharedPointer<AppUnitsBackend> m_backend;
    QStringList m_ignored;
    QVariantList m_apps;
};
