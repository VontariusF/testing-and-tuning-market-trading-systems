#!/usr/bin/env python3
"""
Simple standalone test of algorithm adapters
"""

import sys
import json
from pathlib import Path
import subprocess

# Add stratval adapters to path directly
sys.path.insert(0, str(Path(__file__).parent / 'stratval'))

def test_working_adapters():
    """Test the working algorithm adapters"""
    print("🧪 Testing working algorithm adapters...")

    from stratval.adapters.base import AlgorithmRegistry

    print(f"📊 Available adapters: {AlgorithmRegistry.get_available_algorithms()}")

    # Test adapter templates (without actually running executables)
    working_algorithms = ['CD_MA', 'DRAWDOWN', 'MCPT_BARS', 'SELBIAS', 'MCPT_TRN']

    mock_strategy_results = {
        'returns': [0.01, -0.005, 0.008, 0.012, -0.003, 0.015] * 10,  # Mock returns
        'equity_curve': [100, 101, 100.5, 101.3, 102.5, 102.2, 103.7],
        'trades': [{'return': 0.01, 'pnl': 1.0}] * 60,
        'bars': [  # Mock OHLC bars
            {'date': 20200101, 'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.5},
            {'date': 20200102, 'open': 100.5, 'high': 102.0, 'low': 100.0, 'close': 101.5},
            {'date': 20200103, 'open': 101.5, 'high': 103.0, 'low': 101.0, 'close': 102.0},
            {'date': 20200104, 'open': 102.0, 'high': 104.0, 'low': 101.5, 'close': 103.0},
            {'date': 20200105, 'open': 103.0, 'high': 105.0, 'low': 102.5, 'close': 104.0},
        ] * 20,  # 100 bars total
        'total_return': 0.037,
        'data_source': 'Mock'
    }

    for algo_name in working_algorithms:
        if algo_name in AlgorithmRegistry.get_available_algorithms():
            print(f"  🔬 Testing {algo_name} adapter...")

            try:
                adapter = AlgorithmRegistry.get_adapter(algo_name)

                # Test prepare_input and get_command_args (but don't execute)
                input_file = adapter.prepare_input(mock_strategy_results)
                cmd_args = adapter.get_command_args(str(input_file))

                print(f"    ✅ {algo_name} adapter initialized")
                print(f"       Input file: {input_file}")
                print(f"       Command: {' '.join(cmd_args[:3])}...")
                print(f"       Executable exists: {Path(cmd_args[0]).exists()}")

            except Exception as e:
                print(f"    ❌ {algo_name} failed: {e}")

    print("\n✅ Adapter testing completed!")

if __name__ == "__main__":
    test_working_adapters()
