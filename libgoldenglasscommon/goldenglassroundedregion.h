/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QRect>
#include <QRegion>

namespace GoldenGlass
{
// Rectángulo con las esquinas elegidas redondeadas, en franjas (como la máscara
// del SVG de Plasma): el efecto de KWin mide el radio de cada esquina en ellas.
// Las esquinas son elípticas si rx y ry difieren. Lo usan el estilo (región de
// blur de las ventanas) y el módulo QML org.goldenglass.glass.
inline QRegion roundedRectRegion(const QRect &rect, int rx, int ry, bool topLeft, bool topRight, bool bottomLeft, bool bottomRight)
{
    QRegion region(rect);
    if (rx <= 0 || ry <= 0) {
        return region;
    }
    const int dx = 2 * rx;
    const int dy = 2 * ry;
    // a cada esquina se le quita lo que queda fuera de su elipse
    const auto cut = [&](bool round, int x, int y, int ex, int ey) {
        if (round) {
            region -= QRegion(QRect(x, y, rx, ry)) - QRegion(QRect(ex, ey, dx, dy), QRegion::Ellipse);
        }
    };
    cut(topLeft, rect.left(), rect.top(), rect.left(), rect.top());
    cut(topRight, rect.right() - rx + 1, rect.top(), rect.right() - dx + 1, rect.top());
    cut(bottomLeft, rect.left(), rect.bottom() - ry + 1, rect.left(), rect.bottom() - dy + 1);
    cut(bottomRight, rect.right() - rx + 1, rect.bottom() - ry + 1, rect.right() - dx + 1, rect.bottom() - dy + 1);
    return region;
}
}
