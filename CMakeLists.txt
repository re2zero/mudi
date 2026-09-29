cmake_minimum_required(VERSION 3.16)
project(mudi LANGUAGES CXX)

# Default version, overridden by debian/rules via -DAPP_VERSION
if(NOT DEFINED APP_VERSION)
    set(APP_VERSION "0.4.4")
endif()
message(STATUS "   >>> Version: ${APP_VERSION}")

configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/version.h.in
    ${CMAKE_CURRENT_BINARY_DIR}/version.h
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Use QT_DIR hint from debian/rules for explicit Qt version control
if(DEFINED QT_DIR)
    list(APPEND CMAKE_PREFIX_PATH "${QT_DIR}")
endif()

# Prefer Qt6 explicitly: the generic "NAMES Qt6 Qt5" scan can settle on
# Qt5 on distros where both stacks are installed (deepin ships both).
find_package(Qt6 COMPONENTS Core QUIET)
if(Qt6_FOUND)
    set(QT_VERSION_MAJOR 6)
else()
    find_package(QT NAMES Qt5 REQUIRED COMPONENTS Core)
endif()
message(STATUS "   >>> Found Qt version: ${QT_VERSION_MAJOR}")

if(NOT DEFINED ENV{QT_SELECT})
    set(ENV{QT_SELECT} "qt${QT_VERSION_MAJOR}")
endif()
message(STATUS "   >>> Build with Qt version: $ENV{QT_SELECT}")

# DTK is optional: the runtime only uses it on deepin/UOS (Platform::useDtk).
# Builds for other distros/OSes work without DTK dev packages.
option(DISABLE_DTK "Skip DTK support even if found (generic Qt UI only)" OFF)
set(HAVE_DTK 0)
set(DTK_LINK_TARGETS "")
if(UNIX AND NOT APPLE AND NOT DISABLE_DTK)
    if(QT_VERSION_MAJOR EQUAL 6)
        find_package(Dtk6 COMPONENTS Core Widget QUIET)
        if(Dtk6_FOUND)
            set(HAVE_DTK 1)
            set(DTK_LINK_TARGETS Dtk6::Core Dtk6::Widget)
        endif()
    else()
        find_package(Dtk COMPONENTS Core Widget QUIET)
        if(Dtk_FOUND)
            set(HAVE_DTK 1)
            set(DTK_LINK_TARGETS Dtk::Core Dtk::Widget)
        endif()
    endif()
endif()
message(STATUS "   >>> DTK support: ${HAVE_DTK}")

find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Core Gui Widgets Network DBus LinguistTools)

find_package(PkgConfig REQUIRED)
pkg_check_modules(ICU REQUIRED icu-i18n icu-uc IMPORTED_TARGET)

# terminalwidget: link the system library (provided by deepin-terminal) on
# deepin, or build the vendored copy under 3rdparty/terminalwidget. Bundled
# builds for other platforms must use the vendored copy — there is no
# system terminalwidget on Windows/macOS.
set(USE_SYSTEM_TERMINALWIDGET_DEFAULT ON)
if(WIN32 OR APPLE)
    set(USE_SYSTEM_TERMINALWIDGET_DEFAULT OFF)
else()
    # only deepin provides the system library; generic distros build the
    # vendored copy
    find_library(TERMINALWIDGET_SYSTEM_LIB terminalwidget${QT_VERSION_MAJOR})
    if(NOT TERMINALWIDGET_SYSTEM_LIB)
        set(USE_SYSTEM_TERMINALWIDGET_DEFAULT OFF)
    endif()
endif()
option(USE_SYSTEM_TERMINALWIDGET
    "Link the system terminalwidget instead of the vendored one"
    ${USE_SYSTEM_TERMINALWIDGET_DEFAULT})
message(STATUS "   >>> terminalwidget source: system=${USE_SYSTEM_TERMINALWIDGET}")
if(NOT USE_SYSTEM_TERMINALWIDGET)
    add_subdirectory(3rdparty/terminalwidget)
endif()

set(SOURCES
    src/main.cpp
    src/mainwindow.cpp
    src/appcore.cpp
    src/platform.cpp
    src/settingsdialog.cpp
    src/settingsstyle.cpp
    src/updatebanner.cpp
    src/updater.cpp
    src/agentmonitor.cpp
    src/tray.cpp
)

set(HEADERS
    src/mainwindow.h
    src/appcore.h
    src/platform.h
    src/settingsdialog.h
    src/settingsstyle.h
    src/updatebanner.h
    src/updater.h
    src/agentmonitor.h
    src/tray.h
)

# embedded logo: tray icon fallback when the hicolor theme icon is not
# installed (running from a build tree)
set(RESOURCES
    src/assets/assets.qrc
)

set(TRANSLATION_FILES
    translations/mudi.ts
    translations/mudi_zh_CN.ts
)

foreach(ts_file ${TRANSLATION_FILES})
    qt_add_translation(QM_FILES ${ts_file})
endforeach()

add_executable(mudi ${SOURCES} ${HEADERS} ${RESOURCES} ${QM_FILES})

target_compile_definitions(mudi PRIVATE HAVE_DTK=${HAVE_DTK})

target_include_directories(mudi PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/terminalwidget/lib
    # committed qtermwidget_export.h, used when linking the system library
    ${CMAKE_CURRENT_SOURCE_DIR}/3rdparty/terminalwidget
    ${CMAKE_CURRENT_BINARY_DIR}
)

if(QT_VERSION_MAJOR EQUAL 6)
    find_package(Qt6 REQUIRED COMPONENTS Core5Compat)
    list(APPEND QT_EXTRA_LIBS Qt6::Core5Compat)
endif()

target_link_libraries(mudi PRIVATE
    Qt${QT_VERSION_MAJOR}::Core
    Qt${QT_VERSION_MAJOR}::Gui
    Qt${QT_VERSION_MAJOR}::Widgets
    Qt${QT_VERSION_MAJOR}::Network
    Qt${QT_VERSION_MAJOR}::DBus
    ${QT_EXTRA_LIBS}
    ${DTK_LINK_TARGETS}
    terminalwidget${QT_VERSION_MAJOR}
    PkgConfig::ICU
)

install(TARGETS mudi DESTINATION bin)
install(FILES src/assets/mudi.desktop DESTINATION share/applications)
install(FILES src/assets/mudi.svg DESTINATION share/icons/hicolor/scalable/apps)
install(FILES ${QM_FILES} DESTINATION share/mudi/translations)
