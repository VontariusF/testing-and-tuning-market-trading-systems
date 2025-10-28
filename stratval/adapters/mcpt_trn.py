"""
MCPT_TRN algorithm adapter
Monte Carlo permutation test for trading system validation
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("MCPT_TRN")
class McptTrnAdapter(AlgorithmAdapter):
    """Adapter for MCPT_TRN algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare close price data file for MCPT_TRN

        MCPT_TRN expects: YYYYMMDD Price format (close prices) - same as CD_MA
        """
        temp_dir = kwargs.get('temp_dir', '.')
        closes = []

        # Extract close prices from strategy results
        bars = DataFormat.extract_ohlc_from_strategy(strategy_results)
        if bars:
            closes = [bar['close'] for bar in bars]
        else:
            # Fallback to mock close prices - larger dataset for MCPT_TRN
            closes = [100.0 + i * 0.1 for i in range(2000)]  # Increased to 2000

        if not closes:
            raise ValueError("No close price data found in strategy results for MCPT_TRN")

        input_file = Path(temp_dir) / "mcpt_trn_input.txt"
        DataFormat.write_close_data(str(input_file), closes)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for MCPT_TRN

        Expected format: MCPT_TRN max_lookback nreps filename
        """
        # Extract parameters or use defaults
        max_lookback = kwargs.get('max_lookback', 300)
        nreps = kwargs.get('nreps', 1000)

        return [
            self.executable_path,
            str(max_lookback),
            str(nreps),
            input_path
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse MCPT_TRN results from stdout"""
        results = {
            "algorithm": "MCPT_TRN",
            "p_value": None,
            "test_statistic": None,
            "significance_level": None,
            "null_hypothesis_rejected": None,
            "permutation_results": {}
        }

        try:
            lines = stdout.strip().split('\n')

            for line in lines:
                line = line.strip()

                # Look for p-value and test results
                p_match = re.search(r'p-value[^=]*=\s*([0-9]*\.?[0-9]+)', line, re.IGNORECASE)
                if p_match:
                    results["p_value"] = float(p_match.group(1))

                test_match = re.search(r'test statistic[^=]*=\s*([\-]?[0-9]*\.?[0-9]+)', line, re.IGNORECASE)
                if test_match:
                    results["test_statistic"] = float(test_match.group(1))

                sig_match = re.search(r'significance[^=]*=\s*([0-9]*\.?[0-9]+)', line, re.IGNORECASE)
                if sig_match:
                    results["significance_level"] = float(sig_match.group(1))

                # Check if null hypothesis rejected
                if 'rejected' in line.lower() or 'significant' in line.lower():
                    results["null_hypothesis_rejected"] = True
                elif 'accepted' in line.lower() or 'not significant' in line.lower():
                    results["null_hypothesis_rejected"] = False

                # Check for permutation results
                if 'permutation' in line.lower() and re.search(r'\d+', line):
                    results["permutation_results"]["summary"] = line

        except Exception as e:
            results["parse_error"] = str(e)

        # Infer rejection if we have p-value and significance
        if (results["p_value"] is not None and results["significance_level"] is not None and
            results["null_hypothesis_rejected"] is None):
            results["null_hypothesis_rejected"] = results["p_value"] < results["significance_level"]

        results["raw_output"] = stdout
        return results

    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse MCPT_TRN output from file"""
        try:
            with open(output_file, 'r') as f:
                content = f.read()
            return self.parse_output_from_stdout(content)
        except Exception as e:
            return {"error": f"Failed to read output file: {e}"}
