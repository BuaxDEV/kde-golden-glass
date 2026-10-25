/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QQmlEngine>
#include <QRect>
#include <QSharedPointer>
#include <QString>

class OsdInterceptor;

/*
    OsdHost: one screen's HUD of volume and brightness (one per Control
    Center). While any host lives, OsdInterceptor takes plasmashell's OSDs of
    volume, microphone, media player and brightness off Plasma and hands each
    one to a single host:

      - per-screen brightness, to the host whose screenRect is that screen;
      - anything else, to the host of the screen with the active window
        (activeScreen), else the primary screen's, else the first one.

    A suppressed host (its Control Center is open) shows nothing, and no other
    host does in its place.

        OsdHost {
            screenRect: Plasmoid.containment.screenGeometry
            activeScreen: tasks.activeTask.valid
            suppressed: panel.visible
            onProgressRequested: (icon, value, maximum) => hud.show(icon, value, maximum)
        }

    intercepting is false when Plasma's OSD stays (another Plasma, or no OSD
    service in this process): then nothing ever arrives.
*/
class OsdHost : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(QRect screenRect READ screenRect WRITE setScreenRect NOTIFY screenRectChanged)
    Q_PROPERTY(bool activeScreen READ isActiveScreen WRITE setActiveScreen NOTIFY activeScreenChanged)
    Q_PROPERTY(bool suppressed READ isSuppressed WRITE setSuppressed NOTIFY suppressedChanged)
    Q_PROPERTY(bool intercepting READ isIntercepting CONSTANT)

public:
    explicit OsdHost(QObject *parent = nullptr);
    ~OsdHost() override;

    QRect screenRect() const;
    void setScreenRect(const QRect &screenRect);
    bool isActiveScreen() const;
    void setActiveScreen(bool activeScreen);
    bool isSuppressed() const;
    void setSuppressed(bool suppressed);
    bool isIntercepting() const;

Q_SIGNALS:
    void screenRectChanged();
    void activeScreenChanged();
    void suppressedChanged();
    // icon is Plasma's icon name; value goes from 0 to maximum (100, or more for a raised volume)
    void progressRequested(const QString &icon, int value, int maximum);

private:
    QRect m_screenRect;
    bool m_activeScreen = false;
    bool m_suppressed = false;
    QSharedPointer<OsdInterceptor> m_interceptor;
};
