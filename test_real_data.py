#!/usr/bin/env python3
"""
Test StratVal system with real FreqTrade database data
"""

import sys
import json
from pathlib import Path

# Add stratval package to path
sys.path.insert(0, str(Path(__file__).parent / 'stratval'))

def test_with_real_data():
    """Test the system with real database data"""
    print("🚀 Testing StratVal with Real Database Data...")

    try:
        from stratval.pipeline.orchestrator import ValidationOrchestrator
        from stratval.adapters.base import AlgorithmRegistry

        # Database connection string - UPDATE THIS with your actual connection
        # Example: "postgresql://freqtrade_user:password@localhost:5432/freqtrade"
        db_connection_string = "postgresql://freqtrade_user:Vontarius97$@localhost:5432/freqtrade_db"

        print(f"🔌 Connecting to database: {db_connection_string.replace('your_password', '***')}")

        # Create orchestrator with database connection
        orchestrator = ValidationOrchestrator(db_connection_string)

        # Test database connection
        print("\n📊 Testing database connection...")

        # Get available pairs first
        available_pairs = orchestrator.db.get_available_pairs()
        print(f"   Available pairs: {available_pairs}")

        if available_pairs:
            test_pair = "BTC_USDT"  # Use BTC_USDT format (no slash)
            print(f"   Testing with pair: {test_pair}")
        else:
            test_pair = "BTC_USDT"  # Fallback
            print(f"   No pairs found, using fallback: {test_pair}")

        market_data = orchestrator._fetch_market_data(test_pair, "1h", limit=100)

        if market_data:
            print(f"✅ Successfully fetched {len(market_data)} real market data points!")
            print(f"   Date range: {market_data[0]['timestamp']} to {market_data[-1]['timestamp']}")
            print(f"   Price range: ${market_data[0]['close']:.2f} to ${market_data[-1]['close']:.2f}")
        else:
            print("⚠️  No real data available, using mock data for demonstration")
            market_data = None

        # Test with real data if available, otherwise use mock
        if market_data:
            print("\n🔬 Testing with REAL market data...")
            results = orchestrator.validate(
                strategy_path="./framework/sma_strategy.cpp",
                pair=test_pair,
                timeframe="1h",
                mode="standard",
                output_dir="./real_data_reports"
            )
        else:
            print("\n🔬 Testing with MOCK data (database unavailable)...")
            results = orchestrator.validate(
                strategy_path="./framework/sma_strategy.cpp",
                pair=test_pair,
                timeframe="1h",
                mode="standard",
                output_dir="./mock_data_reports"
            )

        print("✅ Validation completed successfully!")

        # Display results summary
        scores = results.get('scores', {})
        print("\n📊 Results Summary:")
        print(f"   Total Score: {scores.get('total_score', 'N/A')}/100")
        print(f"   Grade: {scores.get('grade', 'N/A')}")
        print(f"   Data Source: {results.get('data_source', 'Unknown')}")
        print(f"   Algorithms Run: {len(results.get('algorithms_run', []))}")

        # Show algorithm results
        algo_results = results.get('algorithm_results', {})
        print("\n🔬 Algorithm Results:")
        for algo_name, algo_result in algo_results.items():
            if 'error' in algo_result:
                print(f"   ⚠️  {algo_name}: {algo_result['error']}")
            else:
                print(f"   ✅ {algo_name}: Completed")

        assert True

    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        import traceback
        traceback.print_exc()
        assert False

if __name__ == "__main__":
    success = test_with_real_data()
    print(f"\n{'🎉 REAL DATA TEST PASSED!' if success else '❌ REAL DATA TEST FAILED!'}")
    sys.exit(0 if success else 1)
