/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "accessibilitysettings.h"

#include "goldenglass_tokens.h"

#include <KConfigGroup>
#include <KSharedConfig>

namespace
{
const QString accessibilityGroup = QStringLiteral("Accessibility");
}

AccessibilitySettings::AccessibilitySettings(QObject *parent)
    : QObject(parent)
    , m_watcher(KConfigWatcher::create(KSharedConfig::openConfig(QStringLiteral("goldenglassrc"), KConfig::SimpleConfig)))
    , m_showBorders(GoldenGlass::Tokens::AccessibilityShowBorders)
    , m_reduceTransparency(GoldenGlass::Tokens::AccessibilityReduceTransparency)
    , m_reduceMotion(GoldenGlass::Tokens::AccessibilityReduceMotion)
{
    connect(m_watcher.data(), &KConfigWatcher::configChanged, this, [this](const KConfigGroup &group) {
        if (group.name() == accessibilityGroup) {
            load();
        }
    });
    load();
}

bool AccessibilitySettings::showBorders() const
{
    return m_showBorders;
}

bool AccessibilitySettings::reduceTransparency() const
{
    return m_reduceTransparency;
}

bool AccessibilitySettings::reduceMotion() const
{
    return m_reduceMotion;
}

void AccessibilitySettings::load()
{
    const KConfigGroup group = m_watcher->config()->group(accessibilityGroup);
    // cada propiedad avisa solo si cambia: un aviso de otra clave del grupo no
    // despierta a quien sigue esta
    const auto update = [this](bool &member, bool value, void (AccessibilitySettings::*changed)()) {
        if (member != value) {
            member = value;
            Q_EMIT(this->*changed)();
        }
    };
    update(m_showBorders, group.readEntry("ShowBorders", GoldenGlass::Tokens::AccessibilityShowBorders), &AccessibilitySettings::showBordersChanged);
    update(m_reduceTransparency,
           group.readEntry("ReduceTransparency", GoldenGlass::Tokens::AccessibilityReduceTransparency),
           &AccessibilitySettings::reduceTransparencyChanged);
    update(m_reduceMotion, group.readEntry("ReduceMotion", GoldenGlass::Tokens::AccessibilityReduceMotion), &AccessibilitySettings::reduceMotionChanged);
}
