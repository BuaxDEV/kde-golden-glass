/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "iconthemewatcher.h"

#include <KIconLoader>

#include <QTimer>

namespace
{
// plasma-changeicons sends one iconChanged per icon group, a few milliseconds apart
constexpr int kSettleMs = 50;
}

IconThemeWatcher::IconThemeWatcher(QObject *parent)
    : QObject(parent)
    , m_settle(new QTimer(this))
{
    m_settle->setSingleShot(true);
    m_settle->setInterval(kSettleMs);
    connect(m_settle, &QTimer::timeout, this, [this] {
        ++m_revision;
        Q_EMIT revisionChanged();
    });
    connect(KIconLoader::global(), &KIconLoader::iconChanged, m_settle, qOverload<>(&QTimer::start));
}

int IconThemeWatcher::revision() const
{
    return m_revision;
}
