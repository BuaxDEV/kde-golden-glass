################# includes #################
include_directories(
    animations
    debug
    ${CMAKE_SOURCE_DIR}/libgoldenglasscommon
    ${CMAKE_BINARY_DIR}/libgoldenglasscommon
)

################# configuration #################
configure_file(config-goldenglass.h.cmake ${CMAKE_CURRENT_BINARY_DIR}/config-goldenglass.h)

########### next target ###############
set(goldenglass_PART_SRCS
    animations/goldenglassanimation.cpp
    animations/goldenglassanimations.cpp
    animations/goldenglassanimationdata.cpp
    animations/goldenglassbaseengine.cpp
    animations/goldenglassbusyindicatordata.cpp
    animations/goldenglassbusyindicatorengine.cpp
    animations/goldenglassdialdata.cpp
    animations/goldenglassdialengine.cpp
    animations/goldenglassenabledata.cpp
    animations/goldenglassgenericdata.cpp
    animations/goldenglassheaderviewdata.cpp
    animations/goldenglassheaderviewengine.cpp
    animations/goldenglassscrollbardata.cpp
    animations/goldenglassscrollbarengine.cpp
    animations/goldenglassspinboxengine.cpp
    animations/goldenglassspinboxdata.cpp
    animations/goldenglassstackedwidgetdata.cpp
    animations/goldenglassstackedwidgetengine.cpp
    animations/goldenglasstabbarengine.cpp
    animations/goldenglasstabbardata.cpp
    animations/goldenglasstoolboxengine.cpp
    animations/goldenglasstransitiondata.cpp
    animations/goldenglasstransitionwidget.cpp
    animations/goldenglasswidgetstateengine.cpp
    animations/goldenglasswidgetstatedata.cpp
    debug/goldenglasswidgetexplorer.cpp
    goldenglassaddeventfilter.cpp
    goldenglassblurhelper.cpp
    goldenglassframeshadow.cpp
    goldenglasshelper.cpp
    goldenglassmdiwindowshadow.cpp
    goldenglassmnemonics.cpp
    goldenglasspropertynames.cpp
    goldenglassshadowhelper.cpp
    goldenglasssplitterproxy.cpp
    goldenglassstyle.cpp
    goldenglassstyleplugin.cpp
    goldenglasstileset.cpp
    goldenglasswindowmanager.cpp
    goldenglasstoolsareamanager.cpp
)

kconfig_add_kcfg_files(goldenglass_PART_SRCS ../kdecoration/goldenglasssettings.kcfgc)
kconfig_add_kcfg_files(goldenglass_PART_SRCS goldenglassstyleconfigdata.kcfgc)

add_library(goldenglass${QT_MAJOR_VERSION} MODULE ${goldenglass_PART_SRCS})

################# find Qt modules #################
if(QT_MAJOR_VERSION EQUAL 6)
    find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Quick QuickWidgets)
else()
    find_package(Qt5 REQUIRED COMPONENTS Core Gui Widgets Quick QuickWidgets)
endif()

################# link Qt libraries #################
target_link_libraries(goldenglass${QT_MAJOR_VERSION}
    PRIVATE
    Qt${QT_MAJOR_VERSION}::Core
    Qt${QT_MAJOR_VERSION}::Gui
    Qt${QT_MAJOR_VERSION}::Widgets
    Qt${QT_MAJOR_VERSION}::DBus
    Qt${QT_MAJOR_VERSION}::Quick
)

if( GOLDENGLASS_HAVE_QTQUICK )
    target_link_libraries(goldenglass${QT_MAJOR_VERSION}
        PRIVATE
            Qt${QT_MAJOR_VERSION}::QuickWidgets
            KF${QT_MAJOR_VERSION}::CoreAddons
    )
endif()

################# link KDE Frameworks #################
target_link_libraries(goldenglass${QT_MAJOR_VERSION}
    PRIVATE
    KF${QT_MAJOR_VERSION}::CoreAddons
    KF${QT_MAJOR_VERSION}::ConfigCore
    KF${QT_MAJOR_VERSION}::ConfigGui
    KF${QT_MAJOR_VERSION}::GuiAddons
    KF${QT_MAJOR_VERSION}::IconThemes
    KF${QT_MAJOR_VERSION}::WindowSystem
)

if(QT_MAJOR_VERSION STREQUAL "5")
    target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE KF5::ConfigWidgets)
    if(GOLDENGLASS_HAVE_QTQUICK)
        target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE KF5::Kirigami2)
    endif()
else()
    target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE KF6::ColorScheme)
    if(GOLDENGLASS_HAVE_QTQUICK)
        target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE KF6::KirigamiPlatform)
    endif()
endif()

################# link internal library #################
target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE goldenglasscommon${QT_MAJOR_VERSION})

################# KDE style integration #################
if(KF${QT_MAJOR_VERSION}FrameworkIntegration_FOUND)
    target_link_libraries(goldenglass${QT_MAJOR_VERSION} PRIVATE KF${QT_MAJOR_VERSION}::Style)
endif()

if (WIN32)
    # As stated in https://docs.microsoft.com/en-us/cpp/c-runtime-library/math-constants M_PI only gets defined
    # when if _USE_MATH_DEFINES is defined
    target_compile_definitions(goldenglass${QT_MAJOR_VERSION} PRIVATE _USE_MATH_DEFINES _BSD_SOURCE)
endif()


########### install files ###############
if (FOR_FLATPAK)
    set(LIB_TARGET ${QT_PLUGINS_DIR}/styles/)
else()
    set(LIB_TARGET ${KDE_INSTALL_QTPLUGINDIR}/styles/)
endif()
install(TARGETS goldenglass${QT_MAJOR_VERSION} DESTINATION ${LIB_TARGET})

if (NOT FOR_FLATPAK)
    install(FILES goldenglass.themerc  DESTINATION  ${KDE_INSTALL_DATADIR}/kstyle/themes)
endif()

########### subdirectories ###############

if (QT_MAJOR_VERSION EQUAL "6" AND TARGET "KF6::KCMUtils" AND NOT FOR_FLATPAK)
    add_subdirectory(config)
endif()

########### tests ###############
include(CTest)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()
