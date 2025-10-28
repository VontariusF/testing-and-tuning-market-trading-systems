#!/usr/bin/env python3
"""
Test script for StratVal system
Demonstrates the complete workflow
"""

import sys
import os
from pathlib import Path

# Add stratval to path
sys.path.insert(0, str(Path(__file__).parent))

from stratval.generator.strategy_generator import StrategyGenerator
from stratval.pipeline.orchestrator import ValidationOrchestrator
from stratval.scoring.scorer import StrategyScorer
from stratval.adapters.base import AlgorithmRegistry
from stratval.adapters.mcpt_bars import MCPTBarsAdapter
from stratval.adapters.drawdown import DrawdownAdapter


def test_strategy_generation():
    """Test AI strategy generation"""
    print("🧪 Testing Strategy Generation...")

    generator = StrategyGenerator()

    # Test natural language generation
    description = "moving average crossover with 10 and 50 periods"
    print(f"📝 Generating strategy: '{description}'")

    try:
        strategy_code = generator.from_natural_language(description)
        print("✅ Strategy generated successfully!")
        print(f"📄 Generated {len(strategy_code)} characters of C++ code")

        # Save to file
        with open("test_strategy.cpp", 'w') as f:
            f.write(strategy_code)
        print("💾 Strategy saved to test_strategy.cpp")

        assert True

    except Exception as e:
        print(f"❌ Strategy generation failed: {e}")
        assert False


def test_algorithm_adapters():
    """Test algorithm adapters"""
    print("\n🧪 Testing Algorithm Adapters...")

    # Register adapters
    AlgorithmRegistry.register("MCPT_BARS", MCPTBarsAdapter)
    AlgorithmRegistry.register("DRAWDOWN", DrawdownAdapter)

    try:
        # Test MCPT_BARS adapter
        mcpt_adapter = AlgorithmRegistry.get_adapter("MCPT_BARS")
        print("✅ MCPT_BARS adapter created successfully")

        # Test DRAWDOWN adapter
        dd_adapter = AlgorithmRegistry.get_adapter("DRAWDOWN")
        print("✅ DRAWDOWN adapter created successfully")

        assert True

    except Exception as e:
        print(f"❌ Adapter creation failed: {e}")
        assert False


def test_scoring_system():
    """Test scoring system"""
    print("\n🧪 Testing Scoring System...")

    try:
        scorer = StrategyScorer()

        # Mock strategy results
        mock_strategy_results = {
            'returns': [0.01, -0.005, 0.008, 0.012, -0.003, 0.015],
            'equity_curve': [100, 101, 100.5, 101.3, 102.5, 102.2, 103.7],
            'trades': [
                {'return': 0.01, 'pnl': 1.0},
                {'return': -0.005, 'pnl': -0.5},
                {'return': 0.008, 'pnl': 0.8},
                {'return': 0.012, 'pnl': 1.2},
                {'return': -0.003, 'pnl': -0.3},
                {'return': 0.015, 'pnl': 1.5}
            ]
        }

        # Mock algorithm results
        mock_algorithm_results = {
            'MCPT_BARS': {
                'pvalue': 0.023,
                'skill': 0.0042,
                'training_bias': 0.0012
            },
            'DRAWDOWN': {
                'drawdown_05': 0.156,
                'drawdown_01': 0.234
            }
        }

        # Calculate score
        scores = scorer.calculate_score(mock_strategy_results, mock_algorithm_results)

        print("✅ Scoring calculation successful!")
        print(f"📊 Total Score: {scores['total_score']}/100")
        print(f"🎓 Grade: {scores['grade']}")
        print(f"📈 Performance Score: {scores['performance_score']}")
        print(f"🔬 Statistical Score: {scores['statistical_score']}")
        print(f"⚠️  Risk Score: {scores['risk_score']}")

        if scores['recommendations']:
            print("💡 Recommendations:")
            for rec in scores['recommendations']:
                print(f"   • {rec}")

        assert True

    except Exception as e:
        print(f"❌ Scoring failed: {e}")
        assert False


def test_mock_validation():
    """Test mock validation pipeline"""
    print("\n🧪 Testing Mock Validation Pipeline...")

    try:
        orchestrator = ValidationOrchestrator()

        # Real data validation run
        results = orchestrator.validate(
            strategy_path="test_strategy.cpp",
            pair="BTC/USDT",  # ✅ Use real market data from database
            mode="quick",
            output_dir="./test_reports"
        )

        print("✅ Mock validation completed!")
        print(f"📊 Score: {results['scores']['total_score']}/100")
        print(f"🎓 Grade: {results['scores']['grade']}")

        assert True

    except Exception as e:
        print(f"❌ Mock validation failed: {e}")
        assert False


def main():
    """Run all tests"""
    print("🚀 Starting StratVal System Tests")
    print("=" * 50)

    tests = [
        test_strategy_generation,
        test_algorithm_adapters,
        test_scoring_system,
        test_mock_validation
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
        except AssertionError:
            continue
        except Exception as exc:
            print(f"❌ {test.__name__} raised an unexpected error: {exc}")
            continue
        else:
            passed += 1

    print("\n" + "=" * 50)
    print(f"🧪 Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! StratVal system is ready.")
        print("\n📖 Usage Examples:")
        print("  python -m stratval.cli.stratval create 'MA crossover 10 50' --output strategy.cpp")
        print("  python -m stratval.cli.stratval validate strategy.cpp --data data.txt --mode thorough")
        print("  python -m stratval.cli.stratval report results.json --format html")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
