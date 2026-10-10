cmake_minimum_required(VERSION 3.16)

# Get version
file(READ "${CMAKE_SOURCE_DIR}/VERSION" VER_RAW)
string(STRIP ${VER_RAW} VER)

project(
    goldenglass
    DESCRIPTION "GoldenGlass widget style and window decoration for KDE Plasma"
    VERSION ${VER}
)

set(KF6_MIN_VERSION "6.10.0")
set(KDE_COMPILERSETTINGS_LEVEL "5.82")
set(QT_MIN_VERSION "6.7.0")

include(GenerateExportHeader)
include(FeatureSummary)

find_package(ECM ${KF6_MIN_VERSION} REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${ECM_MODULE_PATH}  ${CMAKE_SOURCE_DIR}/cmake)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(ECMInstallIcons)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(KDEClangFormat)

set(QT_NO_CREATE_VERSIONLESS_TARGETS ON)
set(QT_NO_CREATE_VERSIONLESS_FUNCTIONS ON)

set(QT_MAJOR_VERSION 6)
include(KDEInstallDirs6)
include(KDECMakeSettings)

option(WITH_DECORATIONS "Build GoldenGlass window decorations for KWin" ON)

find_package(Qt6 ${QT_MIN_VERSION} REQUIRED CONFIG COMPONENTS Widgets DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS
        CoreAddons
        ColorScheme
        Config
        GuiAddons
        I18n
        IconThemes
        WindowSystem)
find_package(KF6KCMUtils ${KF6_MIN_VERSION})
set_package_properties(KF6KCMUtils PROPERTIES
    TYPE REQUIRED
    DESCRIPTION "Helps create configuration modules"
    PURPOSE "KCMUtils used for the configuration modules or the decoration and Qt Style"
)

find_package(Qt6 ${QT_MIN_VERSION} OPTIONAL_COMPONENTS Quick)
    if(${Qt6Quick_FOUND})
        find_package(KF6KirigamiPlatform ${KF6_MIN_VERSION} REQUIRED)
    endif()

find_package(KF6FrameworkIntegration ${KF6_MIN_VERSION} CONFIG )
    set_package_properties(KF${QT_MAJOR_VERSION}FrameworkIntegration PROPERTIES
        DESCRIPTION "KF${QT_MAJOR_VERSION} Framework Integration"
        URL "https://projects.kde.org/projects/frameworks/frameworkintegration"
        TYPE OPTIONAL
        PURPOSE "Required to use KStyle convenience functionalities in style")

set(GOLDENGLASS_HAVE_KSTYLE ${KF6FrameworkIntegration_FOUND})
set(GOLDENGLASS_HAVE_QTQUICK ${Qt6Quick_FOUND})

add_library(Qt::Core ALIAS Qt6::Core)
add_library(Qt::Gui ALIAS Qt6::Gui)
add_library(Qt::OpenGL ALIAS Qt6::OpenGL)
add_library(Qt::Network ALIAS Qt6::Network)
if(Qt6_VERSION_MINOR GREATER 6)
    add_library(Qt::PlatformModuleInternal ALIAS Qt6::PlatformModuleInternal)
endif()

add_subdirectory(kstyle kstyle6)
add_subdirectory(libgoldenglasscommon libgoldenglasscommon6)

if(WITH_DECORATIONS)
    find_package(KDecoration3 REQUIRED)
    set(KDECORATION_VERSION ${KDecoration3_VERSION})
    set(KDECORATION_VERSION_MAJOR ${KDecoration3_VERSION_MAJOR})
    set(KDECORATION_VERSION_MINOR ${KDecoration3_VERSION_MINOR})
    set(KDECORATION_VERSION_PATCH ${KDecoration3_VERSION_PATCH})
    
    add_definitions(
        -DKDECORATION_VERSION_MAJOR=${KDECORATION_VERSION_MAJOR}
        -DKDECORATION_VERSION_MINOR=${KDECORATION_VERSION_MINOR}
        -DKDECORATION_VERSION_PATCH=${KDECORATION_VERSION_PATCH}
    )
    add_subdirectory(kdecoration)
endif()

ki18n_install(po)

# Cabecera de versión para el módulo de configuración del estilo.
include(ECMSetupVersion)
ecm_setup_version(${PROJECT_VERSION} VARIABLE_PREFIX GOLDENGLASS
                VERSION_HEADER "${CMAKE_CURRENT_BINARY_DIR}/kstyle6/config/goldenglassstyleversion.h"
)

unset(QUERY_EXECUTABLE CACHE)

# add clang-format target for all our real source files
file(GLOB_RECURSE ALL_CLANG_FORMAT_SOURCE_FILES *.cpp *.h)
kde_clang_format(${ALL_CLANG_FORMAT_SOURCE_FILES})

feature_summary(WHAT ALL INCLUDE_QUIET_PACKAGES FATAL_ON_MISSING_REQUIRED_PACKAGES)
