/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <KConfigWatcher>
#include <QObject>
#include <QQmlEngine>

/*
    AccessibilitySettings: los ajustes de accesibilidad de GoldenGlass para QML
    (el único tipo que los lee: plasmoides, shell y Motion.qml). Lee
    goldenglassrc [Accessibility] ShowBorders, ReduceTransparency y
    ReduceMotion (de fábrica, los tokens [accessibility]) y los sigue en vivo:
    quien los escribe lo hace con aviso de cambio (KConfig::Notify). Contrato y
    escritores: «Accesibilidad» en docs/ARCHITECTURE.md.

        AccessibilitySettings { id: accessibility }
        opacity: accessibility.reduceTransparency ? 1 : glassAlpha
*/
class AccessibilitySettings : public QObject
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(bool showBorders READ showBorders NOTIFY showBordersChanged)
    Q_PROPERTY(bool reduceTransparency READ reduceTransparency NOTIFY reduceTransparencyChanged)
    Q_PROPERTY(bool reduceMotion READ reduceMotion NOTIFY reduceMotionChanged)

public:
    explicit AccessibilitySettings(QObject *parent = nullptr);

    bool showBorders() const;
    bool reduceTransparency() const;
    bool reduceMotion() const;

Q_SIGNALS:
    void showBordersChanged();
    void reduceTransparencyChanged();
    void reduceMotionChanged();

private:
    void load();

    KConfigWatcher::Ptr m_watcher;
    bool m_showBorders;
    bool m_reduceTransparency;
    bool m_reduceMotion;
};
