add_definitions(-DTRANSLATION_DOMAIN="goldenglass_kwin_deco")

################# configuration #################
configure_file(config-goldenglass.h.cmake ${CMAKE_CURRENT_BINARY_DIR}/config-goldenglass.h )

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
add_library(goldenglassdecoration MODULE
    ${goldenglassdecoration_SRCS}
    ${goldenglassdecoration_config_SRCS}
    ${goldenglassdecoration_config_PART_FORMS_HEADERS})

set_target_properties(goldenglassdecoration PROPERTIES
    OUTPUT_NAME org.goldenglass.decoration
)

target_link_libraries(goldenglassdecoration
     PRIVATE
        goldenglasscommon6
        KF6::CoreAddons
        KF6::ConfigWidgets
        KF6::GuiAddons
        KF6::I18n
        KF6::IconThemes
        KF6::WindowSystem
        KF6::KCMUtils
        Qt6::DBus
        KDecoration3::KDecoration
)
install(TARGETS goldenglassdecoration DESTINATION ${KDE_INSTALL_PLUGINDIR}/${KDECORATION_PLUGIN_DIR})
install(FILES config/goldenglassdecorationconfig.desktop DESTINATION  ${KDE_INSTALL_DATADIR}/kservices6)
add_subdirectory(config)

# Vista previa de los semáforos (desarrollo; no se instala).
if(BUILD_TESTING)
    add_executable(trafficlight_preview tests/trafficlight_preview.cpp ${CMAKE_SOURCE_DIR}/libgoldenglasscommon/goldenglasstrafficlight.cpp)
    target_link_libraries(trafficlight_preview Qt6::Gui)
endif()
