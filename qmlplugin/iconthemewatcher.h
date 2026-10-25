/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QQmlEngine>

class QTimer;

/*
    IconThemeWatcher: counts the icon theme changes this process sees, for the
    Dock and the Apps panel. A Kirigami.Icon that already painted an icon keeps
    it when the theme changes (it reloads only on a palette change or a new
    source), so they set their source again whenever revision grows:

        IconThemeWatcher { id: iconTheme }
        Connections { target: iconTheme; function onRevisionChanged() { reload() } }

    revision grows once KIconLoader of this process has loaded the new theme
    (its iconChanged signal, which plasma-changeicons triggers for every icon
    group): a source set again then finds the icon of the new theme. The signals
    of one switch count once.
*/
class IconThemeWatcher : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(int revision READ revision NOTIFY revisionChanged)

public:
    explicit IconThemeWatcher(QObject *parent = nullptr);

    int revision() const;

Q_SIGNALS:
    void revisionChanged();

private:
    QTimer *m_settle;
    int m_revision = 0;
};
