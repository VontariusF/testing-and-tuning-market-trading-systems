"""
BND_RET algorithm adapter
Uses moving-average-crossover system to demonstrate bounding future returns
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("BND_RET")
class BNDRETAdapter(AlgorithmAdapter):
    """Adapter for BND_RET algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare close price data file for BND_RET

        BND_RET expects: YYYYMMDD Price format (close prices)
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
            raise ValueError("No close price data found in strategy results for BND_RET")

        input_file = Path(temp_dir) / "bndret_input.txt"
        DataFormat.write_close_data(str(input_file), closes)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for BND_RET

        Expected format: BND_RET max_lookback n_train n_test lower_fail upper_fail p_of_q filename
        """
        # Extract parameters or use defaults
        max_lookback = kwargs.get('max_lookback', 100)
        n_train = kwargs.get('n_train', 1000)
        n_test = kwargs.get('n_test', 63)
        lower_fail = kwargs.get('lower_fail', 0.1)
        upper_fail = kwargs.get('upper_fail', 0.4)
        p_of_q = kwargs.get('p_of_q', 0.05)

        return [
            self.executable_path,
            str(max_lookback),
            str(n_train),
            str(n_test),
            str(lower_fail),
            str(upper_fail),
            str(p_of_q),
            input_path
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse BND_RET results from stdout"""
        results = {
            "algorithm": "BND_RET",
            "mean_oos_return": None,
            "n_folds": 0,
            "lower_bound": None,
            "upper_bound": None,
            "lower_bound_fail_rate": None,
            "upper_bound_fail_rate": None
        }

        try:
            lines = stdout.strip().split('\n')

            # Look for key metrics in stdout
            for line in lines:
                line = line.strip()

                # Parse mean OOS return: "mean OOS = XXX.XXX with Y returns"
                if 'mean OOS =' in line and 'with' in line:
                    match = re.search(r'mean OOS = ([\d\-\.]+) with (\d+)', line)
                    if match:
                        results["mean_oos_return"] = float(match.group(1))
                        results["n_folds"] = int(match.group(2))

                # Parse lower bound: "LOWER bound on future returns is XXX.XXX"
                elif 'LOWER bound on future returns is' in line:
                    match = re.search(r'LOWER bound on future returns is ([\d\-\.]+)', line)
                    if match:
                        results["lower_bound"] = float(match.group(1))

                # Parse upper bound: "UPPER bound on future returns is XXX.XXX"
                elif 'UPPER bound on future returns is' in line:
                    match = re.search(r'UPPER bound on future returns is ([\d\-\.]+)', line)
                    if match:
                        results["upper_bound"] = float(match.group(1))

                # Parse failure rates
                elif 'failure rate of' in line:
                    match = re.search(r'failure rate of ([\d\.]+) %', line)
                    if match and results.get("lower_bound_fail_rate") is None:
                        results["lower_bound_fail_rate"] = float(match.group(1))
                    elif match and results.get("upper_bound_fail_rate") is None:
                        results["upper_bound_fail_rate"] = float(match.group(1))

        except Exception as e:
            results["parse_error"] = str(e)

        results["raw_output"] = stdout
        return results
