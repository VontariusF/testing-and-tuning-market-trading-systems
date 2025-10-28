#!/usr/bin/env python3
"""
Debug individual algorithms to identify specific issues
"""

import sys
import json
from pathlib import Path

# Add stratval package to path
sys.path.insert(0, str(Path(__file__).parent / 'stratval'))

def debug_algorithm(algorithm_name):
    """Debug a specific algorithm"""
    print(f"\n🔍 Debugging {algorithm_name}...")
    print("-" * 50)

    try:
        from stratval.adapters.base import AlgorithmRegistry

        # Create mock strategy results
        mock_strategy_results = {
            'returns': [0.01, -0.005, 0.008, 0.012, -0.003, 0.015] * 20,
            'equity_curve': [100 + i * 0.5 for i in range(120)],
            'trades': [{'return': 0.01, 'pnl': 1.0} for _ in range(60)],
            'bars': [
                {'date': 20200101 + i, 'open': 100.0 + i * 0.1, 'high': 101.0 + i * 0.1, 'low': 99.0 + i * 0.1, 'close': 100.5 + i * 0.1}
                for i in range(100)
            ],
            'total_return': 0.15,
            'data_source': 'Mock'
        }

        # Get adapter
        adapter = AlgorithmRegistry.get_adapter(algorithm_name)
        print(f"✅ Adapter initialized: {algorithm_name}")

        # Prepare input
        input_file = adapter.prepare_input(mock_strategy_results)
        print(f"✅ Input prepared: {input_file}")

        # Get command args
        cmd_args = adapter.get_command_args(str(input_file))
        print(f"✅ Command args: {' '.join(cmd_args)}")

        # Check executable exists
        executable_path = Path(cmd_args[0])
        print(f"✅ Executable exists: {executable_path.exists()}")

        # Try to execute
        print("🔄 Executing algorithm...")
        result = adapter.execute(mock_strategy_results, timeout=30)  # Short timeout for debugging

        print(f"✅ Execution completed with result: {result}")

        return True

    except Exception as e:
        print(f"❌ Algorithm {algorithm_name} failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_all_failing_algorithms():
    """Debug all currently failing algorithms"""
    print("🚀 Debugging All Failing Algorithms")
    print("=" * 60)

    failing_algorithms = ['CD_MA', 'MCPT_BARS', 'MCPT_TRN']

    results = {}
    for algo in failing_algorithms:
        success = debug_algorithm(algo)
        results[algo] = "SUCCESS" if success else "FAILED"

    print("\n📊 Debug Results Summary:")
    for algo, status in results.items():
        print(f"   {algo}: {status}")

    return results

if __name__ == "__main__":
    debug_all_failing_algorithms()
