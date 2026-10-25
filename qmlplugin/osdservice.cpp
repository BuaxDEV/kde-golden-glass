/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "osdservice.h"

#include "osdinterceptor.h"

OsdService::OsdService(OsdInterceptor *interceptor)
    : QObject(interceptor)
    , m_interceptor(interceptor)
{
}

void OsdService::brightnessChanged(int percent)
{
    m_interceptor->brightness(percent);
}

void OsdService::screenBrightnessChanged(int percent, const QString &displayId, const QString &displayLabel, int priority, const QRect &screenRect)
{
    Q_UNUSED(priority)
    m_interceptor->screenBrightness(percent, displayId, displayLabel, screenRect);
}

void OsdService::keyboardBrightnessChanged(int percent)
{
    m_interceptor->keyboardBrightness(percent);
}

void OsdService::volumeChanged(int percent)
{
    m_interceptor->volume(percent, 100);
}

void OsdService::volumeChanged(int percent, int maximumPercent)
{
    m_interceptor->volume(percent, maximumPercent);
}

void OsdService::microphoneVolumeChanged(int percent)
{
    m_interceptor->microphoneVolume(percent);
}

void OsdService::mediaPlayerVolumeChanged(int percent, const QString &playerName, const QString &playerIconName)
{
    m_interceptor->mediaPlayerVolume(percent, playerName, playerIconName);
}

void OsdService::kbdLayoutChanged(const QString &layoutName)
{
    m_interceptor->forward("kbdLayoutChanged", layoutName);
}

void OsdService::virtualDesktopChanged(const QString &currentVirtualDesktopName)
{
    m_interceptor->forward("virtualDesktopChanged", currentVirtualDesktopName);
}

void OsdService::touchpadEnabledChanged(bool touchpadEnabled)
{
    m_interceptor->forward("touchpadEnabledChanged", touchpadEnabled);
}

void OsdService::wifiEnabledChanged(bool wifiEnabled)
{
    m_interceptor->forward("wifiEnabledChanged", wifiEnabled);
}

void OsdService::bluetoothEnabledChanged(bool bluetoothEnabled)
{
    m_interceptor->forward("bluetoothEnabledChanged", bluetoothEnabled);
}

void OsdService::wwanEnabledChanged(bool wwanEnabled)
{
    m_interceptor->forward("wwanEnabledChanged", wwanEnabled);
}

void OsdService::virtualKeyboardEnabledChanged(bool virtualKeyboardEnabled)
{
    m_interceptor->forward("virtualKeyboardEnabledChanged", virtualKeyboardEnabled);
}

void OsdService::powerManagementInhibitedChanged(bool inhibited)
{
    m_interceptor->forward("powerManagementInhibitedChanged", inhibited);
}

void OsdService::powerProfileChanged(const QString &profile)
{
    m_interceptor->forward("powerProfileChanged", profile);
}

void OsdService::showText(const QString &icon, const QString &text)
{
    m_interceptor->forward("showText", icon, text);
}

void OsdService::hide()
{
    m_interceptor->forward("hide");
}
