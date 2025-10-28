// Portable shims for MSVC-specific APIs used in original sources
#pragma once

#if !defined(_MSC_VER)

#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdarg.h>
#include <stddef.h>
#include <algorithm>

// Map Microsoft-specific integer type to standard on non-MSVC
#ifndef _int64
#define _int64 long long
#endif

// Map Windows-specific macros to standard C++
#ifndef __min
#define __min(a,b) std::min(a,b)
#endif

// errno_t and fopen_s
typedef int errno_t;
static inline errno_t fopen_s(FILE **fp, const char *filename, const char *mode) {
  if (!fp) return EINVAL;
  *fp = fopen(filename, mode);
  return (*fp) ? 0 : errno;
}

// Helpers to safely get object size when available
#if defined(__GNUC__) || defined(__clang__)
#define __OBJ_SIZE(ptr) __builtin_object_size((ptr), 2)
#else
#define __OBJ_SIZE(ptr) ((size_t)-1)
#endif

// strcpy_s compatibility (supports 2-arg and 3-arg forms)
static inline void __strcpy_s3(char *dst, size_t dstsz, const char *src) {
  if (!dst || !src || dstsz == 0) return;
  strncpy(dst, src, dstsz - 1);
  dst[dstsz - 1] = '\0';
}
static inline void __strcpy_s2(char *dst, const char *src) {
  size_t n = __OBJ_SIZE(dst);
  if (n == (size_t)-1 || n == 0) {
    // Fallback if size unknown
    strcpy(dst, src);
  } else {
    __strcpy_s3(dst, n, src);
  }
}
#define __STRCPY_S_CHOOSER(_1,_2,_3,NAME,...) NAME
#define strcpy_s(...) __STRCPY_S_CHOOSER(__VA_ARGS__, __strcpy_s3, __strcpy_s2)(__VA_ARGS__)

// strcat_s compatibility (2-arg form in sources)
static inline void __strcat_s2(char *dst, const char *src) {
  size_t n = __OBJ_SIZE(dst);
  if (n == (size_t)-1 || n == 0) {
    strcat(dst, src);
  } else {
    size_t len = strlen(dst);
    if (len + 1 < n) {
      size_t space = n - len - 1;
      strncat(dst, src, space);
      dst[n - 1] = '\0';
    }
  }
}
#define strcat_s(d,s) __strcat_s2((d),(s))

// sprintf_s compatibility - simplified to avoid macro conflicts
#define sprintf_s(dst, ...) snprintf(dst, sizeof(dst), __VA_ARGS__)

#endif // !_MSC_VER
