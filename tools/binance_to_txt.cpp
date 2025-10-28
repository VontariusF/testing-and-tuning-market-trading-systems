#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <ctime>

// Convert Binance Futures kline CSV to algorithm input
// Supports two outputs:
//  - OHLC rows:  YYYYMMDD Open High Low Close
//  - Close-only: YYYYMMDD Close
// Usage:
//   binance_to_txt [--close-only] input.csv output.txt
// Accepts first columns as either:
//   1) epoch_ms,open,high,low,close,...
//   2) YYYY-MM-DD HH:MM:SS,open,high,low,close,...
// Lines starting with non-digit or with headers are skipped.

static bool parse_epoch_ms_to_yyyymmdd(const char* s, int* out_date) {
  // parse up to 13 digits
  const char* p = s;
  long long ms = 0;
  int digits = 0;
  while (*p >= '0' && *p <= '9' && digits < 16) { ms = ms*10 + (*p - '0'); ++p; ++digits; }
  if (digits < 10) return false;
  time_t secs = (time_t)(ms / 1000);
  struct tm t; memset(&t, 0, sizeof(t));
  if (!gmtime_r(&secs, &t)) return false;
  *out_date = (t.tm_year + 1900) * 10000 + (t.tm_mon + 1) * 100 + t.tm_mday;
  return true;
}

static bool parse_iso_to_yyyymmdd(const char* s, int* out_date) {
  // Expect: YYYY-MM-DD ...
  if (std::strlen(s) < 10) return false;
  if (!(s[0]>='0'&&s[0]<='9')) return false;
  if (!(s[1]>='0'&&s[1]<='9')) return false;
  if (!(s[2]>='0'&&s[2]<='9')) return false;
  if (!(s[3]>='0'&&s[3]<='9')) return false;
  if (s[4] != '-') return false;
  if (s[7] != '-') return false;
  int y = (s[0]-'0')*1000 + (s[1]-'0')*100 + (s[2]-'0')*10 + (s[3]-'0');
  int m = (s[5]-'0')*10 + (s[6]-'0');
  int d = (s[8]-'0')*10 + (s[9]-'0');
  *out_date = y*10000 + m*100 + d;
  return true;
}

static bool looks_like_header(const char* line) {
  // common headers contain alphabetic characters
  for (const char* p = line; *p; ++p) {
    if ((*p >= 'A' && *p <= 'Z') || (*p >= 'a' && *p <= 'z')) return true;
    if (p - line > 32) break; // early exit
  }
  return false;
}

int main(int argc, char** argv) {
  bool close_only = false;
  const char* in = nullptr; const char* out = nullptr;
  if (argc == 4 && std::strcmp(argv[1], "--close-only") == 0) {
    close_only = true; in = argv[2]; out = argv[3];
  } else if (argc == 3) {
    in = argv[1]; out = argv[2];
  } else {
    std::fprintf(stderr, "Usage: %s [--close-only] input.csv output.txt\n", argv[0]);
    return 2;
  }

  FILE* fi = nullptr; FILE* fo = nullptr;
  if (fopen_s(&fi, in, "rt")) { std::fprintf(stderr, "Cannot open input %s\n", in); return 1; }
  if (fopen_s(&fo, out, "wt")) { std::fprintf(stderr, "Cannot open output %s\n", out); std::fclose(fi); return 1; }

  char line[4096];
  int count = 0, written = 0;
  while (std::fgets(line, sizeof(line), fi)) {
    ++count;
    if (std::strlen(line) < 8) continue;
    // trim leading spaces
    const char* p = line; while (*p == ' ' || *p == '\t') ++p;
    if (*p == '\0' || *p == '\n' || *p == '\r') continue;
    if (!(*p >= '0' && *p <= '9')) {
      if (looks_like_header(p)) continue; // skip header
    }

    // tokenize by comma (Binance CSV has no embedded commas in first columns)
    const char* cols[8] = {0};
    int ncols = 0; cols[ncols++] = p;
    for (const char* q = p; *q && ncols < 8; ++q) {
      if (*q == ',') { cols[ncols++] = q + 1; }
      if (*q == '\r' || *q == '\n') break;
    }
    if (ncols < 5) continue; // need at least 5 columns

    int yyyymmdd = 0;
    bool ok_date = false;
    // Try ISO first, then epoch ms
    ok_date = parse_iso_to_yyyymmdd(cols[0], &yyyymmdd) || parse_epoch_ms_to_yyyymmdd(cols[0], &yyyymmdd);
    if (!ok_date) continue;

    char* end = nullptr;
    double open = std::strtod(cols[1], &end);
    double high = std::strtod(cols[2], &end);
    double low  = std::strtod(cols[3], &end);
    double close = std::strtod(cols[4], &end);
    if (!(open > 0 && high > 0 && low > 0 && close > 0)) continue;

    if (close_only) {
      std::fprintf(fo, "%08d %.8f\n", yyyymmdd, close);
    } else {
      std::fprintf(fo, "%08d %.8f %.8f %.8f %.8f\n", yyyymmdd, open, high, low, close);
    }
    ++written;
  }

  std::fclose(fi);
  std::fclose(fo);
  std::fprintf(stderr, "Converted %d rows, wrote %d\n", count, written);
  return 0;
}

