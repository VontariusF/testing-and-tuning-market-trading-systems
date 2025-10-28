#!/usr/bin/env bash
set -euo pipefail

# Convert all Feather files in a directory to algorithm text formats.
# Usage: tools/convert_binance_feather.sh /path/to/folder [--close-only|--ohlc]

DIR=${1:-}
MODE=${2:---both}

if [[ -z "$DIR" || ! -d "$DIR" ]]; then
  echo "Usage: $0 /path/to/folder [--close-only|--ohlc]" >&2
  exit 2
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
OUT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)/converted
mkdir -p "$OUT_DIR"

shopt -s nullglob
count=0
for f in "$DIR"/*.feather; do
  base=$(basename "$f" .feather)
  if [[ "$MODE" == "--ohlc" ]]; then
    python3 "$SCRIPT_DIR/feather_to_txt.py" "$f" "$OUT_DIR/${base}_ohlc.txt" --mode ohlc
  elif [[ "$MODE" == "--close-only" ]]; then
    python3 "$SCRIPT_DIR/feather_to_txt.py" "$f" "$OUT_DIR/${base}_close.txt" --mode close
  else
    python3 "$SCRIPT_DIR/feather_to_txt.py" "$f" "$OUT_DIR/${base}_ohlc.txt" --mode ohlc
    python3 "$SCRIPT_DIR/feather_to_txt.py" "$f" "$OUT_DIR/${base}_close.txt" --mode close
  fi
  ((count++)) || true
done

echo "Converted $count Feather file(s) into $OUT_DIR"

