/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QPointer>
#include <QQuickItem>
#include <QRegion>

class QQuickWindow;

/*
    GlassRegion: pide a KWin blur solo detrás de las piezas de vidrio de su
    ventana, con sus esquinas redondeadas. Recorre el árbol de «source» (por
    defecto, su padre) y toma cada elemento visible con la propiedad
    goldenGlassTile a true; el radio sale de su propiedad «radius». El efecto
    goldenglass_glass dibuja la refracción de cada pieza por separado.

    Pensado para un PlasmaCore.Dialog sin fondo (NoBackground), que no pide blur.

        GlassRegion { anchors.fill: parent }
*/
class GlassRegion : public QQuickItem
{
    Q_OBJECT
    QML_ELEMENT

    Q_PROPERTY(QQuickItem *source READ source WRITE setSource NOTIFY sourceChanged)

public:
    explicit GlassRegion(QQuickItem *parent = nullptr);
    ~GlassRegion() override;

    QQuickItem *source() const;
    void setSource(QQuickItem *source);

Q_SIGNALS:
    void sourceChanged();

protected:
    void itemChange(ItemChange change, const ItemChangeData &value) override;

private:
    void setWindow(QQuickWindow *window);
    void sync();
    void collect(QQuickItem *item, QRegion &region) const;

    QPointer<QQuickItem> m_source;
    QPointer<QQuickWindow> m_window;
    QRegion m_applied;
    // Dialog quita el blur al mostrarse o cambiar de tamaño: hay que volver a pedirlo
    bool m_force = true;
};
