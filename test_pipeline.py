#!/usr/bin/env python3
"""
Simple test script to verify the validation pipeline works
"""

import sys
import json
from pathlib import Path

# Add stratval package to path
stratval_path = Path(__file__).parent / 'stratval'
sys.path.insert(0, str(stratval_path))

from stratval.pipeline.orchestrator import ValidationOrchestrator


def test_validation_pipeline():
    """Test the validation pipeline with mock data"""
    print("🧪 Testing StratVal validation pipeline...")

    # Create orchestrator
    orchestrator = ValidationOrchestrator()

    # Run validation with mock strategy path and data
    mock_strategy_path = "./framework/sma_strategy.cpp"

    try:
        results = orchestrator.validate(
            strategy_path=mock_strategy_path,
            pair="BTC/USDT",
            timeframe="1h",
            mode="standard",
            output_dir="./test_reports"
        )
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

    print("✅ Pipeline completed successfully!")
    print(f"📊 Results saved to: {results.get('results_file', 'unknown')}")

    # Print summary
    print("\n📈 Summary:")
    print(f"   Algorithms run: {', '.join(results.get('algorithms_run', []))}")
    print(f"   Data source: {results.get('data_source', 'unknown')}")
    print(f"   Strategy return: {results.get('strategy_results', {}).get('total_return', 'unknown')}")

    # Check algorithm results
    algo_results = results.get('algorithm_results', {})
    print(f"   Algorithm results: {len(algo_results)} algorithms processed")

    for algo_name, algo_result in algo_results.items():
        if 'error' in algo_result:
            print(f"   ⚠️  {algo_name}: {algo_result['error']}")
        else:
            print(f"   ✅ {algo_name}: completed")

    assert len(algo_results) > 0


if __name__ == "__main__":
    try:
        test_validation_pipeline()
        sys.exit(0)
    except Exception:
        sys.exit(1)
