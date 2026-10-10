/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Vista previa de los semáforos en todos sus estados, sin KWin:
 *   trafficlight_preview salida.png
 * Filas: barra de título clara y oscura (a tamaño real y ampliadas ×4).
 */

#include "../goldenglasstrafficlight.h"
#include "goldenglass_tokens.h"

#include <QFont>
#include <QGuiApplication>
#include <QImage>
#include <QPainter>

using namespace GoldenGlass;

namespace
{
struct Column {
    const char *label;
    TrafficLight::State state;
};

const Column columns[] = {
    {"activa", {true, false, false, false, 0.0}},
    {"hover", {true, false, false, false, 1.0}},
    {"pulsado", {true, true, false, false, 1.0}},
    {"maximizada", {true, false, true, false, 1.0}},
    {"inactiva", {false, false, false, false, 0.0}},
};

constexpr int kCellWidth = 3 * (Tokens::TrafficLightDiameter + Tokens::TrafficLightGap) + 16;
constexpr int kRowHeight = 28;

// Dibuja una fila de celdas (una por estado) a escala 1 desde `origin`.
void drawRow(QPainter &p, const QPointF &origin, const QColor &titleBar, bool dark)
{
    const int step = Tokens::TrafficLightDiameter + Tokens::TrafficLightGap;
    for (int c = 0; c < int(std::size(columns)); ++c) {
        const QRectF cell(origin + QPointF(c * kCellWidth, 0), QSizeF(kCellWidth, kRowHeight));
        p.fillRect(cell, titleBar);
        TrafficLight::State st = columns[c].state;
        st.darkTitleBar = dark;
        const TrafficLight::Kind kinds[] = {TrafficLight::Kind::Close, TrafficLight::Kind::Minimize, TrafficLight::Kind::Zoom};
        for (int k = 0; k < 3; ++k) {
            const QPointF center(cell.left() + 8 + step / 2.0 + k * step, cell.center().y());
            TrafficLight::render(&p, center, kinds[k], st);
        }
    }
}
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    const QString out = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QStringLiteral("trafficlights.png");

    const int width = kCellWidth * int(std::size(columns));
    QImage row(width, kRowHeight * 2, QImage::Format_ARGB32_Premultiplied);
    row.fill(Qt::transparent);
    {
        QPainter p(&row);
        drawRow(p, QPointF(0, 0), QColor(0xF6, 0xF6, 0xF6), false);
        drawRow(p, QPointF(0, kRowHeight), QColor(0x38, 0x38, 0x38), true);
    }

    constexpr int zoom = 4;
    const int labelHeight = 18;
    QImage sheet(width * zoom, labelHeight + row.height() * (zoom + 1) + 8, QImage::Format_ARGB32_Premultiplied);
    sheet.fill(QColor(0xE0, 0xE0, 0xE0));
    QPainter p(&sheet);
    p.setFont(QFont(QStringLiteral("GoldenGlass Sans"), 9));
    for (int c = 0; c < int(std::size(columns)); ++c) {
        p.drawText(QRectF(c * kCellWidth * zoom, 0, kCellWidth * zoom, labelHeight), Qt::AlignCenter, QString::fromUtf8(columns[c].label));
    }
    p.drawImage(QPointF(0, labelHeight), row); // tamaño real
    p.setRenderHint(QPainter::SmoothPixmapTransform, false);
    p.drawImage(QRectF(0, labelHeight + row.height() + 8, width * zoom, row.height() * zoom), row); // ×4
    p.end();

    return sheet.save(out) ? 0 : 1;
}
