/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "osdhost.h"

#include "osdinterceptor.h"

OsdHost::OsdHost(QObject *parent)
    : QObject(parent)
    , m_interceptor(OsdInterceptor::shared())
{
    m_interceptor->addHost(this);
}

OsdHost::~OsdHost()
{
    m_interceptor->removeHost(this);
}

QRect OsdHost::screenRect() const
{
    return m_screenRect;
}

void OsdHost::setScreenRect(const QRect &screenRect)
{
    if (m_screenRect != screenRect) {
        m_screenRect = screenRect;
        Q_EMIT screenRectChanged();
    }
}

bool OsdHost::isActiveScreen() const
{
    return m_activeScreen;
}

void OsdHost::setActiveScreen(bool activeScreen)
{
    if (m_activeScreen != activeScreen) {
        m_activeScreen = activeScreen;
        Q_EMIT activeScreenChanged();
    }
}

bool OsdHost::isSuppressed() const
{
    return m_suppressed;
}

void OsdHost::setSuppressed(bool suppressed)
{
    if (m_suppressed != suppressed) {
        m_suppressed = suppressed;
        Q_EMIT suppressedChanged();
    }
}

bool OsdHost::isIntercepting() const
{
    return m_interceptor->isIntercepting();
}
