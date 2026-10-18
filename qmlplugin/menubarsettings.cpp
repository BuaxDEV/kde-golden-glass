/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "menubarsettings.h"

#include "goldenglass_tokens.h"

#include <KConfigGroup>
#include <KSharedConfig>

MenuBarSettings::MenuBarSettings(QObject *parent)
    : QObject(parent)
    , m_watcher(KConfigWatcher::create(KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig)))
    , m_background(GoldenGlass::Tokens::MenubarBackground)
{
    connect(m_watcher.data(), &KConfigWatcher::configChanged, this, [this](const KConfigGroup &group) {
        if (group.name() == QLatin1String("Plasma")) {
            load();
        }
    });
    load();
}

bool MenuBarSettings::background() const
{
    return m_background;
}

double MenuBarSettings::inactiveOpacity() const
{
    return GoldenGlass::Tokens::MenubarInactiveOpacity;
}

void MenuBarSettings::load()
{
    const KConfigGroup group = m_watcher->config()->group(QStringLiteral("Plasma"));
    const bool background = group.readEntry("MenubarBackground", GoldenGlass::Tokens::MenubarBackground);
    if (m_background != background) {
        m_background = background;
        Q_EMIT backgroundChanged();
    }
}
