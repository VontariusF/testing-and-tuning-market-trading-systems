"""
MCPT_BARS algorithm adapter
Monte Carlo Permutation Test for bar-based strategies
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("MCPT_BARS")
class MCPTBarsAdapter(AlgorithmAdapter):
    """Adapter for MCPT_BARS algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare OHLC data file for MCPT_BARS

        MCPT_BARS expects: YYYYMMDD Open High Low Close format
        """
        temp_dir = kwargs.get('temp_dir', '.')
        bars = DataFormat.extract_ohlc_from_strategy(strategy_results)

        if not bars:
            # Create minimal test data for MCPT_BARS
            print("   No OHLC data found, creating minimal test data for MCPT_BARS")
            bars = []
            for i in range(100):  # Create 100 bars of test data
                date = 20200101 + i
                base_price = 100.0 + i * 0.1
                bars.append({
                    'date': date,
                    'open': base_price,
                    'high': base_price + 1.0,
                    'low': base_price - 1.0,
                    'close': base_price + 0.5
                })

        input_file = Path(temp_dir) / "market_data.txt"
        DataFormat.write_ohlc_data(str(input_file), bars)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for MCPT_BARS

        Expected format: MCPT_BARS lookback nreps filename
        """
        # Get data size and set appropriate lookback
        strategy_results = kwargs.get('strategy_results', {})
        bars = DataFormat.extract_ohlc_from_strategy(strategy_results)
        data_size = len(bars) if bars else 100

        # Lookback must be at least 10 less than data size
        max_lookback = data_size - 10
        lookback = min(kwargs.get('lookback', 50), max_lookback)  # Default to 50 or less
        nreps = kwargs.get('nreps', 100)  # Reduced for faster testing

        return [
            self.executable_path,
            str(lookback),
            str(nreps),
            input_path
        ]

    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse MCPT_BARS output

        Expected output format includes:
        - p-value for null hypothesis
        - Original return
        - Trend component
        - Training bias
        - Skill estimate
        - Unbiased return
        """
        results = {
            "algorithm": "MCPT_BARS",
            "pvalue": None,
            "original_return": None,
            "trend_component": None,
            "training_bias": None,
            "skill": None,
            "unbiased_return": None,
            "nlong": None
        }

        try:
            with open(output_file, 'r') as f:
                content = f.read()

            # Parse key metrics using regex
            patterns = {
                "pvalue": r"p-value for null hypothesis that system is worthless = (\d+\.\d+)",
                "original_return": r"Original return = ([\d\-\.]+)",
                "trend_component": r"Trend component = ([\d\-\.]+)",
                "training_bias": r"Training bias = ([\d\-\.]+)",
                "skill": r"Skill = ([\d\-\.]+)",
                "unbiased_return": r"Unbiased return = ([\d\-\.]+)",
                "nlong": r"Original nlong = (\d+)"
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    value = match.group(1)
                    # Convert to appropriate type
                    if key in ['pvalue']:
                        results[key] = float(value)
                    elif key in ['nlong']:
                        results[key] = int(value)
                    else:
                        results[key] = float(value)

        except Exception as e:
            results["parse_error"] = str(e)

        return results

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse MCPT_BARS results from stdout"""
        # MCPT_BARS outputs results to both stdout and .LOG file
        # Try to extract key metrics from stdout
        results = {
            "algorithm": "MCPT_BARS",
            "raw_output": stdout
        }

        try:
            lines = stdout.strip().split('\n')
            for line in lines:
                if 'p-value' in line and 'null hypothesis' in line:
                    # Extract p-value
                    match = re.search(r'(\d+\.\d+)', line)
                    if match:
                        results["pvalue"] = float(match.group(1))
                elif 'Original return' in line:
                    match = re.search(r'([\d\-\.]+)', line)
                    if match:
                        results["original_return"] = float(match.group(1))
                elif 'Skill' in line:
                    match = re.search(r'([\d\-\.]+)', line)
                    if match:
                        results["skill"] = float(match.group(1))

        except Exception as e:
            results["parse_error"] = str(e)

        return results
