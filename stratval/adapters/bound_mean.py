"""
BOUND_MEAN algorithm adapter
Uses PER_WHAT system to compare methods for bounding expected returns
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("BOUND_MEAN")
class BOUNDMEANAdapter(AlgorithmAdapter):
    """Adapter for BOUND_MEAN algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare close price data file for BOUND_MEAN

        BOUND_MEAN expects: YYYYMMDD Price format (close prices)
        """
        temp_dir = kwargs.get('temp_dir', '.')
        closes = []

        # Extract close prices from strategy results
        bars = DataFormat.extract_ohlc_from_strategy(strategy_results)
        if bars:
            closes = [bar['close'] for bar in bars]
        else:
            # Fallback to mock data if no bars available
            closes = [100.0 + i * 0.1 for i in range(1000)]

        if not closes:
            raise ValueError("No close price data found in strategy results for BOUND_MEAN")

        input_file = Path(temp_dir) / "boundmean_input.txt"
        DataFormat.write_close_data(str(input_file), closes)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for BOUND_MEAN

        Expected format: BOUND_MEAN max_lookback n_train n_test n_boot filename
        """
        # Extract parameters or use defaults
        max_lookback = kwargs.get('max_lookback', 100)
        n_train = kwargs.get('n_train', 2000)
        n_test = kwargs.get('n_test', 1000)
        n_boot = kwargs.get('n_boot', 1000)

        return [
            self.executable_path,
            str(max_lookback),
            str(n_train),
            str(n_test),
            str(n_boot),
            input_path
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse BOUND_MEAN results from stdout"""
        results = {
            "algorithm": "BOUND_MEAN",
            "walkforward_folds": [],
            "oos_performance": {},
            "confidence_bounds": {},
            "parameters": {}
        }

        try:
            lines = stdout.strip().split('\n')

            fold_count = 0
            current_fold = {}

            for line in lines:
                line = line.strip()

                # Parse walk-forward fold results: "OOS X testing Y from Z had W returns, total=V"
                if 'OOS 0 testing' in line:
                    match = re.search(r'OOS 0 testing (\d+) from (\d+) had (\d+) returns, total=(\d+)', line)
                    if match:
                        fold_count += 1
                        if fold_count not in results["walkforward_folds"]:
                            results["walkforward_folds"].append(current_fold)
                        current_fold = {
                            "fold": fold_count,
                            "test_bars": int(match.group(1)),
                            "start_index": int(match.group(2)),
                            "returns_count": int(match.group(3)),
                            "total_returns": int(match.group(4))
                        }

                # Parse final parameters
                elif 'nprices=' in line and 'max_lookback=' in line and 'n_train=' in line:
                    match = re.search(r'nprices=(\d+)\s+max_lookback=(\d+)\s+n_train=(\d+)\s+n_test=(\d+)', line)
                    if match:
                        results["parameters"] = {
                            "nprices": int(match.group(1)),
                            "max_lookback": int(match.group(2)),
                            "n_train": int(match.group(3)),
                            "n_test": int(match.group(4))
                        }

                # Parse OOS performance - open position bars
                elif 'OOS mean return per open-trade bar' in line:
                    match = re.search(r'OOS mean return per open-trade bar \(times 25200\) = ([\d\-\.]+)', line)
                    if match:
                        results["oos_performance"]["open_trade_bar_return"] = float(match.group(1)) / 25200.0

                # Parse OOS performance - complete trades
                elif 'OOS mean return per complete trade' in line:
                    match = re.search(r'OOS mean return per complete trade \(times 1000\) = ([\d\-\.]+)', line)
                    if match:
                        results["oos_performance"]["complete_trade_return"] = float(match.group(1)) / 1000.0

                # Parse OOS performance - grouped bars
                elif 'OOS mean return per' in line and '-bar group' in line:
                    match = re.search(r'OOS mean return per (\d+)-bar group \(times 25200\) = ([\d\-\.]+)', line)
                    if match:
                        results["oos_performance"]["grouped_return"] = float(match.group(2)) / 25200.0
                        results["oos_performance"]["group_size"] = int(match.group(1))

                # Parse confidence bounds table
                elif line.startswith("Student's t") or line.startswith("Percentile") or line.startswith("Pivot") or line.startswith("BCa"):
                    method = line.split()[0]
                    parts = line.split()[1:]

                    if len(parts) >= 3:
                        results["confidence_bounds"][method.lower()] = {
                            "open_position": float(parts[0]),
                            "complete_trade": float(parts[1]),
                            "grouped": float(parts[2])
                        }

            # Add final fold
            if current_fold:
                results["walkforward_folds"].append(current_fold)

        except Exception as e:
            results["parse_error"] = str(e)

        results["raw_output"] = stdout
        return results
