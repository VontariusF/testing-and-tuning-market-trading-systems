#!/usr/bin/env python3
"""
Convert real market data from FreqTrade DB format to algorithm-compatible format
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

def convert_timestamp_to_date(timestamp: int) -> int:
    """Convert Unix timestamp to YYYYMMDD format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.year * 10000 + dt.month * 100 + dt.day

def load_real_data_results(json_file: str) -> List[Dict]:
    """Load real data from validation results JSON file"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)

        # Extract bars from strategy results
        strategy_results = data.get('strategy_results', {})
        bars = strategy_results.get('bars', [])

        if not bars:
            print(f"No bars found in {json_file}")
            return []

        return bars

    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return []

def convert_bars_to_algorithm_format(bars: List[Dict]) -> str:
    """Convert bars to algorithm-compatible format"""
    lines = []

    for bar in bars:
        # Convert timestamp to YYYYMMDD format
        timestamp = bar.get('timestamp', 0)
        date = convert_timestamp_to_date(timestamp)

        # Extract OHLC values
        open_price = bar.get('open', 0)
        high_price = bar.get('high', 0)
        low_price = bar.get('low', 0)
        close_price = bar.get('close', 0)

        # Format: YYYYMMDD Open High Low Close
        line = f"{date} {open_price:.6f} {high_price:.6f} {low_price:.6f} {close_price:.6f}"
        lines.append(line)

    return "\n".join(lines) + "\n"

def create_market_data_file(real_data_file: str, output_file: str) -> bool:
    """Create market_data.txt file from real data results"""
    try:
        # Load real data
        bars = load_real_data_results(real_data_file)
        if not bars:
            return False

        # Convert to algorithm format
        formatted_data = convert_bars_to_algorithm_format(bars)

        # Write to output file
        with open(output_file, 'w') as f:
            f.write(formatted_data)

        print(f"Converted {len(bars)} bars from {real_data_file} to {output_file}")
        return True

    except Exception as e:
        print(f"Error creating market data file: {e}")
        return False

def find_latest_real_data_results() -> str:
    """Find the most recent real data results file"""
    real_data_dir = Path("real_data_reports")
    if not real_data_dir.exists():
        return ""

    # Find all JSON files in real_data_reports
    json_files = list(real_data_dir.glob("validation_results_*.json"))
    if not json_files:
        return ""

    # Sort by timestamp (newest first)
    json_files.sort(key=lambda x: x.name, reverse=True)
    return str(json_files[0])

def main():
    """Main conversion function"""
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        # Auto-detect latest real data file
        input_file = find_latest_real_data_results()
        if not input_file:
            print("No real data results found in real_data_reports/")
            return 1

        output_file = "market_data.txt"

    print(f"Converting {input_file} to {output_file}")

    if create_market_data_file(input_file, output_file):
        print("Conversion successful!")
        return 0
    else:
        print("Conversion failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
