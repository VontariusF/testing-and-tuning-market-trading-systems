#!/usr/bin/env python3
"""
End-to-end StratVal system test
Generates and tests 50+ random trading strategies
"""

import os
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import statistics

from stratval.utils.config import Config


class EndToEndRunner:
    """Comprehensive end-to-end test runner for StratVal system"""

    def __init__(self):
        self.output_dir = Path("end_to_end_results")
        self.output_dir.mkdir(exist_ok=True)
        self.strategies_dir = self.output_dir / "generated_strategies"
        self.strategies_dir.mkdir(exist_ok=True)
        self.reports_dir = self.output_dir / "validation_reports"
        self.reports_dir.mkdir(exist_ok=True)

        # Load default market data configuration
        self.config = Config()
        self.default_pair = self.config.get('database.default_pair', 'BTC/USDT')
        self.default_timeframe = self.config.get('database.default_timeframe', '1h')

        # Strategy templates for diversity
        self.strategy_templates = [
            # Moving Average strategies
            "moving average crossover strategy with {fast} and {slow} periods",
            "simple moving average trend following strategy using {period} period MA",
            "exponential moving average crossover with periods {fast} and {slow}",
            "triple moving average strategy using {fast}, {medium}, and {slow} periods",

            # RSI strategies
            "RSI oversold bounce strategy with period {rsi_period} and threshold {threshold}",
            "RSI divergence strategy with RSI period {rsi_period}",
            "RSI mean reversion strategy with oversold at {low} and overbought at {high}",

            # MACD strategies
            "MACD strategy with fast {fast}, slow {slow}, and signal {signal} periods",
            "MACD histogram strategy with standard parameters",

            # Bollinger Band strategies
            "Bollinger Band mean reversion strategy with period {period} and deviation {deviation}",
            "Bollinger Band squeeze strategy with period {period}",
            "Bollinger Band breakout strategy",

            # Momentum strategies
            "momentum strategy based on {period} period returns",
            "ROC (Rate of Change) strategy with {period} period",

            # Volume-based strategies
            "volume breakout strategy with {period} period average volume",
            "volume-price analysis strategy",

            # Support/Resistance strategies
            "support and resistance breakout strategy",
            "pivot point strategy",

            # Channel strategies
            "Donchian channel strategy with {period} period",
            "Keltner channel strategy",

            # Oscillator strategies
            "stochastic oscillator strategy with K period {k} and D period {d}",
            "Williams %R strategy",
            "CCI (Commodity Channel Index) strategy with period {period}",

            # Trend following
            "trend following strategy using ADX with period {period}",
            "Parabolic SAR strategy",
            "Ichimoku cloud strategy",

            # Mean reversion
            "mean reversion strategy with lookback {period}",
            "z-score mean reversion strategy",

            # Volatility strategies
            "ATR (Average True Range) based strategy with period {period}",
            "volatility breakout strategy",

            # Multi-timeframe strategies
            "multi-timeframe strategy using {primary} and {secondary} timeframes",

            # Pattern recognition
            "engulfing pattern strategy",
            "morning star pattern strategy",
            "hammer pattern strategy",

            # Custom combinations
            "RSI and moving average combination strategy",
            "MACD and Bollinger Band combination",
            "volume and price momentum strategy",
        ]

        self.strategy_results = []

    def generate_random_strategy_description(self) -> str:
        """Generate a random strategy description with parameters"""
        template = random.choice(self.strategy_templates)

        # Parameter ranges for different strategy types
        params = {
            'fast': random.randint(5, 20),
            'slow': random.randint(20, 50),
            'medium': random.randint(15, 30),
            'period': random.randint(10, 30),
            'rsi_period': random.randint(10, 21),
            'threshold': random.randint(20, 40),
            'low': random.randint(20, 35),
            'high': random.randint(65, 80),
            'signal': random.randint(5, 12),
            'deviation': round(random.uniform(1.5, 2.5), 1),
            'k': random.randint(10, 21),
            'd': random.randint(3, 8),
            'primary': random.choice(['1h', '4h', '1d']),
            'secondary': random.choice(['15m', '30m', '1h'])
        }

        return template.format(**params)

    def create_strategy(self, description: str, strategy_id: int) -> str:
        """Create a strategy using StratVal CLI"""
        strategy_file = self.strategies_dir / f"strategy_{strategy_id:03d}.cpp"

        cmd = [
            sys.executable, "-m", "stratval.cli.stratval", "create",
            description,
            "--output", str(strategy_file)
        ]

        print(f"🎯 Creating strategy {strategy_id}: {description[:50]}...")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                print(f"  ✅ Strategy {strategy_id} created successfully")
                return str(strategy_file)
            else:
                print(f"  ❌ Strategy {strategy_id} creation failed: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print(f"  ⏰ Strategy {strategy_id} creation timed out")
            return None
        except Exception as e:
            print(f"  💥 Strategy {strategy_id} creation error: {e}")
            return None

    def validate_strategy(self, strategy_path: str, strategy_id: int) -> Dict[str, Any]:
        """Validate a strategy using StratVal CLI"""
        results_file = self.reports_dir / f"validation_{strategy_id:03d}.json"

        existing_reports = set(self.reports_dir.glob("validation_results_*.json"))

        cmd = [
            sys.executable, "-m", "stratval.cli.stratval", "validate",
            strategy_path,
            "--mode", "standard",
            "--output-dir", str(self.reports_dir),
            "--format", "json",
            "--quiet"
        ]

        if self.default_pair:
            cmd.extend(["--pair", self.default_pair])
        if self.default_timeframe:
            cmd.extend(["--timeframe", self.default_timeframe])

        print(f"  🔬 Validating strategy {strategy_id}...")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=420)

            if result.returncode == 0:
                print(f"    ✅ Strategy {strategy_id} validated successfully")
                current_reports = set(self.reports_dir.glob("validation_results_*.json"))
                new_reports = list(current_reports - existing_reports)

                selected_report = None
                if new_reports:
                    selected_report = max(new_reports, key=lambda path: path.stat().st_mtime)
                elif current_reports:
                    selected_report = max(current_reports, key=lambda path: path.stat().st_mtime)

                if selected_report:
                    with open(selected_report, 'r') as f:
                        validation_results = json.load(f)

                    try:
                        shutil.copyfile(selected_report, results_file)
                    except Exception as copy_error:
                        print(f"    ⚠️  Could not copy validation results to {results_file}: {copy_error}")

                    return validation_results

                return {"error": "Validation results not generated"}
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
                print(f"    ❌ Strategy {strategy_id} validation failed: {error_msg}")
                return {"error": error_msg}

        except subprocess.TimeoutExpired:
            print(f"    ⏰ Strategy {strategy_id} validation timed out")
            return {"error": "timeout"}
        except Exception as e:
            print(f"    💥 Strategy {strategy_id} validation error: {e}")
            return {"error": str(e)}

    def run_end_to_end_test(self, num_strategies: int = 50) -> Dict[str, Any]:
        """Run the complete end-to-end test"""
        print("🚀 Starting Comprehensive StratVal End-to-End Test")
        print("=" * 60)
        print(f"🎯 Target: Generate and test {num_strategies} random strategies")
        print(f"📁 Output directory: {self.output_dir}")
        print()

        start_time = time.time()
        successful_creations = 0
        successful_validations = 0

        for i in range(1, num_strategies + 1):
            # Generate random strategy description
            description = self.generate_random_strategy_description()

            # Create strategy
            strategy_path = self.create_strategy(description, i)

            validation_results = None
            if strategy_path:
                successful_creations += 1
                # Validate strategy
                validation_results = self.validate_strategy(strategy_path, i)
                if 'error' not in validation_results:
                    successful_validations += 1

            # Record results
            strategy_result = {
                'strategy_id': i,
                'description': description,
                'created': strategy_path is not None,
                'validated': validation_results is not None and 'error' not in validation_results,
                'strategy_path': strategy_path,
                'validation_results': validation_results,
                'timestamp': time.time()
            }

            self.strategy_results.append(strategy_result)

            # Periodic progress report
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"Processed {i} strategies in {elapsed:.1f}s ({rate:.1f} strat/sec)")
                print()

        # Generate final summary
        end_time = time.time()
        total_time = end_time - start_time

        summary = self.generate_summary_report(total_time, num_strategies, successful_creations, successful_validations)

        print("\n" + "=" * 60)
        print("🏁 End-to-End Test Complete!")
        print("=" * 60)
        print(f"⏱️  Total time: {total_time:.2f} seconds")
        print(f"🎯 Strategies attempted: {num_strategies}")
        print(f"✅ Strategies created: {successful_creations}")
        print(f"🔬 Strategies validated: {successful_validations}")
        if total_time > 0:
            print(f"📈 Creation rate: {successful_creations/total_time:.1f} strat/s")
            print(f"🔬 Validation rate: {successful_validations/total_time:.1f} strat/s")
        print(f"📊 Success rate: {(successful_creations/num_strategies)*100:.1f}% creation, {(successful_validations/num_strategies)*100:.1f}% validation")
        print(f"📁 Results saved to: {self.output_dir}")

        return summary

    def generate_summary_report(self, total_time: float, total_attempted: int,
                              successful_creations: int, successful_validations: int) -> Dict[str, Any]:
        """Generate comprehensive summary report"""
        summary_file = self.output_dir / "end_to_end_summary.json"

        # Extract scores from successful validations
        scores = []
        grades = []
        for result in self.strategy_results:
            if result['validated'] and result['validation_results']:
                scores_data = result['validation_results'].get('scores', {})
                if isinstance(scores_data, dict):
                    total_score = scores_data.get('total_score')
                    grade = scores_data.get('grade')
                    if total_score is not None:
                        scores.append(total_score)
                    if grade:
                        grades.append(grade)

        # Calculate statistics
        summary = {
            'test_metadata': {
                'total_strategies_attempted': total_attempted,
                'successful_creations': successful_creations,
                'successful_validations': successful_validations,
                'total_time_seconds': round(total_time, 2),
                'creation_success_rate': round(successful_creations/total_attempted*100, 1),
                'validation_success_rate': round(successful_validations/total_attempted*100, 1),
                'test_timestamp': time.time(),
                'stratval_version': '1.0.0'
            },
            'performance_statistics': {},
            'strategy_distribution': {},
            'detailed_results': self.strategy_results
        }

        if scores:
            summary['performance_statistics'] = {
                'average_score': round(statistics.mean(scores), 2),
                'median_score': round(statistics.median(scores), 2),
                'min_score': min(scores),
                'max_score': max(scores),
                'score_std_dev': round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
                'total_scores_calculated': len(scores)
            }

        if grades:
            grade_counts = {}
            for grade in grades:
                grade_counts[grade] = grade_counts.get(grade, 0) + 1
            summary['performance_statistics']['grade_distribution'] = grade_counts

        # Strategy distribution by type
        strategy_types = {}
        for result in self.strategy_results:
            desc = result['description'].lower()
            strategy_type = 'Unknown'
            if 'moving average' in desc or 'ma ' in desc:
                strategy_type = 'Moving Average'
            elif 'rsi' in desc:
                strategy_type = 'RSI'
            elif 'macd' in desc:
                strategy_type = 'MACD'
            elif 'bollinger' in desc:
                strategy_type = 'Bollinger Band'
            elif 'momentum' in desc or 'roc' in desc:
                strategy_type = 'Momentum'
            elif 'volume' in desc:
                strategy_type = 'Volume'
            elif 'stochastic' in desc:
                strategy_type = 'Stochastic'
            elif 'cci' in desc:
                strategy_type = 'CCI'
            elif 'trend' in desc:
                strategy_type = 'Trend Following'
            elif 'mean reversion' in desc:
                strategy_type = 'Mean Reversion'
            elif 'volatility' in desc or 'atr' in desc:
                strategy_type = 'Volatility'
            elif 'pattern' in desc:
                strategy_type = 'Pattern Recognition'

            strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1

        summary['strategy_distribution'] = strategy_types

        # Save comprehensive report
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        # Save simplified results table
        table_file = self.output_dir / "end_to_end_results_table.txt"
        self.save_results_table(table_file)

        print(f"💾 Detailed summary saved to: {summary_file}")
        print(f"📋 Results table saved to: {table_file}")

        return summary

    def save_results_table(self, output_file: Path):
        """Save a readable table of results"""
        with open(output_file, 'w') as f:
            f.write("StratVal End-to-End Test Results\n")
            f.write("=" * 80 + "\n\n")

            f.write("ID | Created | Validated | Score | Grade | Strategy Description (truncated)\n")
            f.write("-" * 80 + "\n")

            for result in self.strategy_results:
                strategy_id = result['strategy_id']
                created = "✅" if result['created'] else "❌"
                validated = "✅" if result['validated'] else "❌"

                score = "N/A"
                grade = "N/A"
                if result['validation_results'] and 'scores' in result['validation_results']:
                    scores = result['validation_results']['scores']
                    if isinstance(scores, dict):
                        total_score_val = scores.get('total_score')
                        if total_score_val is not None:
                            score = f"{total_score_val:.1f}"
                        if 'grade' in scores:
                            grade = scores['grade']

                desc = result['description'][:60] + "..." if len(result['description']) > 60 else result['description']

                f.write(f"{strategy_id:2d} |   {created}    |    {validated}    | {score:4s} | {grade:4s} | {desc}\n")

            f.write("\n" + "=" * 80 + "\n")


def main():
    """Main entry point"""
    # Ensure we're in the right directory
    if not Path("stratval").exists():
        print("❌ Error: Please run this script from the StratVal project root directory")
        return 1

    # Create and run the test
    runner = EndToEndRunner()

    try:
        summary = runner.run_end_to_end_test(num_strategies=50)

        # Print key metrics
        meta = summary['test_metadata']
        perf = summary.get('performance_statistics', {})

        print("\n📊 Key Metrics:")
        print(f"   Success Rate: {meta['creation_success_rate']}% creation, {meta['validation_success_rate']}% validation")
        print(f"   Average Score: {perf.get('average_score', 'N/A')}")
        print(f"   Grade Distribution: {perf.get('grade_distribution', {})}")
        print(f"   Strategy Types: {summary.get('strategy_distribution', {})}")

        return 0

    except Exception as e:
        print(f"💥 End-to-end test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
