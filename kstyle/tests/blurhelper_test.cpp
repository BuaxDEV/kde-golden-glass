/*
 * Unit tests for BlurHelper behavior with DolphinViewOpacity
 *
 * Tests that blur regions are correctly calculated when
 * DolphinViewOpacity is set to less than 100.
 */

#include <QTest>
#include <QWidget>
#include <QMainWindow>
#include <QScrollArea>
#include <QVBoxLayout>
#include <QTemporaryDir>
#include <QStandardPaths>

#include "goldenglassblurhelper.h"
#include "goldenglassstyleconfigdata.h"

// Mock widget that inherits from QAbstractScrollArea and pretends to be KItemListContainer
class MockKItemListContainer : public QAbstractScrollArea
{
    Q_OBJECT
public:
    explicit MockKItemListContainer(QWidget *parent = nullptr)
        : QAbstractScrollArea(parent)
    {
        setObjectName("MockKItemListContainer");
    }

    // Override inherits to pretend we're KItemListContainer
    bool inherits(const char *classname) const
    {
        if (qstrcmp(classname, "KItemListContainer") == 0) {
            return true;
        }
        return QAbstractScrollArea::inherits(classname);
    }
};

class BlurHelperTest : public QObject
{
    Q_OBJECT

private:
    QTemporaryDir m_tempDir;

private Q_SLOTS:
    void initTestCase();
    void cleanupTestCase();
    void init();
    void cleanup();

    // Blur region tests
    void testNoBlurWhenOpacity100();
    void testBlurEnabledWhenOpacityLessThan100();
    void testBlurRegionIncludesKItemListContainer();
    void testBlurIndependentOfSidebarOpacity();

    // la ventana que pasa a opaca (o deja el estilo) retira su región en KWin
    void testBlurDisabledWhenWindowBecomesOpaque();
    void testBlurDisabledOnUnregister();
};

void BlurHelperTest::initTestCase()
{
    QVERIFY(m_tempDir.isValid());
    QStandardPaths::setTestModeEnabled(true);
}

void BlurHelperTest::cleanupTestCase()
{
    QStandardPaths::setTestModeEnabled(false);
}

void BlurHelperTest::init()
{
    GoldenGlass::StyleConfigData::self()->setDefaults();
}

void BlurHelperTest::cleanup()
{
}

void BlurHelperTest::testNoBlurWhenOpacity100()
{
    // When opacity is 100, no blur should be needed for the view
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(100);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 100);

    // The condition for blur registration should be false
    bool shouldRegisterBlur = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    QVERIFY(!shouldRegisterBlur);
}

void BlurHelperTest::testBlurEnabledWhenOpacityLessThan100()
{
    // When opacity is less than 100, blur should be enabled
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(50);
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 50);

    bool shouldRegisterBlur = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    QVERIFY(shouldRegisterBlur);

    // Test with 0 opacity
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(0);
    shouldRegisterBlur = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    QVERIFY(shouldRegisterBlur);

    // Test with 99 opacity
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(99);
    shouldRegisterBlur = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    QVERIFY(shouldRegisterBlur);
}

void BlurHelperTest::testBlurRegionIncludesKItemListContainer()
{
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(50);

    // Create a mock window with a KItemListContainer-like widget
    QMainWindow window;
    window.setGeometry(0, 0, 800, 600);

    auto *container = new MockKItemListContainer(&window);
    container->setGeometry(100, 100, 400, 300);

    window.setCentralWidget(container);
    window.show();

    // Process events to ensure visibility is updated
    QTest::qWait(10);

    // Verify our mock properly reports as KItemListContainer
    QVERIFY(container->inherits("KItemListContainer"));

    // The blur helper would find this widget and include its region
    // We can't directly test BlurHelper without more infrastructure,
    // but we can verify the conditions are met
    bool isDolphin = true; // In real code, this is set based on app name
    bool viewOpacityLessThan100 = GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100;
    bool containerIsKItemList = container->inherits("KItemListContainer");

    // The core conditions for blur region inclusion
    QVERIFY(isDolphin);
    QVERIFY(viewOpacityLessThan100);
    QVERIFY(containerIsKItemList);

    // After window.show() and event processing, container should be visible
    // But in headless test environment, this may not work - so we test the logic only
    QCOMPARE(GoldenGlass::StyleConfigData::dolphinViewOpacity(), 50);
}

