/*
 * Unit tests for DolphinViewOpacity configuration
 *
 * Tests the new DolphinViewOpacity setting that controls
 * transparency of Dolphin's main file view area.
 */

#include <QTest>
#include <QTemporaryDir>
#include <QStandardPaths>

#include "darklystyleconfigdata.h"

class DolphinViewOpacityTest : public QObject
{
    Q_OBJECT

private:
    QTemporaryDir m_tempDir;

private Q_SLOTS:
    void initTestCase();
    void cleanupTestCase();
    void init();
    void cleanup();

    // Configuration tests
    void testDefaultValue();
    void testSetAndGetValue();
    void testBoundaryValues();
    void testPersistence();
    void testIndependentFromSidebarOpacity();
};

void DolphinViewOpacityTest::initTestCase()
{
    // Use temporary directory for config files
    QVERIFY(m_tempDir.isValid());
    QStandardPaths::setTestModeEnabled(true);
}

void DolphinViewOpacityTest::cleanupTestCase()
{
    QStandardPaths::setTestModeEnabled(false);
}

void DolphinViewOpacityTest::init()
{
    // Reset to defaults before each test
    Darkly::StyleConfigData::self()->setDefaults();
}

void DolphinViewOpacityTest::cleanup()
{
    // Nothing to clean up
}

void DolphinViewOpacityTest::testDefaultValue()
{
    // The default value should be 100 (fully opaque)
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 100);
}

void DolphinViewOpacityTest::testSetAndGetValue()
{
    // Test setting various valid values
    Darkly::StyleConfigData::setDolphinViewOpacity(50);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 50);

    Darkly::StyleConfigData::setDolphinViewOpacity(0);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 0);

    Darkly::StyleConfigData::setDolphinViewOpacity(75);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 75);

    Darkly::StyleConfigData::setDolphinViewOpacity(100);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 100);
}

void DolphinViewOpacityTest::testBoundaryValues()
{
    // Test minimum value (0 = fully transparent)
    Darkly::StyleConfigData::setDolphinViewOpacity(0);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 0);

    // Test maximum value (100 = fully opaque)
    Darkly::StyleConfigData::setDolphinViewOpacity(100);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 100);

    // Test value at 1 (near minimum)
    Darkly::StyleConfigData::setDolphinViewOpacity(1);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 1);

    // Test value at 99 (near maximum)
    Darkly::StyleConfigData::setDolphinViewOpacity(99);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 99);
}

void DolphinViewOpacityTest::testPersistence()
{
    // Set a non-default value
    Darkly::StyleConfigData::setDolphinViewOpacity(42);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 42);

    // Save configuration
    Darkly::StyleConfigData::self()->save();

    // Reset to defaults
    Darkly::StyleConfigData::self()->setDefaults();
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 100);

    // Reload configuration
    Darkly::StyleConfigData::self()->load();
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 42);
}

void DolphinViewOpacityTest::testIndependentFromSidebarOpacity()
{
    // Set different values for view and sidebar opacity
    Darkly::StyleConfigData::setDolphinViewOpacity(30);
    Darkly::StyleConfigData::setDolphinSidebarOpacity(70);

    // Verify they are independent
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 30);
    QCOMPARE(Darkly::StyleConfigData::dolphinSidebarOpacity(), 70);

    // Change one, verify the other is unaffected
    Darkly::StyleConfigData::setDolphinViewOpacity(50);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 50);
    QCOMPARE(Darkly::StyleConfigData::dolphinSidebarOpacity(), 70);

    Darkly::StyleConfigData::setDolphinSidebarOpacity(25);
    QCOMPARE(Darkly::StyleConfigData::dolphinViewOpacity(), 50);
    QCOMPARE(Darkly::StyleConfigData::dolphinSidebarOpacity(), 25);
}

QTEST_MAIN(DolphinViewOpacityTest)
#include "dolphinviewopacity_test.moc"
