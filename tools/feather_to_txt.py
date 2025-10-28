#!/usr/bin/env python3
"""
Convert Binance Futures Feather files to algorithm input text.

Outputs either:
 - OHLC rows:  YYYYMMDD Open High Low Close
 - Close-only: YYYYMMDD Close

Usage:
  python3 tools/feather_to_txt.py input.feather output.txt --mode ohlc
  python3 tools/feather_to_txt.py input.feather output.txt --mode close

Options:
  --date-col   name of timestamp/date column (default: auto-detect)
  --open-col   name of open column (default: auto-detect)
  --high-col   name of high column (default: auto-detect)
  --low-col    name of low column (default: auto-detect)
  --close-col  name of close/price column (default: auto-detect)

Requires: pyarrow (no pandas needed).
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

try:
    import pyarrow as pa
    import pyarrow.feather as feather
    import pyarrow.compute as pc
except Exception as e:
    print("ERROR: pyarrow is required (pip install pyarrow)", file=sys.stderr)
    raise


def _auto_find(colnames: List[str], candidates: List[str]) -> Optional[str]:
    lower = {c.lower(): c for c in colnames}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def _to_yyyymmdd_from_timestamp(arr: pa.ChunkedArray) -> List[str]:
    # arr is timestamp, use Arrow to format to YYYYMMDD
    out = pc.strftime(arr, format="%Y%m%d")
    return out.to_pylist()


def _infer_epoch_unit(v: int) -> str:
    # Infer seconds/ms/us/ns by magnitude
    if v >= 10**18:
        return "ns"
    if v >= 10**15:
        return "us"
    if v >= 10**12:
        return "ms"
    return "s"


def _to_yyyymmdd_from_int(arr: pa.ChunkedArray) -> List[str]:
    # Convert integer epoch to YYYYMMDD
    vals = arr.cast(pa.int64()).to_pylist()
    # find first non-null
    scale = "s"
    for x in vals:
        if x is not None:
            scale = _infer_epoch_unit(int(x))
            break
    div = {"s": 1, "ms": 1000, "us": 1000000, "ns": 1000000000}[scale]
    out: List[str] = []
    from datetime import datetime, timezone

    for x in vals:
        if x is None:
            out.append("")
            continue
        secs = int(int(x) // div)
        dt = datetime.fromtimestamp(secs, tz=timezone.utc)
        out.append(dt.strftime("%Y%m%d"))
    return out


def _to_yyyymmdd_from_string(arr: pa.ChunkedArray) -> List[str]:
    # Try Arrow strptime then strftime
    try:
        ts = pc.strptime(arr, format="%Y-%m-%d %H:%M:%S", unit="s")
        out = pc.strftime(ts, format="%Y%m%d").to_pylist()
        return out
    except Exception:
        pass
    # Try date only
    try:
        ts = pc.strptime(arr, format="%Y-%m-%d", unit="s")
        out = pc.strftime(ts, format="%Y%m%d").to_pylist()
        return out
    except Exception:
        pass
    # Fallback: extract first 8 digits if present
    py = arr.cast(pa.string()).to_pylist()
    out: List[str] = []
    for s in py:
        if not s:
            out.append("")
            continue
        digits = ''.join(ch for ch in s if ch.isdigit())
        out.append(digits[:8] if len(digits) >= 8 else "")
    return out


def _yyyymmdd(table: pa.Table, date_col: str) -> List[str]:
    arr = table[date_col]
    t = arr.type
    if pa.types.is_timestamp(t):
        return _to_yyyymmdd_from_timestamp(arr)
    if pa.types.is_integer(t):
        return _to_yyyymmdd_from_int(arr)
    if pa.types.is_string(t) or pa.types.is_large_string(t):
        return _to_yyyymmdd_from_string(arr)
    # Convert to string as last resort
    return _to_yyyymmdd_from_string(pc.cast(arr, pa.string()))


def main() -> int:
    p = argparse.ArgumentParser(description="Convert Feather to algo text format")
    p.add_argument("input", help="input .feather file")
    p.add_argument("output", help="output .txt file")
    p.add_argument("--mode", choices=["ohlc", "close"], default="ohlc")
    p.add_argument("--date-col")
    p.add_argument("--open-col")
    p.add_argument("--high-col")
    p.add_argument("--low-col")
    p.add_argument("--close-col")
    args = p.parse_args()

    table = feather.read_table(args.input)
    cols = table.column_names

    # Heuristics for column names (case-insensitive)
    date_col = args.date_col or _auto_find(cols, [
        "open_time", "timestamp", "time", "date", "datetime",
        "startTime", "start_time", "openTime"
    ])
    if not date_col:
        print("ERROR: Could not detect date column; use --date-col", file=sys.stderr)
        return 2

    if args.mode == "ohlc":
        ocol = args.open_col or _auto_find(cols, ["open", "o", "Open"])
        hcol = args.high_col or _auto_find(cols, ["high", "h", "High"])
        lcol = args.low_col  or _auto_find(cols, ["low", "l", "Low"])
        ccol = args.close_col or _auto_find(cols, ["close", "c", "Close"])
        for name, nm in [("open", ocol), ("high", hcol), ("low", lcol), ("close", ccol)]:
            if nm is None:
                print(f"ERROR: Could not detect {name} column; use --{name}-col", file=sys.stderr)
                return 2
        ymd = _yyyymmdd(table, date_col)
        o = table[ocol].cast(pa.float64()).to_pylist()
        h = table[hcol].cast(pa.float64()).to_pylist()
        l = table[lcol].cast(pa.float64()).to_pylist()
        c = table[ccol].cast(pa.float64()).to_pylist()
        with open(args.output, "w") as fo:
            wrote = 0
            for i in range(len(ymd)):
                if not ymd[i] or o[i] is None or h[i] is None or l[i] is None or c[i] is None:
                    continue
                fo.write(f"{ymd[i]} {o[i]:.8f} {h[i]:.8f} {l[i]:.8f} {c[i]:.8f}\n")
                wrote += 1
        print(f"Wrote {wrote} OHLC rows to {args.output}")
        return 0

    else:  # close-only
        ccol = args.close_col or _auto_find(cols, ["close", "c", "Close", "price"])
        if ccol is None:
            print("ERROR: Could not detect close/price column; use --close-col", file=sys.stderr)
            return 2
        ymd = _yyyymmdd(table, date_col)
        c = table[ccol].cast(pa.float64()).to_pylist()
        with open(args.output, "w") as fo:
            wrote = 0
            for i in range(len(ymd)):
                if not ymd[i] or c[i] is None:
                    continue
                fo.write(f"{ymd[i]} {c[i]:.8f}\n")
                wrote += 1
        print(f"Wrote {wrote} close-only rows to {args.output}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

