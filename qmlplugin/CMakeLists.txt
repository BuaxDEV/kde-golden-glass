# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Módulo QML org.goldenglass.glass: le pasa a KWin la región de blur de las
# piezas de vidrio de una ventana (p. ej. las tarjetas sueltas del Centro de
# control), que Plasma no deja hacer desde QML, y da al shell los ajustes de
# la barra de menús (MenuBarSettings).
include(ECMQmlModule)

# Fuentes y bibliotecas del módulo, una por línea (cada PR añade las suyas):
# las usan el plugin y la biblioteca estática de las pruebas (tests/).
set(GOLDENGLASS_QMLPLUGIN_SOURCES
    glassregion.cpp
    glassregion.h
    menubarsettings.cpp
    menubarsettings.h
)
set(GOLDENGLASS_QMLPLUGIN_LIBS
    Qt6::Quick
    KF6::WindowSystem
    KF6::ConfigCore
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
