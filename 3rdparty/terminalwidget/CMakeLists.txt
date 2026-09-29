# Vendored build script for the terminalwidget library.
# The sources under lib/ come from deepin-terminal (see VENDOR.md); this
# CMakeLists is a lean local replacement for the upstream one, which
# requires lxqt-build-tools. Differences: no lib translation handling,
# static-by-default, relocatable data-dir fallback (TERMWIDGET_RELOCATABLE_DATADIR).
#
# The target name matches the system library (terminalwidget<Qt major>) so
# the application links the same name in both modes.

include(GNUInstallDirs)
include(CheckFunctionExists)
include(GenerateExportHeader)

if(WIN32)
    # kpty is POSIX-only; bundling a Windows build needs the ConPTY port (roadmap M4).
    message(WARNING "terminalwidget: Windows support pending (ConPTY port, roadmap M4).")
endif()

set(TERMINALWIDGET_VERSION_MAJOR "0")
set(TERMINALWIDGET_VERSION_MINOR "14")
set(TERMINALWIDGET_VERSION_PATCH "1")

set(TERMINALWIDGET_LIBRARY_NAME terminalwidget${QT_VERSION_MAJOR})
# data lives under mudi's own name: on deepin the system share/terminalwidget6
# tree belongs to the deepin-terminal package, and shipping the same paths
# makes dpkg refuse the mudi package (file conflict, 0.4.1 vs deepin-terminal)
# absolute, for compile-time data-dir defines
set(TW_INSTALL_DATADIR "${CMAKE_INSTALL_FULL_DATADIR}/mudi/${TERMINALWIDGET_LIBRARY_NAME}")
# relative, for install DESTINATION (must honor cmake --install --prefix)
set(TW_INSTALL_DATADIR_REL "${CMAKE_INSTALL_DATADIR}/mudi/${TERMINALWIDGET_LIBRARY_NAME}")
# relative to the application directory, for relocatable/bundled layouts
set(TW_RELOCATABLE_DATADIR "../share/mudi/${TERMINALWIDGET_LIBRARY_NAME}")

option(TERMINALWIDGET_STATIC_BUILD "Build the vendored terminalwidget as a static library" ON)

find_package(PkgConfig REQUIRED)
# Encoding detection: uchardet is required; libchardet is optional
# (VENDOR: without it detectcode.cpp falls back to uchardet-only via
# TERMINALWIDGET_HAVE_CHARDET). macOS/homebrew ships no chardet formula.
option(TERMINALWIDGET_DISABLE_CHARDET "Skip libchardet even if found" OFF)
pkg_check_modules(CHARTDET chardet IMPORTED_TARGET)
pkg_check_modules(UCHARDET REQUIRED uchardet IMPORTED_TARGET)
set(TW_CHARDET_DEFINES "")
set(TW_CHARDET_LIBS "")
if(CHARTDET_FOUND AND NOT TERMINALWIDGET_DISABLE_CHARDET)
    list(APPEND TW_CHARDET_DEFINES TERMINALWIDGET_HAVE_CHARDET)
    list(APPEND TW_CHARDET_LIBS PkgConfig::CHARTDET)
endif()

check_function_exists(updwtmpx HAVE_UPDWTMPX)

set(TW_SOURCES
    lib/BlockArray.cpp
    lib/ColorScheme.cpp
    lib/CharacterFormat.cpp
    lib/Emulation.cpp
    lib/Filter.cpp
    lib/history/HistoryFile.cpp
    lib/history/HistoryScroll.cpp
    lib/history/HistoryScrollFile.cpp
    lib/history/HistoryScrollNone.cpp
    lib/history/HistoryType.cpp
    lib/history/HistoryTypeFile.cpp
    lib/history/HistoryTypeNone.cpp
    lib/history/compact/CompactHistoryScroll.cpp
    lib/history/compact/CompactHistoryType.cpp
    lib/HistorySearch.cpp
    lib/KeyboardTranslator.cpp
    lib/konsole_wcwidth.cpp
    lib/kprocess.cpp
    lib/kpty.cpp
    lib/kptydevice.cpp
    lib/kptyprocess.cpp
    lib/ProcessInfo.cpp
    lib/Pty.cpp
    lib/qtermwidget.cpp
    lib/Screen.cpp
    lib/ScreenWindow.cpp
    lib/SearchBar.cpp
    lib/Session.cpp
    lib/SessionManager.cpp
    lib/ShellCommand.cpp
    lib/TerminalCharacterDecoder.cpp
    lib/TerminalDisplay.cpp
    lib/tools.cpp
    lib/Vt102Emulation.cpp
    lib/EscapeSequenceUrlExtractor.cpp
    lib/encodes/detectcode.cpp
)

