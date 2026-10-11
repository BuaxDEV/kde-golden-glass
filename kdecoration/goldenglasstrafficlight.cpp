/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "goldenglasstrafficlight.h"

#include "goldenglass_tokens.h"

#include <QLinearGradient>
#include <QPainter>
#include <QPainterPath>
#include <QPolygonF>
#include <QRadialGradient>

namespace GoldenGlass::TrafficLight
{

namespace
{
struct Colors {
    QColor body;
    QColor rim;
    QColor glyph;
};

Colors colorsFor(Kind kind, const State &state)
{
    Colors c;
    if (!state.lit) {
        c.body = QColor::fromRgba(state.darkTitleBar ? Tokens::TrafficLightInactiveDark : Tokens::TrafficLightInactiveLight);
        c.rim = state.darkTitleBar ? c.body.lighter(118) : c.body.darker(112);
        return c;
    }
    switch (kind) {
    case Kind::Close:
        c = {QColor::fromRgba(Tokens::TrafficLightClose), QColor::fromRgba(Tokens::TrafficLightCloseBorder), QColor::fromRgba(Tokens::TrafficLightCloseGlyph)};
        break;
    case Kind::Minimize:
        c = {QColor::fromRgba(Tokens::TrafficLightMinimize),
             QColor::fromRgba(Tokens::TrafficLightMinimizeBorder),
             QColor::fromRgba(Tokens::TrafficLightMinimizeGlyph)};
        break;
    case Kind::Zoom:
        c = {QColor::fromRgba(Tokens::TrafficLightZoom), QColor::fromRgba(Tokens::TrafficLightZoomBorder), QColor::fromRgba(Tokens::TrafficLightZoomGlyph)};
        break;
    }
    if (state.pressed) {
        c.body = c.body.darker(122);
        c.rim = c.rim.darker(122);
        c.glyph = c.glyph.darker(140);
    }
    return c;
}

QColor withAlpha(QColor color, qreal alpha)
{
    color.setAlphaF(color.alphaF() * alpha);
    return color;
}

// Glyphs as in macOS: ×, − and the two full-screen triangles, tinted per button.
void drawGlyph(QPainter *painter, const QPointF &center, Kind kind, const State &state, const QColor &color, qreal d)
{
    const QColor glyph = withAlpha(color, state.glyphOpacity);

    switch (kind) {
    case Kind::Close: {
        painter->setPen(QPen(glyph, d * 0.09, Qt::SolidLine, Qt::RoundCap));
        painter->setBrush(Qt::NoBrush);
        const qreal k = d * 0.2;
        painter->drawLine(center + QPointF(-k, -k), center + QPointF(k, k));
        painter->drawLine(center + QPointF(k, -k), center + QPointF(-k, k));
        break;
    }
    case Kind::Minimize: {
        painter->setPen(QPen(glyph, d * 0.095, Qt::SolidLine, Qt::RoundCap));
        const qreal k = d * 0.26;
        painter->drawLine(center + QPointF(-k, 0), center + QPointF(k, 0));
        break;
    }
    case Kind::Zoom: {
        // Two right triangles in opposite corners, separated by a diagonal
        // gap: pointing outward (enter full screen) or inward when maximized.
        painter->setPen(Qt::NoPen);
        painter->setBrush(glyph);
        const qreal leg = d * 0.36;
        if (state.maximized) {
            const qreal inner = d * 0.05;
            const QPointF a = center + QPointF(-inner, -inner);
            const QPointF b = center + QPointF(inner, inner);
            painter->drawPolygon(QPolygonF{a, a + QPointF(-leg, 0), a + QPointF(0, -leg)});
            painter->drawPolygon(QPolygonF{b, b + QPointF(leg, 0), b + QPointF(0, leg)});
        } else {
            const qreal edge = d * 0.24;
            const QPointF a = center + QPointF(-edge, -edge);
            const QPointF b = center + QPointF(edge, edge);
            painter->drawPolygon(QPolygonF{a, a + QPointF(leg, 0), a + QPointF(0, leg)});
            painter->drawPolygon(QPolygonF{b, b + QPointF(-leg, 0), b + QPointF(0, -leg)});
        }
        break;
    }
    }
}
}

void render(QPainter *painter, const QPointF &center, Kind kind, const State &state)
{
    painter->save();
    painter->setRenderHints(QPainter::Antialiasing);

    // Pressed: the control shrinks slightly, as the macOS 27 ones animate.
    const qreal d = Tokens::TrafficLightDiameter * (state.pressed ? 0.9 : 1.0);
    const qreal r = d / 2;
    const QRectF circle(center - QPointF(r, r), QSizeF(d, d));
    const Colors c = colorsFor(kind, state);
    // Highlights fade on inactive windows (gray glass, still with depth).
    const qreal shine = state.lit ? 1.0 : 0.45;

    // 1. Soft drop shadow: the glass piece sits on top of the window.
    {
        QRadialGradient shadow(center + QPointF(0, d * 0.07), r * 1.18);
        shadow.setColorAt(0.78, QColor(0, 0, 0, state.lit ? 60 : 30));
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0));
        painter->setPen(Qt::NoPen);
        painter->setBrush(shadow);
        painter->drawEllipse(center + QPointF(0, d * 0.07), r * 1.18, r * 1.18);
    }

    // 2. Body: the color with some volume (lighter on top, deeper at the bottom).
    {
        QLinearGradient body(circle.topLeft(), circle.bottomLeft());
        body.setColorAt(0.0, c.body.lighter(state.lit ? 112 : 104));
        body.setColorAt(1.0, c.body.darker(state.lit ? 106 : 102));
        painter->setPen(QPen(c.rim, 0.75));
        painter->setBrush(body);
        painter->drawEllipse(circle.adjusted(0.375, 0.375, -0.375, -0.375));
    }

    // 3. Bottom highlight: light gathering inside the glass at the bottom.
    {
        QRadialGradient glow(QPointF(center.x(), circle.bottom() - d * 0.14), r * 0.95);
        glow.setColorAt(0.0, QColor(255, 255, 255, int(110 * shine)));
        glow.setColorAt(1.0, QColor(255, 255, 255, 0));
        QPainterPath clip;
        clip.addEllipse(circle.adjusted(0.75, 0.75, -0.75, -0.75));
        painter->setClipPath(clip);
        painter->setPen(Qt::NoPen);
        painter->setBrush(glow);
        painter->drawEllipse(QPointF(center.x(), circle.bottom() - d * 0.14), r * 0.95, r * 0.6);
        painter->setClipping(false);
    }

    // 4. Top highlight: the glossy cap of the glass.
    {
        const QRectF cap(circle.left() + d * 0.17, circle.top() + d * 0.06, d * 0.66, d * 0.44);
        QLinearGradient gloss(cap.topLeft(), cap.bottomLeft());
        gloss.setColorAt(0.0, QColor(255, 255, 255, int(200 * shine)));
        gloss.setColorAt(1.0, QColor(255, 255, 255, int(20 * shine)));
        painter->setPen(Qt::NoPen);
        painter->setBrush(gloss);
        painter->drawEllipse(cap);
    }

    if (state.lit && state.glyphOpacity > 0) {
        drawGlyph(painter, center, kind, state, c.glyph, d);
    }

    painter->restore();
}

}
