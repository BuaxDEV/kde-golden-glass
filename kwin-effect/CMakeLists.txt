# Efecto de KWin goldenglass_glass: fork del Blur de KWin 6.7 con refracción
# (ver docs/ARCHITECTURE.md 4.14 y UPSTREAM.md). Se compila contra las cabeceras
# de KWin instaladas y solo carga con la misma versión de KWin.
find_package(KWin 6.8 REQUIRED)
# el código de X11 del Blur original sigue compilado (KWin instalado lo activa)
find_package(XCB REQUIRED COMPONENTS XCB)

set(goldenglass_glass_SOURCES
    glass.cpp
    glass.qrc
    main.cpp
)
kconfig_add_kcfg_files(goldenglass_glass_SOURCES glassconfig.kcfgc)

add_library(goldenglass_glass MODULE ${goldenglass_glass_SOURCES})
target_link_libraries(goldenglass_glass PRIVATE
    KWin::kwin
    KF6::ConfigGui
    KDecoration3::KDecoration
    XCB::XCB
)
install(TARGETS goldenglass_glass DESTINATION ${KDE_INSTALL_PLUGINDIR}/kwin/effects/plugins)

# Pruebas de la geometría del vidrio (glassgeometry.h), sin KWin
if(BUILD_TESTING)
    include(ECMAddTests)
    find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED COMPONENTS Test Gui)
    ecm_add_test(tests/glassgeometry_test.cpp
        LINK_LIBRARIES Qt6::Test Qt6::Gui
        TEST_NAME glassgeometry_test)
    target_include_directories(glassgeometry_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
endif()
