#####  config classes ææææææ

set(goldenglassdecoration_config_SRCS
  ../goldenglassexceptionlist.cpp
    goldenglassconfigwidget.cpp
    goldenglassexceptiondialog.cpp
    goldenglassexceptionlistwidget.cpp
    goldenglassexceptionmodel.cpp
    goldenglassitemmodel.cpp
)
ki18n_wrap_ui(goldenglassdecoration_config_SRCS
    ui/goldenglassconfigurationui.ui
    ui/goldenglassexceptiondialog.ui
    ui/goldenglassexceptionlistwidget.ui
)

kcoreaddons_add_plugin(kcm_goldenglassdecoration SOURCES kcm_goldenglassdecoration.cpp ${goldenglassdecoration_config_SRCS} INSTALL_NAMESPACE "${KDECORATION_KCM_PLUGIN_DIR}")
kconfig_add_kcfg_files(kcm_goldenglassdecoration ../goldenglasssettings.kcfgc)
target_include_directories(kcm_goldenglassdecoration PRIVATE ${CMAKE_SOURCE_DIR}/kdecoration ${CMAKE_BINARY_DIR}/kdecoration/)
target_link_libraries(kcm_goldenglassdecoration
     PUBLIC
        Qt6::Core
        Qt6::Gui
        Qt6::DBus
        KDecoration3::KDecoration
     PRIVATE
        KF6::CoreAddons
        KF6::ConfigWidgets
        KF6::GuiAddons
        KF6::I18n
        KF6::IconThemes
        KF6::WindowSystem
        KF6::KCMUtils
)
kcmutils_generate_desktop_file(kcm_goldenglassdecoration)
