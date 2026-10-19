/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#pragma once

#include <QPointF>

class QPainter;

namespace GoldenGlass::TrafficLight
{

enum class Kind {
    Close,
    Minimize,
    Zoom,
};

struct State {
    //* colored (window active or group hovered); gray otherwise
    bool lit = true;
    bool pressed = false;
    //* zoom glyph points inward when the window is maximized
    bool maximized = false;
    //* picks the inactive gray for dark or light title bars
    bool darkTitleBar = false;
    //* 0 (hidden) .. 1 (fully visible); glyphs only show while lit
    qreal glyphOpacity = 0;
};

//* Draws a macOS 27 traffic light (glass body + glyph) centered at `center`,
//* sized and colored from the design tokens.
void render(QPainter *painter, const QPointF &center, Kind kind, const State &state);

}
