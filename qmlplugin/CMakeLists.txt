# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# QML module org.goldenglass.glass: hands KWin the blur region of the glass
# pieces of a window (e.g. the Control Center's loose cards), which Plasma does
# not allow from QML; gives the shell the menu bar settings (MenuBarSettings),
# Plasma the accessibility ones (AccessibilitySettings) and the Dock the apps
# that systemd runs (AppUnits).
include(ECMQmlModule)

# Sources and libraries of the module, one per line (each PR appends its own):
# the plugin and the static library of the tests (tests/) use them.
set(GOLDENGLASS_QMLPLUGIN_SOURCES
    glassregion.cpp
    glassregion.h
    menubarsettings.cpp
    menubarsettings.h
    accessibilitysettings.cpp
    accessibilitysettings.h
    unitname.cpp
    unitname.h
    appunitsbackend.cpp
    appunitsbackend.h
    appunits.cpp
    appunits.h
)
set(GOLDENGLASS_QMLPLUGIN_LIBS
    Qt6::Quick
    KF6::WindowSystem
    KF6::ConfigCore
    Qt6::DBus
)

ecm_add_qml_module(goldenglassglassplugin
    URI org.goldenglass.glass
    GENERATE_PLUGIN_SOURCE
)

target_sources(goldenglassglassplugin PRIVATE ${GOLDENGLASS_QMLPLUGIN_SOURCES})
# goldenglassroundedregion.h (solo cabecera, compartida con el estilo)
target_include_directories(goldenglassglassplugin PRIVATE ${CMAKE_SOURCE_DIR}/libgoldenglasscommon)

target_link_libraries(goldenglassglassplugin PRIVATE ${GOLDENGLASS_QMLPLUGIN_LIBS})

ecm_finalize_qml_module(goldenglassglassplugin DESTINATION ${KDE_INSTALL_QMLDIR})

# Pruebas del módulo (ctest): ver tests/CMakeLists.txt
include(CTest)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()
