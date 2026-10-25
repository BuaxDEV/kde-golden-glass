/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QDBusConnection>
#include <QList>
#include <QLoggingCategory>
#include <QObject>
#include <QPointer>
#include <QRect>
#include <QSharedPointer>
#include <QString>

Q_DECLARE_LOGGING_CATEGORY(lcOsd)

class OsdHost;
class OsdService;

/*
    OsdInterceptor: the volume and brightness OSDs of plasmashell go to the
    GoldenGlass HUD under the menu bar (docs/ARCHITECTURE.md, «HUD de volumen
    y brillo»). Plasma shows them from its own Osd object at
    /org/kde/osdService, and turning it off ([OSD] Enabled=false) also mutes
    the osdProgress and osdText signals the lock screen shows; so, inside
    plasmashell, its object is swapped for an OsdService with the same
    interface:

      - volume, microphone, media player, brightness (also per screen) and
        keyboard brightness go to one OsdHost as progressRequested, and to the
        lock screen as the same osdProgress and osdText that Plasma emits;
      - everything else (the text OSDs, hide) goes on to Plasma's object, and
        its signals reach the bus through OsdService.

    One interceptor per process, shared by every OsdHost: it takes over when
    the first host is created and gives /org/kde/osdService back to Plasma's
    object when the last one goes. If that object does not export exactly
    OsdService's signatures (another Plasma), it does nothing and Plasma's OSD
    stays.
*/
class OsdInterceptor : public QObject
{
    Q_OBJECT

public:
    static QSharedPointer<OsdInterceptor> shared();
    ~OsdInterceptor() override;

    bool isIntercepting() const;

    void addHost(OsdHost *host);
    void removeHost(OsdHost *host);

    // the public slots and signals of OsdService, its D-Bus interface name included
    static bool exportsOsdServiceInterface(const QMetaObject *metaObject);

    // the OSDs the HUD shows, called by OsdService
    void brightness(int percent);
    void screenBrightness(int percent, const QString &displayId, const QString &displayLabel, const QRect &screenRect);
    void keyboardBrightness(int percent);
    void volume(int percent, int maximumPercent);
    void microphoneVolume(int percent);
    void mediaPlayerVolume(int percent, const QString &playerName, const QString &playerIconName);

    // the rest goes on to Plasma's Osd, with its own arguments
    template<typename... Args>
    void forward(const char *method, const Args &...arguments)
    {
        if (m_original && !QMetaObject::invokeMethod(m_original, method, Qt::DirectConnection, arguments...)) {
            qCWarning(lcOsd) << "could not forward" << method << "to Plasma's OSD";
        }
    }

private:
    OsdInterceptor();

    void install();
    void restore();
    bool osdEnabled() const;

    // the host on whose screen the OSD shows
    OsdHost *hostFor(const QRect &screenRect = {}, const QString &displayId = {}) const;
    OsdHost *hostOnScreen(const QRect &screenRect) const;

    void showProgress(OsdHost *host, const QString &icon, int percent, int maximumPercent, const QString &additionalText = {});
    // Plasma shows a text OSD for a mute; the HUD shows the empty bar
    void showMuted(OsdHost *host, const QString &icon, int maximumPercent, const QString &text);

    QDBusConnection m_bus;
    OsdService *m_service;
    QPointer<QObject> m_original;
    QList<OsdHost *> m_hosts;
};
