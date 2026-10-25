/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "osdinterceptor.h"

#include "osdhost.h"
#include "osdservice.h"

#include <KConfigGroup>
#include <KLocalizedString>
#include <KSharedConfig>

#include <QDBusError>
#include <QGuiApplication>
#include <QMetaMethod>
#include <QScreen>
#include <QStringList>

#include <algorithm>

Q_LOGGING_CATEGORY(lcOsd, "org.goldenglass.osd", QtWarningMsg)

namespace
{
const QString osdPath = QStringLiteral("/org/kde/osdService");
// how plasmashell registers its Osd (shell/osd.cpp)
constexpr QDBusConnection::RegisterOptions osdExport = QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals;
constexpr int fullPercent = 100;
// the texts Plasma shows the lock screen for a mute come from its own catalog
constexpr const char *plasmaDomain = "plasmashell";

// D-Bus interface, then every public slot and signal QtDBus exports
QStringList exportedInterface(const QMetaObject *metaObject)
{
    QStringList exported;
    const int interfaceInfo = metaObject->indexOfClassInfo("D-Bus Interface");
    exported << QString::fromLatin1(interfaceInfo >= 0 ? metaObject->classInfo(interfaceInfo).value() : "");
    for (int i = QObject::staticMetaObject.methodCount(); i < metaObject->methodCount(); ++i) {
        const QMetaMethod method = metaObject->method(i);
        const bool slot = method.methodType() == QMetaMethod::Slot;
        if (method.access() != QMetaMethod::Public || (!slot && method.methodType() != QMetaMethod::Signal)) {
            continue;
        }
        exported << QStringLiteral("%1 %2 %3").arg(slot ? u"slot" : u"signal", QLatin1String(method.typeName()), QLatin1String(method.methodSignature()));
    }
    return exported;
}

// Plasma's icons (shell/osd.cpp), which the lock screen shows too
QString volumeIcon(int percent)
{
    if (percent <= 0) {
        return QStringLiteral("audio-volume-muted");
    }
    if (percent <= 25) {
        return QStringLiteral("audio-volume-low");
    }
    if (percent <= 75) {
        return QStringLiteral("audio-volume-medium");
    }
    if (percent <= 100) {
        return QStringLiteral("audio-volume-high");
    }
    if (percent <= 125) {
        return QStringLiteral("audio-volume-high-warning");
    }
    return QStringLiteral("audio-volume-high-danger");
}

QString microphoneIcon(int percent)
{
    if (percent <= 0) {
        return QStringLiteral("microphone-sensitivity-muted");
    }
    if (percent <= 25) {
        return QStringLiteral("microphone-sensitivity-low");
    }
    if (percent <= 75) {
        return QStringLiteral("microphone-sensitivity-medium");
    }
    return QStringLiteral("microphone-sensitivity-high");
}

const QString brightnessIcon = QStringLiteral("video-display-brightness");
const QString keyboardBrightnessIcon = QStringLiteral("input-keyboard-brightness");
} // namespace

QSharedPointer<OsdInterceptor> OsdInterceptor::shared()
{
    static QWeakPointer<OsdInterceptor> instance;
    QSharedPointer<OsdInterceptor> interceptor = instance.toStrongRef();
    if (!interceptor) {
        interceptor.reset(new OsdInterceptor);
        instance = interceptor;
    }
    return interceptor;
}

OsdInterceptor::OsdInterceptor()
    : m_bus(QDBusConnection::sessionBus())
    , m_service(new OsdService(this))
{
    install();
}

OsdInterceptor::~OsdInterceptor()
{
    restore();
}

bool OsdInterceptor::isIntercepting() const
{
    return !m_original.isNull();
}

void OsdInterceptor::addHost(OsdHost *host)
{
    m_hosts.append(host);
}

void OsdInterceptor::removeHost(OsdHost *host)
{
    m_hosts.removeAll(host);
}

bool OsdInterceptor::exportsOsdServiceInterface(const QMetaObject *metaObject)
{
    return exportedInterface(metaObject) == exportedInterface(&OsdService::staticMetaObject);
}

void OsdInterceptor::install()
{
    QObject *original = m_bus.objectRegisteredAt(osdPath);
    if (!original) {
        qCInfo(lcOsd) << "no OSD service at" << osdPath << "in this process: Plasma's OSD stays";
        return;
    }
    if (!exportsOsdServiceInterface(original->metaObject())) {
        qCWarning(lcOsd) << original->metaObject()->className() << "at" << osdPath
                         << "does not export the osdService signatures GoldenGlass knows: Plasma's OSD stays";
        return;
    }
    m_bus.unregisterObject(osdPath);
    if (!m_bus.registerObject(osdPath, m_service, osdExport)) {
        qCWarning(lcOsd) << "could not register the HUD's OSD service:" << m_bus.lastError().message();
        m_bus.registerObject(osdPath, original, osdExport);
        return;
    }
    m_original = original;
    // once unregistered, the original's signals no longer reach the bus by themselves
    connect(original, SIGNAL(osdProgress(QString, int, int, QString)), m_service, SIGNAL(osdProgress(QString, int, int, QString)));
    connect(original, SIGNAL(osdText(QString, QString)), m_service, SIGNAL(osdText(QString, QString)));
    qCDebug(lcOsd) << "volume and brightness OSDs go to the HUD";
}

