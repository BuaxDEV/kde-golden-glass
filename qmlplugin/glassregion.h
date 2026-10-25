/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QElapsedTimer>
#include <QPointer>
#include <QQuickItem>
#include <QRegion>
#include <QTimer>

class QQuickWindow;

/*
    GlassRegion: asks KWin for blur only behind the glass pieces of its
    window, with their rounded corners. It walks the tree of «source» (its
    parent by default) and takes every visible item whose goldenGlassTile
    property is true; the radius comes from its «radius» property and follows
    its scale (also when width and height scale differently). Ancestors with
    clip: true cut each piece as Qt Quick cuts their pixels, so a scrolled
    list asks for no blur outside its view. The goldenglass_glass effect draws
    the refraction of each piece on its own.

    Meant for a PlasmaCore.Dialog without background (NoBackground), which
    asks for no blur.

        GlassRegion { anchors.fill: parent }

    active: false removes the blur (e.g. while the window fades out).
    updateInterval: minimum ms between two updates sent to KWin while the
    region changes (animations); the last change always arrives.
*/
class GlassRegion : public QQuickItem
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(QQuickItem *source READ source WRITE setSource NOTIFY sourceChanged)
    Q_PROPERTY(bool active READ isActive WRITE setActive NOTIFY activeChanged)
    Q_PROPERTY(int updateInterval READ updateInterval WRITE setUpdateInterval NOTIFY updateIntervalChanged)

public:
    explicit GlassRegion(QQuickItem *parent = nullptr);
    ~GlassRegion() override;

    QQuickItem *source() const;
    void setSource(QQuickItem *source);

    bool isActive() const;
    void setActive(bool active);

    int updateInterval() const;
    void setUpdateInterval(int interval);

    // Region of the glass pieces under «source», in scene coordinates
    QRegion collectRegion() const;

Q_SIGNALS:
    void sourceChanged();
    void activeChanged();
    void updateIntervalChanged();

protected:
    void itemChange(ItemChange change, const ItemChangeData &value) override;

private:
    void setWindow(QQuickWindow *window);
    void requestUpdate();
    void sync();
    void collect(QQuickItem *item, const QRect &clip, QRegion &region) const;

    QPointer<QQuickItem> m_source;
    QPointer<QQuickWindow> m_window;
    QRegion m_applied;
    bool m_active = true;
    // Dialog quita el blur al mostrarse o cambiar de tamaño: hay que volver a pedirlo
    bool m_force = true;
    int m_updateInterval = 0;
    QElapsedTimer m_sinceLastUpdate;
    QTimer m_pending;
};
