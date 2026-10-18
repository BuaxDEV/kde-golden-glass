/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "glassregion.h"

#include <KWindowEffects>
#include <QQuickWindow>

#include <algorithm>
#include <cmath>

namespace
{
// Rectángulo con las cuatro esquinas redondeadas, en franjas (como la máscara
// del SVG de Plasma): el efecto mide el radio de cada esquina en ellas.
QRegion roundedRegion(const QRect &rect, int radius)
{
    radius = std::clamp(radius, 0, std::min(rect.width(), rect.height()) / 2);
    QRegion region(rect);
    if (radius == 0) {
        return region;
    }
    const int d = 2 * radius;
    const QRect corners[] = {
        QRect(rect.left(), rect.top(), radius, radius),
        QRect(rect.right() - radius + 1, rect.top(), radius, radius),
        QRect(rect.left(), rect.bottom() - radius + 1, radius, radius),
        QRect(rect.right() - radius + 1, rect.bottom() - radius + 1, radius, radius),
    };
    const QRect ellipses[] = {
        QRect(rect.left(), rect.top(), d, d),
        QRect(rect.right() - d + 1, rect.top(), d, d),
        QRect(rect.left(), rect.bottom() - d + 1, d, d),
        QRect(rect.right() - d + 1, rect.bottom() - d + 1, d, d),
    };
    for (int i = 0; i < 4; ++i) {
        region -= QRegion(corners[i]) - QRegion(ellipses[i], QRegion::Ellipse);
    }
    return region;
}
}

GlassRegion::GlassRegion(QQuickItem *parent)
    : QQuickItem(parent)
{
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
    m_force = true;
    Q_EMIT sourceChanged();
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
    const auto force = [this] {
        m_force = true;
        if (m_window) {
            m_window->update();
        }
    };
    connect(window, &QWindow::visibleChanged, this, force);
    connect(window, &QWindow::widthChanged, this, force);
    connect(window, &QWindow::heightChanged, this, force);
}

void GlassRegion::collect(QQuickItem *item, QRegion &region) const
{
    if (!item->isVisible() || qFuzzyIsNull(item->opacity())) {
        return;
    }
    if (item->property("goldenGlassTile").toBool()) {
        const QRect rect = item->mapRectToScene(item->boundingRect()).toAlignedRect();
        // el radio escala con el elemento (botones que encogen al pulsarlos)
        const qreal scale = item->width() > 0 ? rect.width() / item->width() : 1;
        region += roundedRegion(rect, int(std::round(item->property("radius").toReal() * scale)));
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
    collect(root, region);
    if (!m_force && region == m_applied) {
        return;
    }
    m_force = false;
    m_applied = region;
    KWindowEffects::enableBlurBehind(m_window, !region.isEmpty(), region);
}

#include "moc_glassregion.cpp"
