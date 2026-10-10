### configuration plugin
add_definitions(-DTRANSLATION_DOMAIN=\"goldenglass_style_config\")
set(kstyle_goldenglass_config_PART_SRCS goldenglassstyleconfig.cpp)

set(kstyle_goldenglass_config_PART_SRCS ${kstyle_goldenglass_config_PART_SRCS} goldenglassstyleconfigmodule.cpp)

kconfig_add_kcfg_files(kstyle_goldenglass_config_PART_SRCS ../goldenglassstyleconfigdata.kcfgc)
set(kstyle_goldenglass_config_PART_FORMS ui/goldenglassstyleconfig.ui)
ki18n_wrap_ui(kstyle_goldenglass_config_PART_FORMS_HEADERS ${kstyle_goldenglass_config_PART_FORMS})

kcoreaddons_add_plugin(goldenglassstyleconfig SOURCES
    ${kstyle_goldenglass_config_PART_SRCS}
    ${kstyle_goldenglass_config_PART_FORMS_HEADERS}
    INSTALL_NAMESPACE "kstyle_config"
)

target_link_libraries(goldenglassstyleconfig Qt6::Core Qt6::Gui Qt6::Widgets Qt6::DBus)
target_link_libraries(goldenglassstyleconfig KF6::CoreAddons KF6::ConfigCore KF6::ConfigWidgets KF6::I18n)
target_link_libraries(goldenglassstyleconfig KF6::KCMUtils)
kcmutils_generate_desktop_file(goldenglassstyleconfig)

set(goldenglass_settings_SOURCES main.cpp)
add_executable(goldenglass-settings ${goldenglass_settings_SOURCES} )
target_link_libraries(goldenglass-settings Qt6::Core Qt6::Gui Qt6::Widgets )
target_link_libraries(goldenglass-settings KF6::I18n KF6::KCMUtils KF6::CoreAddons)

set_target_properties(goldenglass-settings PROPERTIES OUTPUT_NAME goldenglass-settings)

install(TARGETS goldenglass-settings ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})

# icon
ecm_install_icons(ICONS sc-apps-goldenglass-settings.svgz
    DESTINATION ${KDE_INSTALL_ICONDIR}
    THEME hicolor )


