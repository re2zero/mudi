Name:           mudi
Version:        @VERSION@
Release:        1
Summary:        Terminal workspace frontend for AI coding agents
License:        GPL-3.0-or-later
URL:            https://github.com/re2zero/mudi

%description
MuDi is a GUI frontend for the herdr terminal workspace manager for
AI coding agents. It provides workspace, tab and pane management,
desktop notifications with one-click agent focus, tray presence and
in-app updates. This is the plain Qt build (no DTK).

Library dependencies (Qt6, uchardet, ICU) are resolved automatically
from the linked binaries by rpmbuild.

%files
/usr/bin/mudi
/usr/share/applications/mudi.desktop
/usr/share/icons/hicolor/scalable/apps/mudi.svg
/usr/share/mudi/translations/
