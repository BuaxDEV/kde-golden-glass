# Tests for GoldenGlass KStyle

include(ECMAddTests)

find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Test Widgets)

# Generate the config data for tests
kconfig_add_kcfg_files(test_config_SRCS ${CMAKE_CURRENT_SOURCE_DIR}/../goldenglassstyleconfigdata.kcfgc)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/..
    ${CMAKE_CURRENT_BINARY_DIR}/..
    ${CMAKE_CURRENT_BINARY_DIR}
)

# Test for DolphinViewOpacity configuration
ecm_add_test(
    dolphinviewopacity_test.cpp
    ${test_config_SRCS}
    LINK_LIBRARIES
        Qt${QT_MAJOR_VERSION}::Test
        Qt${QT_MAJOR_VERSION}::Widgets
        KF${QT_MAJOR_VERSION}::ConfigCore
        KF${QT_MAJOR_VERSION}::ConfigGui
    TEST_NAME
        dolphinviewopacity_test${QT_MAJOR_VERSION}
)

# Test for blur helper behavior (config and the blur helper itself)
ecm_add_test(
    blurhelper_test.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../goldenglassblurhelper.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../goldenglasspropertynames.cpp
    ${test_config_SRCS}
    LINK_LIBRARIES
        Qt${QT_MAJOR_VERSION}::Test
        Qt${QT_MAJOR_VERSION}::Widgets
        KF${QT_MAJOR_VERSION}::ConfigCore
        KF${QT_MAJOR_VERSION}::ConfigGui
        KF${QT_MAJOR_VERSION}::ColorScheme
        KF${QT_MAJOR_VERSION}::WindowSystem
    TEST_NAME
        blurhelper_test${QT_MAJOR_VERSION}
)

# Test for style configuration module
ecm_add_test(
    styleconfig_test.cpp
    ${test_config_SRCS}
    LINK_LIBRARIES
        Qt${QT_MAJOR_VERSION}::Test
        Qt${QT_MAJOR_VERSION}::Widgets
        KF${QT_MAJOR_VERSION}::ConfigCore
        KF${QT_MAJOR_VERSION}::ConfigGui
    TEST_NAME
        styleconfig_test${QT_MAJOR_VERSION}
)

# The style dialog with its real .ui (change tracking, defaults, reload)
ki18n_wrap_ui(styleconfigdialog_test_UI ${CMAKE_CURRENT_SOURCE_DIR}/../config/ui/goldenglassstyleconfig.ui)
ecm_add_test(
    styleconfigdialog_test.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../config/goldenglassstyleconfig.cpp
    ${styleconfigdialog_test_UI}
    ${test_config_SRCS}
    LINK_LIBRARIES
        Qt${QT_MAJOR_VERSION}::Test
        Qt${QT_MAJOR_VERSION}::Widgets
        Qt${QT_MAJOR_VERSION}::DBus
        KF${QT_MAJOR_VERSION}::ConfigCore
        KF${QT_MAJOR_VERSION}::ConfigGui
        KF${QT_MAJOR_VERSION}::ConfigWidgets
        KF${QT_MAJOR_VERSION}::I18n
    TEST_NAME
        styleconfigdialog_test${QT_MAJOR_VERSION}
)
target_include_directories(styleconfigdialog_test${QT_MAJOR_VERSION} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/../config ${CMAKE_BINARY_DIR}/kstyle6/config)
target_compile_definitions(styleconfigdialog_test${QT_MAJOR_VERSION} PRIVATE TRANSLATION_DOMAIN=\"goldenglass_style_config\")
