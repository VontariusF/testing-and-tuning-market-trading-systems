#!/usr/bin/env python3
"""
StratVal - Strategy Validator
AI-powered trading strategy creation, validation, and optimization system

Usage:
    stratval create "moving average crossover" --output strategy.cpp
    stratval validate strategy.cpp --data market_data.txt --mode thorough
    stratval optimize strategy.cpp --data market_data.txt --params "fast:5-20,slow:30-100"
    stratval report results.json --format html
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

def get_database():
    """Get database connection for the project"""
    from pathlib import Path
    db_path = Path.cwd() / "strategy_repository.db"
    try:
        from strategys.db import StrategyRepository
        return StrategyRepository(db_path)
    except ImportError:
        try:
            import strategys.db.repository as repo
            return repo.StrategyRepository(db_path)
        except ImportError as e:
            raise ImportError(f"Cannot import StrategyRepository: {e}")

try:
    from stratval.generator.strategy_generator import StrategyGenerator
    from stratval.pipeline.orchestrator import ValidationOrchestrator
    from stratval.reporting.json_reporter import JSONReporter
    from stratval.reporting.terminal_reporter import TerminalReporter
    from stratval.reporting.html_reporter import HTMLReporter
    from stratval.utils.config import Config
except ImportError:  # Allow running as a script from repo root
    from generator.strategy_generator import StrategyGenerator
    from pipeline.orchestrator import ValidationOrchestrator
    from reporting.json_reporter import JSONReporter
    from reporting.terminal_reporter import TerminalReporter
    from reporting.html_reporter import HTMLReporter
    from utils.config import Config


class StratValCLI:
    """Main CLI interface for StratVal system"""

    def __init__(self):
        self.config = Config()
        self.generator = StrategyGenerator()
        self.orchestrator = ValidationOrchestrator()

    def create_strategy(self, args) -> int:
        """Create a new strategy from natural language description"""
        try:
            print(f"🎯 Creating strategy: {args.description}")

            # Generate strategy code
            strategy_code = self.generator.from_natural_language(args.description)

            # Write to output file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                f.write(strategy_code)

            print(f"✅ Strategy created: {output_path}")

            if args.validate:
                print("🔄 Running validation on new strategy...")
                return self.validate_strategy(args, strategy_path=str(output_path))

            return 0

        except Exception as e:
            print(f"❌ Error creating strategy: {e}")
            return 1

    def validate_strategy(self, args, strategy_path: str = None) -> int:
        """Validate a strategy using statistical algorithms"""
        try:
            strategy_file = strategy_path or args.strategy
            data_file = getattr(args, 'data', None)

            # Determine requested market data configuration
            pair = getattr(args, 'pair', None) or self.config.get('database.default_pair', 'BTC/USDT')
            timeframe = getattr(args, 'timeframe', None) or self.config.get('database.default_timeframe', '1h')

            if not os.path.exists(strategy_file):
                print(f"❌ Strategy file not found: {strategy_file}")
                return 1

            if data_file:
                if not os.path.exists(data_file):
                    print(f"❌ Data file not found: {data_file}")
                    return 1
                print(f"📊 Using local market data file: {data_file}")
            else:
                print(f"📊 Using database market data: pair={pair}, timeframe={timeframe}")

            print(f"🔬 Validating strategy: {strategy_file}")
            print(f"⚡ Mode: {args.mode}")

            # Run validation pipeline
            results = self.orchestrator.validate(
                strategy_path=strategy_file,
                pair=pair,
                timeframe=timeframe,
                mode=args.mode,
                output_dir=args.output_dir,
                data_path=data_file
            )

            # Generate reports
            self._generate_reports(results, args)

            return 0

        except Exception as e:
            print(f"❌ Error validating strategy: {e}")
            return 1

    def optimize_strategy(self, args) -> int:
        """Optimize strategy parameters"""
        try:
            print(f"🔧 Optimizing strategy: {args.strategy}")

            # Parse parameter ranges
            param_ranges = self._parse_param_ranges(args.params)

            # Run optimization
            results = self.orchestrator.optimize(
                strategy_path=args.strategy,
                data_path=args.data,
                param_ranges=param_ranges,
                optimization_target=args.optimize_for
            )

            # Generate reports
            self._generate_reports(results, args)

            return 0

        except Exception as e:
            print(f"❌ Error optimizing strategy: {e}")
            return 1

    def generate_report(self, args) -> int:
        """Generate report from validation results"""
        try:
            # Load results
            with open(args.results, 'r') as f:
                results = json.load(f)

            print(f"📋 Generating report from: {args.results}")

            # Generate requested formats
            if 'html' in args.format:
                html_reporter = HTMLReporter()
                html_path = html_reporter.generate(results, args.output)
                print(f"📄 HTML report: {html_path}")

            if 'json' in args.format:
                json_reporter = JSONReporter()
                json_path = json_reporter.generate(results, args.output)
                print(f"📄 JSON report: {json_path}")

            if 'terminal' in args.format or not args.format:
                terminal_reporter = TerminalReporter()
                terminal_reporter.generate(results)

            return 0

        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return 1

    def show_leaderboard(self, args) -> int:
        """Show strategy leaderboard with performance metrics"""
        try:
            # Initialize repository
            repository = get_database()

            if args.summary:
                # Show summary statistics
                summary = repository.get_leaderboard_summary()
                self._print_leaderboard_summary(summary)
            else:
                # Show detailed leaderboard
                leaderboard = repository.get_leaderboard(
                    top_n=args.top,
                    status_filter=args.status,
                    strategy_family=args.family
                )
                self._print_leaderboard(leaderboard, args.detailed)

            return 0

        except Exception as e:
            print(f"❌ Error accessing leaderboard: {e}")
            return 1

    def _print_leaderboard_summary(self, summary: Dict[str, Any]):
        """Print leaderboard summary statistics"""
        print("🏆 Strategy Leaderboard Summary")
        print("=" * 50)

        print(f"📊 Total Strategies Tracked: {summary['total_strategies']}")
        print(f"🏃 Active Leaderboard Entries: {summary['active_leaderboard_entries']}")
        print()

        print("📈 Performance Averages (Active Strategies):")
        print(".2f")
        print(".1%")
        print(".1%")
        print(".2f")
        print(".1f")

        if summary['top_performer']['name']:
            print()
            print(".1f")

    def _print_leaderboard(self, leaderboard: List[Dict[str, Any]], detailed: bool = False):
        """Print detailed leaderboard"""
        if not leaderboard:
            print("📈 No leaderboard entries found")
            return

        print("🏆 Strategy Leaderboard")
        print("=" * 80)

        if detailed:
            # Detailed tabular format
            headers = ["Rank", "Strategy", "Family", "Status", "Score", "Sharpe", "Return", "Max DD", "Win Rate", "Trades", "Bias Sel"]
            col_widths = [4, 20, 12, 8, 6, 6, 6, 7, 8, 6, 8]

            # Header
            header_line = " | ".join(f"{header:<{width}}" for header, width in zip(headers, col_widths))
            print(header_line)
            print("-" * len(header_line))

            # Data rows
            for entry in leaderboard:
                strategy_name = entry['strategy_name'][:19] if entry['strategy_name'] else "N/A"
                family = entry['family'][:11] if entry['family'] else "N/A"
                status = entry['status'][:7] if entry['status'] else "N/A"

                row = [
                    f"{entry['rank']}",
                    strategy_name,
                    family,
                    status,
                    f"{entry['score']:.1f}",
                    ".2f",
                    ".1%",
                    ".1%",
                    ".0%",
                    f"{entry.get('total_trades', 0)}" if entry.get('total_trades') else "N/A",
                    ".2f" if entry.get('bias_selection') is not None else "N/A"
                ]
                print(" | ".join(f"{cell:<{width}}" for cell, width in zip(row, col_widths)))
        else:
            # Simple format for ops/daily monitoring
            print("<4")
            print("-" * 40)

            for i, entry in enumerate(leaderboard, 1):
                strategy_name = entry['strategy_name'] or "Unknown"
                score = entry['score']
                sharpe = entry.get('sharpe_ratio', 0)
                total_return = entry.get('total_return', 0)
                max_dd = entry.get('max_drawdown', 0)

                print(
                    "<4"
                    "<20"  # Increased width for strategy name
                    ".2f"
                    ".1%"
                )

                # Additional metrics for daily monitoring
                if entry.get('win_rate') is not None:
                    print("8"                  ".0%"                  f"{entry.get('total_trades', 'N/A')} trades")
                if entry.get('bias_selection') is not None and abs(entry['bias_selection']) > 0.01:
                    print("8"                ".3f")

                if i < len(leaderboard):
                    print()

    def _parse_param_ranges(self, params_str: str) -> Dict[str, List[int]]:
        """Parse parameter range string like 'fast:5-20,slow:30-100'"""
        ranges = {}
        for param in params_str.split(','):
            name, range_str = param.split(':')
            start, end = range_str.split('-')
            ranges[name.strip()] = list(range(int(start), int(end) + 1))
        return ranges

    def _generate_reports(self, results: dict, args):
        """Generate reports in requested formats"""
        # Always generate JSON for programmatic access
        json_reporter = JSONReporter()
        json_path = json_reporter.generate(results, args.output_dir)

        # Terminal output
        if not args.quiet:
            terminal_reporter = TerminalReporter()
            terminal_reporter.generate(results)

        # HTML report
        if args.format == 'html' or args.format == 'all':
            html_reporter = HTMLReporter()
            html_path = html_reporter.generate(results, args.output_dir)
            print(f"📄 HTML report: {html_path}")

        print(f"💾 Results saved to: {json_path}")

    def run(self) -> int:
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="StratVal - AI-powered trading strategy validation system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  stratval create "RSI oversold bounce strategy" --output rsi_strategy.cpp
  stratval validate strategy.cpp --data BTC_1h.txt --mode thorough
  stratval optimize strategy.cpp --data BTC_1h.txt --params "rsi_period:10-20,threshold:20-40"
  stratval report results.json --format html
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Create command
        create_parser = subparsers.add_parser('create', help='Create new strategy')
        create_parser.add_argument('description', help='Natural language strategy description')
        create_parser.add_argument('--output', '-o', required=True, help='Output file path')
        create_parser.add_argument('--validate', '-v', action='store_true', help='Validate after creation')

        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate existing strategy')
        validate_parser.add_argument('strategy', help='Strategy file path')
        validate_parser.add_argument('--data', '-d', help='Market data file (optional when using database)')
        validate_parser.add_argument('--pair', help='Trading pair to fetch from the database (e.g., BTC/USDT)')
        validate_parser.add_argument('--timeframe', help='Timeframe to fetch from the database (e.g., 1h, 4h)')
        validate_parser.add_argument('--mode', '-m', choices=['quick', 'standard', 'thorough'],
                                   default='standard', help='Validation thoroughness')
        validate_parser.add_argument('--output-dir', default='./reports', help='Output directory')
        validate_parser.add_argument('--format', choices=['terminal', 'html', 'json', 'all'],
                                   default='terminal', help='Report format')
        validate_parser.add_argument('--quiet', '-q', action='store_true', help='Suppress terminal output')

        # Optimize command
        optimize_parser = subparsers.add_parser('optimize', help='Optimize strategy parameters')
        optimize_parser.add_argument('strategy', help='Strategy file path')
        optimize_parser.add_argument('--data', '-d', required=True, help='Market data file')
        optimize_parser.add_argument('--params', '-p', required=True, help='Parameter ranges (e.g., "fast:5-20,slow:30-100")')
        optimize_parser.add_argument('--optimize-for', default='sharpe', choices=['sharpe', 'return', 'calmar'],
                                   help='Optimization target')
        optimize_parser.add_argument('--output-dir', default='./reports', help='Output directory')

        # Report command
        report_parser = subparsers.add_parser('report', help='Generate report from results')
        report_parser.add_argument('results', help='Results JSON file')
        report_parser.add_argument('--format', '-f', default='terminal',
                                  help='Report format (terminal, html, json, all)')
        report_parser.add_argument('--output', '-o', help='Output file path')

        # Leaderboard command
        leaderboard_parser = subparsers.add_parser('leaderboard', help='Show strategy leaderboard')
        leaderboard_parser.add_argument('--top', '-t', type=int, default=10,
                                       help='Show top N strategies (default: 10)')
        leaderboard_parser.add_argument('--status', '-s', choices=['active', 'candidate', 'retired'],
                                       help='Filter by status')
        leaderboard_parser.add_argument('--family', '-f', help='Filter by strategy family')
        leaderboard_parser.add_argument('--summary', action='store_true',
                                       help='Show summary statistics instead of detailed list')
        leaderboard_parser.add_argument('--detailed', action='store_true',
                                       help='Show detailed tabular format')

        # Parse arguments
        if len(sys.argv) == 1:
            parser.print_help()
            return 0

        args = parser.parse_args()

        # Execute command
        if args.command == 'create':
            return self.create_strategy(args)
        elif args.command == 'validate':
            return self.validate_strategy(args)
        elif args.command == 'optimize':
            return self.optimize_strategy(args)
        elif args.command == 'report':
            return self.generate_report(args)
        elif args.command == 'leaderboard':
            return self.show_leaderboard(args)
        else:
            parser.print_help()
            return 1


def main():
    """Entry point"""
    cli = StratValCLI()
    exit_code = cli.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
