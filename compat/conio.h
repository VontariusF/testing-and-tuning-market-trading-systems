// Minimal conio.h shim for non-Windows builds
#pragma once

#ifdef _WIN32
#  include <conio.h>
#else
// Provide non-blocking keyboard stubs used by sources
static inline int _kbhit(void) { return 0; }
static inline int _getch(void) { return 0; }
#endif