# headers carrying Q_OBJECT: listed so AUTOMOC picks them up deterministically
set(TW_HEADERS
    lib/Emulation.h
    lib/Filter.h
    lib/history/HistoryFile.h
    lib/history/HistoryScroll.h
    lib/history/HistoryScrollFile.h
    lib/history/HistoryScrollNone.h
    lib/history/HistoryType.h
    lib/history/HistoryTypeFile.h
    lib/history/HistoryTypeNone.h
    lib/history/compact/CompactHistoryScroll.h
    lib/history/compact/CompactHistoryType.h
    lib/HistorySearch.h
    lib/kprocess.h
    lib/kptydevice.h
    lib/kptyprocess.h
    lib/ProcessInfo.h
    lib/Pty.h
    lib/qtermwidget.h
    lib/ScreenWindow.h
    lib/SearchBar.h
    lib/Session.h
    lib/SessionManager.h
    lib/TerminalDisplay.h
    lib/Vt102Emulation.h
    lib/EscapeSequenceUrlExtractor.h
    lib/encodes/detectcode.h
)

if(QT_VERSION_MAJOR EQUAL 6)
    # self-contained: this subdirectory may configure before the root
    # project gets around to finding Core5Compat (QTextCodec/QRegExp live there)
    find_package(Qt6 REQUIRED COMPONENTS Core5Compat)
    list(APPEND TW_EXTRA_LIBS Qt6::Core5Compat)
endif()

if(TERMINALWIDGET_STATIC_BUILD)
    set(TW_LIB_TYPE STATIC)
else()
    set(TW_LIB_TYPE SHARED)
endif()

add_library(${TERMINALWIDGET_LIBRARY_NAME} ${TW_LIB_TYPE}
    ${TW_SOURCES} ${TW_HEADERS} lib/SearchBar.ui)

target_link_libraries(${TERMINALWIDGET_LIBRARY_NAME}
    PUBLIC
        Qt${QT_VERSION_MAJOR}::Widgets
        ${TW_EXTRA_LIBS}
        PkgConfig::ICU
        PkgConfig::UCHARDET
        ${TW_CHARDET_LIBS}
)
if(UNIX)
    target_link_libraries(${TERMINALWIDGET_LIBRARY_NAME} PRIVATE m)
endif()
# VENDOR: macOS keeps iconv out of libSystem; without this the final
# link of any consumer of the static library fails on _iconv_open
if(APPLE)
    target_link_libraries(${TERMINALWIDGET_LIBRARY_NAME} PUBLIC iconv)
endif()

target_compile_definitions(${TERMINALWIDGET_LIBRARY_NAME}
    PRIVATE
        "KB_LAYOUT_DIR=\"${TW_INSTALL_DATADIR}/kb-layouts\""
        "COLORSCHEMES_DIR=\"${TW_INSTALL_DATADIR}/color-schemes\""
        "TRANSLATIONS_DIR=\"${TW_INSTALL_DATADIR}/translations\""
        "TERMWIDGET_RELOCATABLE_DATADIR=\"${TW_RELOCATABLE_DATADIR}\""
        ${TW_CHARDET_DEFINES}
        "HAVE_POSIX_OPENPT"
        "HAVE_SYS_TIME_H"
        $<$<BOOL:${HAVE_UPDWTMPX}>:HAVE_UPDWTMPX>
)
if(APPLE)
    target_compile_definitions(${TERMINALWIDGET_LIBRARY_NAME} PRIVATE HAVE_UTMPX UTMPX_COMPAT)
endif()

generate_export_header(${TERMINALWIDGET_LIBRARY_NAME}
    EXPORT_FILE_NAME "${CMAKE_CURRENT_BINARY_DIR}/lib/qtermwidget_export.h"
    EXPORT_MACRO_NAME TERMINALWIDGET_EXPORT
    NO_EXPORT_MACRO_NAME TERMINALWIDGET_NO_EXPORT
    STATIC_DEFINE TERMINALWIDGET_STATIC_DEFINE
)
if(TERMINALWIDGET_STATIC_BUILD)
    # consumers include qtermwidget.h -> qtermwidget_export.h
    target_compile_definitions(${TERMINALWIDGET_LIBRARY_NAME} PUBLIC TERMINALWIDGET_STATIC_DEFINE)
endif()

target_include_directories(${TERMINALWIDGET_LIBRARY_NAME}
    PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/lib>"
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/lib>"
)

set_target_properties(${TERMINALWIDGET_LIBRARY_NAME} PROPERTIES
    VERSION "${TERMINALWIDGET_VERSION_MAJOR}.${TERMINALWIDGET_VERSION_MINOR}.${TERMINALWIDGET_VERSION_PATCH}"
    SOVERSION ${TERMINALWIDGET_VERSION_MAJOR}
)

# Data files for both the regular install prefix and the relocatable
# layout (they are the same paths: <prefix>/share/<libname>/...).
install(DIRECTORY lib/color-schemes/
    DESTINATION "${TW_INSTALL_DATADIR_REL}/color-schemes"
    FILES_MATCHING PATTERN "*.*schem*")
install(DIRECTORY lib/kb-layouts/
    DESTINATION "${TW_INSTALL_DATADIR_REL}/kb-layouts"
    FILES_MATCHING PATTERN "*.keytab")
if(NOT TERMINALWIDGET_STATIC_BUILD)
    install(TARGETS ${TERMINALWIDGET_LIBRARY_NAME}
        LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
        RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
endif()
