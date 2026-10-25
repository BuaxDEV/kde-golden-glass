add_definitions(-DTRANSLATION_DOMAIN="goldenglass_kwin_deco")

################# includes #################
include_directories(${CMAKE_SOURCE_DIR}/libgoldenglasscommon)
include_directories(${CMAKE_BINARY_DIR}/libgoldenglasscommon)

################# newt target #################
### plugin classes
set(goldenglassdecoration_SRCS
    goldenglassbutton.cpp
    goldenglassdecoration.cpp
    goldenglassexceptionlist.cpp
    goldenglasssettingsprovider.cpp
)
### build library
kconfig_add_kcfg_files(goldenglassdecoration_SRCS goldenglasssettings.kcfgc)
add_library(goldenglassdecoration MODULE ${goldenglassdecoration_SRCS})

set_target_properties(goldenglassdecoration PROPERTIES
    OUTPUT_NAME org.goldenglass.decoration
)

target_link_libraries(goldenglassdecoration
     PRIVATE
        goldenglasscommon6
        KF6::ColorScheme
        KF6::ConfigGui
        KF6::CoreAddons
        KF6::GuiAddons
        KF6::IconThemes
        KDecoration3::KDecoration
)
install(TARGETS goldenglassdecoration DESTINATION ${KDE_INSTALL_PLUGINDIR}/${KDECORATION_PLUGIN_DIR})
add_subdirectory(config)

# Vista previa de los semáforos (desarrollo; no se instala).
if(BUILD_TESTING)
    add_executable(trafficlight_preview tests/trafficlight_preview.cpp ${CMAKE_SOURCE_DIR}/libgoldenglasscommon/goldenglasstrafficlight.cpp)
    target_link_libraries(trafficlight_preview Qt6::Gui)
endif()
