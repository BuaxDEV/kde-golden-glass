/*
 * SPDX-FileCopyrightText: 2026 GoldenGlass contributors
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Pruebas de glassgeometry.h (piezas y esquinas del vidrio) con QRectF, sin
 * KWin: las regiones imitan las que manda Plasma, con las esquinas redondeadas
 * en franjas.
 */

#include "glassgeometry.h"

#include <QRectF>
#include <QTest>

#include <algorithm>

using GoldenGlass::cornerRadii;
using GoldenGlass::GlassPiece;

namespace
{
QList<GlassPiece<QRectF>> pieces(const QList<QRectF> &rects)
{
    auto result = GoldenGlass::glassPieces<QRectF>(QSpan<const QRectF>(rects));
    // el orden de las piezas no está definido: por posición
    std::sort(result.begin(), result.end(), [](const auto &a, const auto &b) {
        return std::pair(a.bounds.top(), a.bounds.left()) < std::pair(b.bounds.top(), b.bounds.left());
    });
    return result;
}

// rectángulo de 100×50 con esquinas de radio 10 en franjas, como una región de Plasma
QList<QRectF> roundedStrips(qreal x = 0, qreal y = 0)
{
    return {
        QRectF(x + 10, y + 0, 80, 2),
        QRectF(x + 5, y + 2, 90, 3),
        QRectF(x + 2, y + 5, 96, 5),
        QRectF(x + 0, y + 10, 100, 30),
        QRectF(x + 2, y + 40, 96, 5),
        QRectF(x + 5, y + 45, 90, 3),
        QRectF(x + 10, y + 48, 80, 2),
    };
}
}

class GlassGeometryTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void emptyRegion()
    {
        QVERIFY(pieces({}).isEmpty());
    }

    void roundedShapeIsOnePiece()
    {
        const auto result = pieces(roundedStrips());
        QCOMPARE(result.size(), 1);
        QCOMPARE(result[0].bounds, QRectF(0, 0, 100, 50));
        QCOMPARE(result[0].rects.size(), 7);
        QCOMPARE(cornerRadii(result[0].rects, result[0].bounds), QVector4D(10, 10, 10, 10));
    }

    void onlyTopCornersRounded()
    {
        const QList<QRectF> rects{QRectF(10, 0, 80, 10), QRectF(0, 10, 100, 40)};
        // (arriba-izq., arriba-der., abajo-izq., abajo-der.)
        QCOMPARE(cornerRadii(rects, QRectF(0, 0, 100, 50)), QVector4D(10, 10, 0, 0));
    }

    void squareCorners()
    {
        const QList<QRectF> rects{QRectF(0, 0, 100, 50)};
        QCOMPARE(cornerRadii(rects, rects[0]), QVector4D(0, 0, 0, 0));
    }

    void radiusIsAtMostHalfTheShortSide()
    {
        // ninguna franja toca los laterales: el radio máximo
        const QList<QRectF> rects{QRectF(10, 0, 80, 40)};
        QCOMPARE(cornerRadii(rects, QRectF(0, 0, 100, 40)), QVector4D(20, 20, 20, 20));
    }

    void separateCardsAreSeparatePieces()
    {
        // dos tarjetas del Centro de control, una al lado de la otra
        QList<QRectF> rects = roundedStrips(0, 0);
        const QList<QRectF> second = roundedStrips(120, 0);
        rects.append(second);
        std::stable_sort(rects.begin(), rects.end(), [](const QRectF &a, const QRectF &b) {
            return a.top() < b.top();
        });
        const auto result = pieces(rects);
        QCOMPARE(result.size(), 2);
        QCOMPARE(result[0].bounds, QRectF(0, 0, 100, 50));
        QCOMPARE(result[1].bounds, QRectF(120, 0, 100, 50));
        for (const auto &piece : result) {
            QCOMPARE(piece.rects.size(), 7);
            QCOMPARE(cornerRadii(piece.rects, piece.bounds), QVector4D(10, 10, 10, 10));
        }
    }

    void touchingRectsJoin()
    {
        // se tocan (o casi: hasta medio píxel) → una pieza; más lejos → dos
        QCOMPARE(pieces({QRectF(0, 0, 50, 50), QRectF(0, 50, 50, 50)}).size(), 1);
        QCOMPARE(pieces({QRectF(0, 0, 50, 50), QRectF(0, 50.4, 50, 50)}).size(), 1);
        QCOMPARE(pieces({QRectF(0, 0, 50, 50), QRectF(0, 52, 50, 50)}).size(), 2);
        QCOMPARE(pieces({QRectF(0, 0, 50, 50), QRectF(52, 0, 50, 50)}).size(), 2);
    }

    void laterRectJoinsEarlierPieces()
    {
        // dos rectángulos sueltos que un tercero, más abajo, une en una sola pieza
        const auto result = pieces({QRectF(0, 0, 10, 10), QRectF(20, 0, 10, 10), QRectF(0, 10, 30, 10)});
        QCOMPARE(result.size(), 1);
        QCOMPARE(result[0].bounds, QRectF(0, 0, 30, 20));
        QCOMPARE(result[0].rects.size(), 3);
    }

    void edgeBandIsARing()
    {
        const QList<QRectF> band = GoldenGlass::edgeBand(QRectF(10, 20, 100, 50), 4, 0);
        QCOMPARE(band,
                 (QList<QRectF>{QRectF(10, 20, 100, 4), QRectF(10, 66, 100, 4), QRectF(10, 24, 4, 42), QRectF(106, 24, 4, 42)}));
        // the four pieces cover the ring once
        qreal area = 0;
        for (const QRectF &rect : band) {
            area += rect.width() * rect.height();
        }
        QCOMPARE(area, 100.0 * 50 - 92.0 * 42);
    }

    void edgeBandReachesPastRoundedCorners()
    {
        // 45° on a corner of radius 14: the band 6 px deep ends 14·0.293 + 6·0.707 ≈ 8.3 px from both sides
        const QList<QRectF> band = GoldenGlass::edgeBand(QRectF(0, 0, 200, 60), 6, 14);
        QCOMPARE(band[0].height(), 9.0);
        QCOMPARE(band[2].width(), 9.0);
        // a deeper band than the corner bend keeps its depth (rounded up to whole pixels)
        QCOMPARE(GoldenGlass::edgeBand(QRectF(0, 0, 200, 60), 6.5, 2)[0].height(), 7.0);
    }

    void edgeBandOfASmallPieceIsThePiece()
    {
        const QRectF box(0, 0, 200, 16);
        QCOMPARE(GoldenGlass::edgeBand(box, 8, 4), QList<QRectF>{box});
    }
};

QTEST_GUILESS_MAIN(GlassGeometryTest)

#include "glassgeometry_test.moc"
