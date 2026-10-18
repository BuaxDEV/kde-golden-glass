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
    GlassRegion: pide a KWin blur solo detrás de las piezas de vidrio de su
    ventana, con sus esquinas redondeadas. Recorre el árbol de «source» (por
    defecto, su padre) y toma cada elemento visible con la propiedad
    goldenGlassTile a true; el radio sale de su propiedad «radius» y sigue
    las escalas (también distintas a lo ancho y a lo alto). El efecto
    goldenglass_glass dibuja la refracción de cada pieza por separado.

    Pensado para un PlasmaCore.Dialog sin fondo (NoBackground), que no pide blur.

        GlassRegion { anchors.fill: parent }

    active: false quita el blur (p. ej. al desvanecerse la ventana).
    updateInterval: ms mínimos entre dos envíos a KWin mientras la región
    cambia (animaciones); el último cambio siempre llega.
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
    void collect(QQuickItem *item, QRegion &region) const;

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
