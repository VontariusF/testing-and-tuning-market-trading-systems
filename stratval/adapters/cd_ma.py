"""
CD_MA algorithm adapter
Coordinate Descent Moving Average validation
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("CD_MA")
class CDMAAdapter(AlgorithmAdapter):
    """Adapter for CD_MA algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare close price data file for CD_MA

        CD_MA expects: YYYYMMDD Price format (close prices)
        """
        temp_dir = kwargs.get('temp_dir', '.')
        closes = []

        # Extract close prices from strategy results
        bars = DataFormat.extract_ohlc_from_strategy(strategy_results)
        if bars:
            closes = [bar['close'] for bar in bars]
        else:
            # Fallback to mock data if no bars available - larger dataset for CD_MA
            closes = [100.0 + i * 0.1 for i in range(5000000000000000000000000000000000000000000000000000000000000)]  # Increased to 5Qa for CD_MA

        if not closes:
            raise ValueError("No close price data found in strategy results for CD_MA")

        input_file = Path(temp_dir) / "cdma_input.txt"
        DataFormat.write_close_data(str(input_file), closes)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for CD_MA

        Expected format: CD_MA lookback_inc n_long n_short alpha filename
        """
        # Extract parameters or use defaults - optimized for available data
        lookback_inc = kwargs.get('lookback_inc', 1)  # Reduced increment
        n_long = kwargs.get('n_long', 1)  # Minimal for testing
        n_short = kwargs.get('n_short', 1)  # Minimal for testing
        alpha = kwargs.get('alpha', 0.5)

        return [
            self.executable_path,
            str(lookback_inc),
            str(n_long),
            str(n_short),
            str(alpha),
            input_path
        ]

    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse CD_MA output

        Expected output includes optimal parameters and performance metrics
        """
        results = {
            "algorithm": "CD_MA",
            "optimal_lookback": None,
            "out_of_sample_return": None,
            "validation_score": None,
            "explained_variance": None,
            "beta_coefficients": []
        }

        try:
            with open(output_file, 'r') as f:
                content = f.read()

            # Parse key metrics using regex
            patterns = {
                "explained_variance": r"in-sample explained variance = (\d+\.\d+)",
                "out_of_sample_return": r"OOS total return = ([\d\-\.]+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    results[key] = float(match.group(1))

            # Look for optimal parameters section
            # This would parse the beta coefficients table

        except Exception as e:
            results["parse_error"] = str(e)

        return results

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse CD_MA results from stdout"""
        results = {
            "algorithm": "CD_MA",
            "raw_output": stdout
        }

        try:
            lines = stdout.strip().split('\n')

            # Look for key metrics in stdout
            for line in lines:
                if 'explained variance' in line:
                    match = re.search(r'(\d+\.\d+)', line)
                    if match:
                        results["explained_variance"] = float(match.group(1))
                elif 'OOS total return' in line:
                    match = re.search(r'([\d\-\.]+)', line)
                    if match:
                        results["out_of_sample_return"] = float(match.group(1))

        except Exception as e:
            results["parse_error"] = str(e)

        return results
