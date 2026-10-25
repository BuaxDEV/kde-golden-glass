/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "glassregion.h"

#include "goldenglassroundedregion.h"

#include <KWindowEffects>
#include <QQuickWindow>

#include <algorithm>
#include <cmath>

namespace
{
// Las cuatro esquinas redondeadas; elípticas si el elemento está escalado
// distinto a lo ancho (rx) y a lo alto (ry).
QRegion roundedRegion(const QRect &rect, int rx, int ry)
{
    rx = std::clamp(rx, 0, rect.width() / 2);
    ry = std::clamp(ry, 0, rect.height() / 2);
    return GoldenGlass::roundedRectRegion(rect, rx, ry, true, true, true, true);
}
}

GlassRegion::GlassRegion(QQuickItem *parent)
    : QQuickItem(parent)
{
    m_pending.setSingleShot(true);
    connect(&m_pending, &QTimer::timeout, this, &GlassRegion::sync);
}

GlassRegion::~GlassRegion()
{
    if (m_window && !m_applied.isEmpty()) {
        KWindowEffects::enableBlurBehind(m_window, false);
    }
}

QQuickItem *GlassRegion::source() const
{
    return m_source ? m_source.data() : parentItem();
}

void GlassRegion::setSource(QQuickItem *source)
{
    if (m_source == source) {
        return;
    }
    m_source = source;
    requestUpdate();
    Q_EMIT sourceChanged();
}

bool GlassRegion::isActive() const
{
    return m_active;
}

void GlassRegion::setActive(bool active)
{
    if (m_active == active) {
        return;
    }
    m_active = active;
    requestUpdate();
    Q_EMIT activeChanged();
}

int GlassRegion::updateInterval() const
{
    return m_updateInterval;
}

void GlassRegion::setUpdateInterval(int interval)
{
    if (m_updateInterval == interval) {
        return;
    }
    m_updateInterval = std::max(0, interval);
    Q_EMIT updateIntervalChanged();
}

void GlassRegion::requestUpdate()
{
    m_force = true;
    if (m_window) {
        m_window->update();
    }
}

void GlassRegion::itemChange(ItemChange change, const ItemChangeData &value)
{
    if (change == ItemSceneChange) {
        setWindow(value.window);
    }
    QQuickItem::itemChange(change, value);
}

void GlassRegion::setWindow(QQuickWindow *window)
{
    if (m_window == window) {
        return;
    }
    if (m_window) {
        disconnect(m_window, nullptr, this, nullptr);
    }
    m_window = window;
    m_applied = QRegion();
    m_force = true;
    if (!window) {
        return;
    }
    // afterAnimating: en el hilo de la interfaz, en cada fotograma, después de
    // que Dialog haya reaccionado a mostrarse o cambiar de tamaño
    connect(window, &QQuickWindow::afterAnimating, this, &GlassRegion::sync);
    connect(window, &QWindow::visibleChanged, this, &GlassRegion::requestUpdate);
    connect(window, &QWindow::widthChanged, this, &GlassRegion::requestUpdate);
    connect(window, &QWindow::heightChanged, this, &GlassRegion::requestUpdate);
}

void GlassRegion::collect(QQuickItem *item, QRegion &region) const
{
    if (!item->isVisible() || qFuzzyIsNull(item->opacity())) {
        return;
    }
    if (item->property("goldenGlassTile").toBool()) {
        const QRect rect = item->mapRectToScene(item->boundingRect()).toAlignedRect();
        // el radio escala con el elemento (tarjetas que ceden al pulsarlas, el
        // resorte al abrir, que escala distinto a lo ancho y a lo alto)
        const qreal radius = item->property("radius").toReal();
        const qreal scaleX = item->width() > 0 ? rect.width() / item->width() : 1;
        const qreal scaleY = item->height() > 0 ? rect.height() / item->height() : 1;
        region += roundedRegion(rect, int(std::round(radius * scaleX)), int(std::round(radius * scaleY)));
        return;
    }
    const auto children = item->childItems();
    for (QQuickItem *child : children) {
        collect(child, region);
    }
}

void GlassRegion::sync()
{
    QQuickItem *root = source();
    if (!m_window || !m_window->isVisible() || !root) {
        return;
    }
    QRegion region;
    if (m_active) {
        collect(root, region);
    }
    if (!m_force && region == m_applied) {
        return;
    }
    // durante una animación, como mucho un envío cada updateInterval ms; el
    // temporizador manda el último estado aunque la animación ya haya parado
    if (!m_force && m_sinceLastUpdate.isValid() && m_sinceLastUpdate.elapsed() < m_updateInterval) {
        if (!m_pending.isActive()) {
            m_pending.start(int(m_updateInterval - m_sinceLastUpdate.elapsed()));
        }
        return;
    }
    m_pending.stop();
    m_force = false;
    m_applied = region;
    m_sinceLastUpdate.start();
    KWindowEffects::enableBlurBehind(m_window, !region.isEmpty(), region);
}

#include "moc_glassregion.cpp"
