#!/usr/bin/env bash
set -euo pipefail

# Run 5m SMA strategies for SOL & ADA through the framework
# Usage: scripts/run_5m_strategies.sh /path/to/feather/dir [--short N] [--long M] [--fee F]

DIR=${1:-}
shift || true
SW=20
LW=60
FEE=0.0004

while [[ $# -gt 0 ]]; do
  case "$1" in
    --short) SW=$2; shift 2;;
    --long)  LW=$2; shift 2;;
    --fee)   FEE=$2; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$DIR" || ! -d "$DIR" ]]; then
  echo "Usage: $0 /path/to/feather/dir [--short N] [--long M] [--fee F]" >&2
  exit 2
fi

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR="$ROOT_DIR/converted"
mkdir -p "$OUT_DIR"

need_pyarrow=0
python3 - << 'PY' || need_pyarrow=1
try:
  import pyarrow as pa
  import pyarrow.feather
  print('ok')
except Exception:
  pass
PY

if [[ $need_pyarrow -eq 1 ]]; then
  echo "ERROR: pyarrow is required for Feather conversion. Install with: python3 -m pip install pyarrow" >&2
  exit 1
fi

convert_one() {
  local f=$1
  local sym=$2
  local base=$(basename "$f" .feather)
  local out="$OUT_DIR/${base}_ohlc.txt"
  echo "Converting $f -> $out"
  python3 "$ROOT_DIR/tools/feather_to_txt.py" "$f" "$out" --mode ohlc
  echo "Running strategy on $sym: $out"
  "$ROOT_DIR/build/strategy_runner" sma "$out" --short "$SW" --long "$LW" --fee "$FEE" --symbol "$sym"
}

sol_file=$(ls "$DIR"/*SOL*5m*.feather 2>/dev/null | head -n1 || true)
ada_file=$(ls "$DIR"/*ADA*5m*.feather 2>/dev/null | head -n1 || true)

if [[ -z "$sol_file" ]]; then echo "No SOL 5m Feather file found in $DIR" >&2; fi
if [[ -z "$ada_file" ]]; then echo "No ADA 5m Feather file found in $DIR" >&2; fi

if [[ -n "$sol_file" ]]; then convert_one "$sol_file" "SOLUSDT"; fi
if [[ -n "$ada_file" ]]; then convert_one "$ada_file" "ADAUSDT"; fi

echo "Done. Outputs in $OUT_DIR"

