/*
 * Unit tests for DolphinViewOpacity configuration
 *
 * Tests the new DolphinViewOpacity setting that controls
 * transparency of Dolphin's main file view area.
 */

#include <QTest>
#include <QTemporaryDir>
#include <QStandardPaths>

#include "goldenglassstyleconfigdata.h"

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
    GoldenGlass::StyleConfigData::self()->setDefaults();
}

void DolphinViewOpacityTest::cleanup()
{
    // Nothing to clean up
}

void DolphinViewOpacityTest::testDefaultValue()
{
    // The default value should be 100 (fully opaque)
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 100);
}

void DolphinViewOpacityTest::testSetAndGetValue()
{
    // Test setting various valid values
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(50);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 50);

    GoldenGlass::StyleConfigData::setDolphinViewOpacity(0);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 0);

    GoldenGlass::StyleConfigData::setDolphinViewOpacity(75);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 75);

    GoldenGlass::StyleConfigData::setDolphinViewOpacity(100);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 100);
}

void DolphinViewOpacityTest::testBoundaryValues()
{
    // Test minimum value (0 = fully transparent)
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(0);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 0);

    // Test maximum value (100 = fully opaque)
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(100);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 100);

    // Test value at 1 (near minimum)
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(1);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 1);

    // Test value at 99 (near maximum)
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(99);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 99);
}

void DolphinViewOpacityTest::testPersistence()
{
    // Set a non-default value
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(42);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 42);

    // Save configuration
    GoldenGlass::StyleConfigData::self()->save();

    // Reset to defaults
    GoldenGlass::StyleConfigData::self()->setDefaults();
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 100);

    // Reload configuration
    GoldenGlass::StyleConfigData::self()->load();
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 42);
}

void DolphinViewOpacityTest::testIndependentFromSidebarOpacity()
{
    // Set different values for view and sidebar opacity
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(30);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(70);

    // Verify they are independent
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 30);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinSidebarOpacity(), 70);

    // Change one, verify the other is unaffected
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(50);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 50);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinSidebarOpacity(), 70);

    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(25);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 50);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinSidebarOpacity(), 25);
}

QTEST_MAIN(DolphinViewOpacityTest)
#include "dolphinviewopacity_test.moc"
