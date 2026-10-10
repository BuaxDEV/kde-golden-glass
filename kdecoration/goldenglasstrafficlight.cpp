/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "goldenglasstrafficlight.h"

#include "goldenglass_tokens.h"

#include <QLinearGradient>
#include <QPainter>
#include <QPolygonF>
#include <QRadialGradient>

namespace GoldenGlass::TrafficLight
{

namespace
{
void colorsFor(Kind kind, const State &state, QColor &body, QColor &rim)
{
    if (!state.lit) {
        body = QColor::fromRgba(state.darkTitleBar ? Tokens::TrafficLightInactiveDark : Tokens::TrafficLightInactiveLight);
        rim = body.darker(112);
    } else {
        switch (kind) {
        case Kind::Close:
            body = QColor::fromRgba(Tokens::TrafficLightClose);
            rim = QColor::fromRgba(Tokens::TrafficLightCloseBorder);
            break;
        case Kind::Minimize:
            body = QColor::fromRgba(Tokens::TrafficLightMinimize);
            rim = QColor::fromRgba(Tokens::TrafficLightMinimizeBorder);
            break;
        case Kind::Zoom:
            body = QColor::fromRgba(Tokens::TrafficLightZoom);
            rim = QColor::fromRgba(Tokens::TrafficLightZoomBorder);
            break;
        }
    }
    if (state.pressed) {
        body = body.darker(125);
        rim = rim.darker(125);
    }
}

void drawGlyph(QPainter *painter, const QPointF &center, Kind kind, const State &state, qreal u)
{
    QColor glyph = QColor::fromRgba(Tokens::TrafficLightGlyph);
    glyph.setAlphaF(glyph.alphaF() * state.glyphOpacity);

    switch (kind) {
    case Kind::Close: {
        painter->setPen(QPen(glyph, u / 10.0, Qt::SolidLine, Qt::RoundCap));
        painter->setBrush(Qt::NoBrush);
        const qreal k = u * 0.2;
        painter->drawLine(center + QPointF(-k, -k), center + QPointF(k, k));
        painter->drawLine(center + QPointF(k, -k), center + QPointF(-k, k));
        break;
    }
    case Kind::Minimize: {
        painter->setPen(QPen(glyph, u / 11.0, Qt::SolidLine, Qt::RoundCap));
        const qreal k = u * 0.25;
        painter->drawLine(center + QPointF(-k, 0), center + QPointF(k, 0));
        break;
    }
    case Kind::Zoom: {
        // two triangles pointing to opposite corners; inward when maximized
        painter->setPen(Qt::NoPen);
        painter->setBrush(glyph);
        const qreal leg = u * 0.34;
        if (state.maximized) {
            const qreal inner = u * 0.06;
            const QPointF a = center + QPointF(-inner, -inner);
            const QPointF b = center + QPointF(inner, inner);
            painter->drawPolygon(QPolygonF{a, a + QPointF(-leg, 0), a + QPointF(0, -leg)});
            painter->drawPolygon(QPolygonF{b, b + QPointF(leg, 0), b + QPointF(0, leg)});
        } else {
            const qreal edge = u * 0.25;
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

    const qreal diameter = Tokens::TrafficLightDiameter;
    const QRectF circle(center - QPointF(diameter / 2, diameter / 2), QSizeF(diameter, diameter));

    QColor body;
    QColor rim;
    colorsFor(kind, state, body, rim);

    // body with a hairline rim
    painter->setPen(QPen(rim, 0.75));
    painter->setBrush(body);
    painter->drawEllipse(circle.adjusted(0.375, 0.375, -0.375, -0.375));

    if (state.lit) {
        // glass shading (macOS 27): soft top light fading into the body...
        QLinearGradient shade(circle.topLeft(), circle.bottomLeft());
        shade.setColorAt(0.0, QColor(255, 255, 255, 90));
        shade.setColorAt(0.55, QColor(255, 255, 255, 0));
        shade.setColorAt(1.0, QColor(0, 0, 0, 28));
        painter->setPen(Qt::NoPen);
        painter->setBrush(shade);
        painter->drawEllipse(circle.adjusted(0.75, 0.75, -0.75, -0.75));

        // ...and a small specular highlight near the top
        const QRectF spec(circle.left() + diameter * 0.24, circle.top() + diameter * 0.1, diameter * 0.52, diameter * 0.34);
        QRadialGradient highlight(spec.center(), spec.width() / 2);
        highlight.setColorAt(0.0, QColor(255, 255, 255, 150));
        highlight.setColorAt(1.0, QColor(255, 255, 255, 0));
        painter->setBrush(highlight);
        painter->drawEllipse(spec);

        if (state.glyphOpacity > 0) {
            drawGlyph(painter, center, kind, state, diameter);
        }
    }

    painter->restore();
}

}
