/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QRect>
#include <QString>

class OsdInterceptor;

/*
    The object OsdInterceptor puts at /org/kde/osdService in place of
    plasmashell's own. Its slots and signals copy those of Plasma's Osd
    (shell/osd.h of plasma-workspace 6.8), in the same order and with the same
    argument names, so that its introspection is identical to the original's:
    plasma-pa, powerdevil, KWin and the lock screen cannot tell them apart.
    OsdInterceptor only takes over when the original exports exactly these
    signatures, so any change here must follow Plasma's.
*/
class OsdService : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.kde.osdService")

public:
    explicit OsdService(OsdInterceptor *interceptor);

public Q_SLOTS:
    void brightnessChanged(int percent);
    void screenBrightnessChanged(int percent, const QString &displayId, const QString &displayLabel, int priority, const QRect &screenRect);
    void keyboardBrightnessChanged(int percent);
    void volumeChanged(int percent);
    void volumeChanged(int percent, int maximumPercent);
    void microphoneVolumeChanged(int percent);
    void mediaPlayerVolumeChanged(int percent, const QString &playerName, const QString &playerIconName);
    void kbdLayoutChanged(const QString &layoutName);
    void virtualDesktopChanged(const QString &currentVirtualDesktopName);
    void touchpadEnabledChanged(bool touchpadEnabled);
    void wifiEnabledChanged(bool wifiEnabled);
    void bluetoothEnabledChanged(bool bluetoothEnabled);
    void wwanEnabledChanged(bool wwanEnabled);
    void virtualKeyboardEnabledChanged(bool virtualKeyboardEnabled);
    void powerManagementInhibitedChanged(bool inhibited);
    void powerProfileChanged(const QString &profile);
    void showText(const QString &icon, const QString &text);
    void hide();

Q_SIGNALS:
    // what the lock screen (kscreenlocker_greet) listens to
    void osdProgress(const QString &icon, const int percent, const int maximumPercent, const QString &additionalText);
    void osdText(const QString &icon, const QString &text);

private:
    OsdInterceptor *const m_interceptor;
};
