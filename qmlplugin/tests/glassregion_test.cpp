/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// GlassRegion: the glass pieces it finds and how clipping ancestors cut them.

#include "glassregion.h"

#include "testbus.h"

#include <QQuickItem>

#include <memory>

namespace
{
QQuickItem *addItem(QQuickItem *parent, const QRectF &geometry, bool clip = false)
{
    auto *item = new QQuickItem(parent);
    item->setPosition(geometry.topLeft());
    item->setSize(geometry.size());
    item->setClip(clip);
    return item;
}

// Square corners keep the expected regions plain rectangles
QQuickItem *addTile(QQuickItem *parent, const QRectF &geometry, qreal radius = 0)
{
    QQuickItem *tile = addItem(parent, geometry);
    tile->setProperty("goldenGlassTile", true);
    tile->setProperty("radius", radius);
    return tile;
}

QRegion regionOf(QQuickItem *source)
{
    GlassRegion glass;
    glass.setSource(source);
    return glass.collectRegion();
}
}

class GlassRegionTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void collectsEachTile()
    {
        auto root = std::make_unique<QQuickItem>();
        root->setSize({400, 400});
        addTile(root.get(), {10, 10, 50, 40});
        QQuickItem *group = addItem(root.get(), {100, 100, 200, 200});
        addTile(group, {20, 30, 60, 60});

        QCOMPARE(regionOf(root.get()), QRegion(10, 10, 50, 40) + QRegion(120, 130, 60, 60));
    }

    void skipsHiddenTiles()
    {
        auto root = std::make_unique<QQuickItem>();
        addTile(root.get(), {0, 0, 50, 50})->setVisible(false);
        addTile(root.get(), {60, 0, 50, 50})->setOpacity(0);

        QVERIFY(regionOf(root.get()).isEmpty());
    }

    void roundsTheCorners()
    {
        auto root = std::make_unique<QQuickItem>();
        addTile(root.get(), {0, 0, 100, 100}, 20);

        const QRegion region = regionOf(root.get());
        QCOMPARE(region.boundingRect(), QRect(0, 0, 100, 100));
        QVERIFY(!region.contains(QPoint(0, 0)));
        QVERIFY(region.contains(QPoint(50, 50)));
    }

    void clipCutsTilesOutsideTheView()
    {
        // a scrolled list: the viewport clips, its content moved up by 60
        auto root = std::make_unique<QQuickItem>();
        QQuickItem *viewport = addItem(root.get(), {0, 100, 200, 100}, true);
        QQuickItem *content = addItem(viewport, {0, -60, 200, 400});
        addTile(content, {0, 0, 200, 50}); // scrolled out above
        addTile(content, {0, 50, 200, 50}); // half visible
        addTile(content, {0, 100, 200, 50}); // fully visible
        addTile(content, {0, 200, 200, 50}); // below the view

        QCOMPARE(regionOf(root.get()), QRegion(0, 100, 200, 40) + QRegion(0, 140, 200, 50));
    }

    void nestedClipsIntersect()
    {
        auto root = std::make_unique<QQuickItem>();
        QQuickItem *outer = addItem(root.get(), {0, 0, 100, 100}, true);
        QQuickItem *inner = addItem(outer, {50, 50, 100, 100}, true);
        addTile(inner, {-50, -50, 200, 200});

        QCOMPARE(regionOf(root.get()), QRegion(50, 50, 50, 50));
    }

    void tileClipDoesNotCutItself()
    {
        auto root = std::make_unique<QQuickItem>();
        addTile(root.get(), {10, 10, 80, 80})->setClip(true);

        QCOMPARE(regionOf(root.get()), QRegion(10, 10, 80, 80));
    }

    void unclippedSiblingsKeepTheirTiles()
    {
        auto root = std::make_unique<QQuickItem>();
        QQuickItem *clipped = addItem(root.get(), {0, 0, 50, 50}, true);
        addTile(clipped, {0, 0, 100, 100});
        QQuickItem *free = addItem(root.get(), {0, 0, 50, 50});
        addTile(free, {0, 100, 100, 100});

        QCOMPARE(regionOf(root.get()), QRegion(0, 0, 50, 50) + QRegion(0, 100, 100, 100));
    }

    void emptyClipSkipsTheSubtree()
    {
        auto root = std::make_unique<QQuickItem>();
        QQuickItem *collapsed = addItem(root.get(), {0, 0, 0, 0}, true);
        addTile(collapsed, {0, 0, 100, 100});

        QVERIFY(regionOf(root.get()).isEmpty());
    }
};

GOLDENGLASS_TEST_MAIN(GlassRegionTest)
#include "glassregion_test.moc"