void OsdInterceptor::restore()
{
    if (!m_original) {
        return;
    }
    disconnect(m_original, nullptr, m_service, nullptr);
    m_bus.unregisterObject(osdPath);
    if (!m_bus.registerObject(osdPath, m_original, osdExport)) {
        qCWarning(lcOsd) << "could not give" << osdPath << "back to Plasma's OSD:" << m_bus.lastError().message();
    }
    m_original.clear();
}

bool OsdInterceptor::osdEnabled() const
{
    // plasmashell reads the same switch (shell/osd.cpp); its watcher keeps this config fresh
    return KSharedConfig::openConfig(QStringLiteral("plasmarc"))->group(QStringLiteral("OSD")).readEntry("Enabled", true);
}

OsdHost *OsdInterceptor::hostOnScreen(const QRect &screenRect) const
{
    const auto it = std::find_if(m_hosts.cbegin(), m_hosts.cend(), [&screenRect](const OsdHost *host) {
        return host->screenRect() == screenRect;
    });
    return it == m_hosts.cend() ? nullptr : *it;
}

OsdHost *OsdInterceptor::hostFor(const QRect &screenRect, const QString &displayId) const
{
    if (screenRect.isValid()) {
        if (OsdHost *host = hostOnScreen(screenRect)) {
            return host;
        }
    }
    // powerdevil sends no screenRect; its display ids may be output names
    if (!displayId.isEmpty()) {
        const QList<QScreen *> screens = QGuiApplication::screens();
        const auto screen = std::find_if(screens.cbegin(), screens.cend(), [&displayId](const QScreen *screen) {
            return screen->name() == displayId;
        });
        if (screen != screens.cend()) {
            if (OsdHost *host = hostOnScreen((*screen)->geometry())) {
                return host;
            }
        }
    }
    const auto active = std::find_if(m_hosts.cbegin(), m_hosts.cend(), [](const OsdHost *host) {
        return host->isActiveScreen();
    });
    if (active != m_hosts.cend()) {
        return *active;
    }
    if (const QScreen *primary = QGuiApplication::primaryScreen()) {
        if (OsdHost *host = hostOnScreen(primary->geometry())) {
            return host;
        }
    }
    return m_hosts.isEmpty() ? nullptr : m_hosts.first();
}

void OsdInterceptor::showProgress(OsdHost *host, const QString &icon, int percent, int maximumPercent, const QString &additionalText)
{
    if (!osdEnabled()) {
        return;
    }
    const int value = qBound(0, percent, maximumPercent);
    if (host && !host->isSuppressed()) {
        Q_EMIT host->progressRequested(icon, value, maximumPercent);
    }
    Q_EMIT m_service->osdProgress(icon, value, maximumPercent, additionalText);
}

void OsdInterceptor::showMuted(OsdHost *host, const QString &icon, int maximumPercent, const QString &text)
{
    if (!osdEnabled()) {
        return;
    }
    if (host && !host->isSuppressed()) {
        Q_EMIT host->progressRequested(icon, 0, maximumPercent);
    }
    Q_EMIT m_service->osdText(icon, text);
}

void OsdInterceptor::brightness(int percent)
{
    showProgress(hostFor(), brightnessIcon, percent, fullPercent);
}

void OsdInterceptor::screenBrightness(int percent, const QString &displayId, const QString &displayLabel, const QRect &screenRect)
{
    // the HUD shows on that screen; the lock screen, which has no per-screen OSD, gets its name
    const QString label = QGuiApplication::screens().size() > 1 ? displayLabel : QString();
    showProgress(hostFor(screenRect, displayId), brightnessIcon, percent, fullPercent, label);
}

void OsdInterceptor::keyboardBrightness(int percent)
{
    showProgress(hostFor(), keyboardBrightnessIcon, percent, fullPercent);
}

void OsdInterceptor::volume(int percent, int maximumPercent)
{
    const QString icon = volumeIcon(percent);
    if (percent <= 0) {
        showMuted(hostFor(), icon, maximumPercent, i18ndc(plasmaDomain, "OSD informing that the system is muted, keep short", "Audio Muted"));
    } else {
        showProgress(hostFor(), icon, percent, maximumPercent);
    }
}

void OsdInterceptor::microphoneVolume(int percent)
{
    const QString icon = microphoneIcon(percent);
    if (percent <= 0) {
        showMuted(hostFor(), icon, fullPercent, i18ndc(plasmaDomain, "OSD informing that the microphone is muted, keep short", "Microphone Muted"));
    } else {
        showProgress(hostFor(), icon, percent, fullPercent);
    }
}

void OsdInterceptor::mediaPlayerVolume(int percent, const QString &playerName, const QString &playerIconName)
{
    if (percent == 0) {
        showMuted(hostFor(),
                  playerIconName,
                  fullPercent,
                  i18ndc(plasmaDomain, "OSD informing that some media app is muted, eg. Amarok Muted", "%1 Muted", playerName));
    } else {
        showProgress(hostFor(), playerIconName, percent, fullPercent, playerName);
    }
}
