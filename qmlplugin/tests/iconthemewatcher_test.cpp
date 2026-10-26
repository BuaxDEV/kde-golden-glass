/*
    SPDX-FileCopyrightText: 2026 GoldenGlass contributors
    SPDX-License-Identifier: GPL-3.0-or-later
*/

// IconThemeWatcher: one revision per icon theme switch of KIconLoader (no bus).

#include "iconthemewatcher.h"

#include "testbus.h"

#include <KIconLoader>

#include <QSignalSpy>

class IconThemeWatcherTest : public QObject
{
    Q_OBJECT
private Q_SLOTS:
    void startsAtZero()
    {
        IconThemeWatcher watcher;
        QCOMPARE(watcher.revision(), 0);
    }

    void oneSwitchCountsOnce()
    {
        IconThemeWatcher watcher;
        QSignalSpy changed(&watcher, &IconThemeWatcher::revisionChanged);
        // what plasma-changeicons makes KIconLoader emit: every group
        for (int group = KIconLoader::FirstGroup; group < KIconLoader::LastGroup; ++group) {
            Q_EMIT KIconLoader::global()->iconChanged(group);
        }
        QVERIFY(changed.wait());
        QTest::qWait(200);
        QCOMPARE(changed.count(), 1);
        QCOMPARE(watcher.revision(), 1);
    }

    void everySwitchCounts()
    {
        IconThemeWatcher watcher;
        QSignalSpy changed(&watcher, &IconThemeWatcher::revisionChanged);
        Q_EMIT KIconLoader::global()->iconChanged(KIconLoader::Desktop);
        QVERIFY(changed.wait());
        Q_EMIT KIconLoader::global()->iconChanged(KIconLoader::Desktop);
        QVERIFY(changed.wait());
        QCOMPARE(watcher.revision(), 2);
    }
};

GOLDENGLASS_TEST_MAIN(IconThemeWatcherTest)
#include "iconthemewatcher_test.moc"