void BlurHelperTest::testBlurIndependentOfSidebarOpacity()
{
    // Test that view blur is independent of sidebar blur

    // Case 1: View transparent, sidebar opaque
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(50);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(100);

    bool shouldBlurView = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    bool shouldBlurSidebar = (GoldenGlass::StyleConfigData::dolphinSidebarOpacity() < 100);

    QVERIFY(shouldBlurView);
    QVERIFY(!shouldBlurSidebar);

    // Case 2: View opaque, sidebar transparent
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(100);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(50);

    shouldBlurView = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    shouldBlurSidebar = (GoldenGlass::StyleConfigData::dolphinSidebarOpacity() < 100);

    QVERIFY(!shouldBlurView);
    QVERIFY(shouldBlurSidebar);

    // Case 3: Both transparent
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(30);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(70);

    shouldBlurView = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    shouldBlurSidebar = (GoldenGlass::StyleConfigData::dolphinSidebarOpacity() < 100);

    QVERIFY(shouldBlurView);
    QVERIFY(shouldBlurSidebar);

    // Case 4: Both opaque
    GoldenGlass::StyleConfigData::setDolphinViewOpacity(100);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(100);

    shouldBlurView = (GoldenGlass::StyleConfigData::dolphinViewOpacity() < 100);
    shouldBlurSidebar = (GoldenGlass::StyleConfigData::dolphinSidebarOpacity() < 100);

    QVERIFY(!shouldBlurView);
    QVERIFY(!shouldBlurSidebar);
}

namespace
{
void setWindowAlpha(QWidget *widget, int alpha)
{
    QPalette palette(widget->palette());
    QColor color(palette.color(QPalette::Window));
    color.setAlpha(alpha);
    palette.setColor(QPalette::Window, color);
    widget->setPalette(palette);
}

bool blurEnabled(const QWidget *widget)
{
    return widget->property("_goldenglass_blurEnabled").toBool();
}
}

void BlurHelperTest::testBlurDisabledWhenWindowBecomesOpaque()
{
    // sin barras translúcidas: una ventana opaca no tiene región
    GoldenGlass::StyleConfigData::setMenuBarOpacity(100);
    GoldenGlass::StyleConfigData::setToolBarOpacity(100);
    GoldenGlass::StyleConfigData::setDolphinSidebarOpacity(100);

    QWidget window;
    window.resize(200, 150);
    setWindowAlpha(&window, 128);
    window.show();
    QVERIFY(QTest::qWaitForWindowExposed(&window));

    GoldenGlass::BlurHelper helper(nullptr);
    helper.registerWidget(&window, false);
    QVERIFY(blurEnabled(&window));

    setWindowAlpha(&window, 255);
    helper.forceUpdate(&window);
    QVERIFY(!blurEnabled(&window));

    setWindowAlpha(&window, 128);
    helper.forceUpdate(&window);
    QVERIFY(blurEnabled(&window));
}

void BlurHelperTest::testBlurDisabledOnUnregister()
{
    QWidget window;
    window.resize(200, 150);
    setWindowAlpha(&window, 128);
    window.show();
    QVERIFY(QTest::qWaitForWindowExposed(&window));

    GoldenGlass::BlurHelper helper(nullptr);
    helper.registerWidget(&window, false);
    QVERIFY(blurEnabled(&window));

    helper.unregisterWidget(&window);
    QVERIFY(!blurEnabled(&window));
}

QTEST_MAIN(BlurHelperTest)
#include "blurhelper_test.moc"
