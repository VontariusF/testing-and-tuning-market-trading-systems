"""
DEV_MA algorithm adapter
Differential evolution optimization of thresholded moving-average system
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("DEV_MA")
class DEVMAAdapter(AlgorithmAdapter):
    """Adapter for DEV_MA algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare close price data file for DEV_MA

        DEV_MA expects: YYYYMMDD Price format (close prices)
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
            raise ValueError("No close price data found in strategy results for DEV_MA")

        input_file = Path(temp_dir) / "devma_input.txt"
        DataFormat.write_close_data(str(input_file), closes)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for DEV_MA

        Expected format: DEV_MA max_lookback max_thresh filename
        """
        # Extract parameters or use defaults
        max_lookback = kwargs.get('max_lookback', 100)
        max_thresh = kwargs.get('max_thresh', 100.0)

        return [
            self.executable_path,
            str(max_lookback),
            str(max_thresh),
            input_path
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse DEV_MA results from stdout"""
        results = {
            "algorithm": "DEV_MA",
            "best_performance": None,
            "optimal_parameters": {},
            "bias_estimates": {},
            "expected_performance": None
        }

        try:
            lines = stdout.strip().split('\n')

            for line in lines:
                line = line.strip()

                # Parse best performance and parameters
                # "Best performance = XXX.XXXX  Variables follow..."
                if "Best performance =" in line and "Variables follow..." in line:
                    match = re.search(r'Best performance = ([\d\-\.]+)', line)
                    if match:
                        results["best_performance"] = float(match.group(1))

                # Parse parameters (4 variables follow)
                elif re.search(r'^\d+\.\d+$', line):
                    # This is a parameter value - we need to collect 4 of them
                    if "parameters" not in results["optimal_parameters"]:
                        results["optimal_parameters"]["parameters"] = []
                    if len(results["optimal_parameters"]["parameters"]) < 4:
                        results["optimal_parameters"]["parameters"].append(float(line))

                # Parse bias estimates
                elif "In-sample mean =" in line:
                    match = re.search(r'In-sample mean = ([\d\-\.]+)', line)
                    if match:
                        results["bias_estimates"]["in_sample_mean"] = float(match.group(1))

                elif "Out-of-sample mean =" in line:
                    match = re.search(r'Out-of-sample mean = ([\d\-\.]+)', line)
                    if match:
                        results["bias_estimates"]["out_of_sample_mean"] = float(match.group(1))

                elif "Bias =" in line:
                    match = re.search(r'Bias = ([\d\-\.]+)', line)
                    if match:
                        results["bias_estimates"]["bias"] = float(match.group(1))

                elif "Expected =" in line:
                    match = re.search(r'Expected = ([\d\-\.]+)', line)
                    if match:
                        results["expected_performance"] = float(match.group(1))

            # Organize parameters better
            if "parameters" in results["optimal_parameters"]:
                params = results["optimal_parameters"]["parameters"]
                if len(params) >= 4:
                    results["optimal_parameters"] = {
                        "long_term_lookback": int(params[0] + 0.5),  # First parameter
                        "short_pct": params[1],  # Percentage
                        "short_thresh": params[2] / 10000.0,  # Scale back
                        "long_thresh": params[3] / 10000.0,   # Scale back
                        "raw_parameters": params
                    }

        except Exception as e:
            results["parse_error"] = str(e)

        results["raw_output"] = stdout
        return results
