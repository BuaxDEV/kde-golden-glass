add_library(goldenglasscommon${QT_MAJOR_VERSION} OBJECT goldenglassboxshadowrenderer.cpp goldenglasstrafficlight.cpp)

set_target_properties(goldenglasscommon${QT_MAJOR_VERSION} PROPERTIES POSITION_INDEPENDENT_CODE TRUE)

target_link_libraries(goldenglasscommon${QT_MAJOR_VERSION}
    PUBLIC
        Qt${QT_MAJOR_VERSION}::Core
        Qt${QT_MAJOR_VERSION}::Gui)
