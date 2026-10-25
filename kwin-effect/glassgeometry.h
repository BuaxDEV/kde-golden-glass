/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Geometría del vidrio a partir de la región de blur: piezas separadas y radio
 * de cada esquina. Plantillas sobre el tipo de rectángulo (KWin::RectF en el
 * efecto, QRectF en las pruebas) para probarlas sin enlazar con KWin.
 */
#pragma once

#include <QHash>
#include <QList>
#include <QSpan>
#include <QVector4D>

#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>

namespace GoldenGlass
{

// Radio de cada esquina medido en la región de blur: Plasma la manda con la
// forma redondeada de su SVG, en franjas; una esquina mide lo que tardan las
// franjas en tocar el lateral. (arriba-izq., arriba-der., abajo-izq., abajo-der.)
template<typename Rect>
QVector4D cornerRadii(const QList<Rect> &rects, const Rect &box)
{
    const float maxRadius = std::min(box.width(), box.height()) / 2;
    float topLeft = maxRadius, topRight = maxRadius, bottomLeft = maxRadius, bottomRight = maxRadius;
    constexpr float epsilon = 0.5;
    for (const Rect &rect : rects) {
        if (std::abs(rect.left() - box.left()) < epsilon) {
            topLeft = std::min(topLeft, float(rect.top() - box.top()));
            bottomLeft = std::min(bottomLeft, float(box.bottom() - rect.bottom()));
        }
        if (std::abs(rect.right() - box.right()) < epsilon) {
            topRight = std::min(topRight, float(rect.top() - box.top()));
            bottomRight = std::min(bottomRight, float(box.bottom() - rect.bottom()));
        }
    }
    return QVector4D(topLeft, topRight, bottomLeft, bottomRight);
}

// Piezas separadas de la región (rectángulos que se tocan o se solapan): una
// ventana puede llevar varias piezas de vidrio sueltas (las tarjetas del Centro
// de control) y cada una tiene su propio borde, sus esquinas y su refracción.
template<typename Rect>
struct GlassPiece {
    QList<Rect> rects;
    Rect bounds;
};

// rects: los de una región, ordenados por su borde superior
template<typename Rect>
QList<GlassPiece<Rect>> glassPieces(QSpan<const Rect> rects)
{
    std::vector<qsizetype> parent(rects.size());
    std::iota(parent.begin(), parent.end(), 0);
    const auto find = [&parent](qsizetype i) {
        while (parent[i] != i) {
            i = parent[i] = parent[parent[i]];
        }
        return i;
    };
    constexpr float touch = 0.5;
    for (qsizetype i = 0; i < rects.size(); ++i) {
        const Rect grown = rects[i].adjusted(-touch, -touch, touch, touch);
        for (qsizetype j = i + 1; j < rects.size() && rects[j].top() <= grown.bottom(); ++j) {
            if (grown.intersects(rects[j])) {
                parent[find(i)] = find(j);
            }
        }
    }
    QHash<qsizetype, GlassPiece<Rect>> pieces;
    for (qsizetype i = 0; i < rects.size(); ++i) {
        GlassPiece<Rect> &piece = pieces[find(i)];
        piece.bounds = piece.rects.isEmpty() ? rects[i] : piece.bounds.united(rects[i]);
        piece.rects.append(rects[i]);
    }
    return pieces.values();
}

} // namespace GoldenGlass
