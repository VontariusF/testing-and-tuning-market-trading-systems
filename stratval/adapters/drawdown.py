"""
DRAWDOWN algorithm adapter
Monte Carlo drawdown analysis
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("DRAWDOWN")
class DrawdownAdapter(AlgorithmAdapter):
    """Adapter for DRAWDOWN algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare returns data file for DRAWDOWN

        DRAWDOWN generates its own synthetic returns data, so we don't need
        to provide actual strategy returns - just the count of returns.
        """
        # DRAWDOWN generates synthetic returns internally, but we need to
        # provide the number of returns to analyze
        returns = DataFormat.extract_returns_from_strategy(strategy_results)

        if not returns:
            # Default to reasonable size if no returns found
            n_returns = 252  # One year of daily returns
        else:
            n_returns = len(returns)

        # Create a dummy input file (DRAWDOWN doesn't actually read from it)
        temp_dir = kwargs.get('temp_dir', '.')
        input_file = Path(temp_dir) / "dummy_input.txt"

        with open(input_file, 'w') as f:
            f.write(f"{n_returns}\n")

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for DRAWDOWN

        Expected format: DRAWDOWN Nchanges Ntrades WinProb BoundConf BootstrapReps QuantileReps TestReps
        """
        # Extract parameters or use defaults optimized for performance
        n_changes = kwargs.get('n_changes', 252)    # Reduced for faster testing
        n_trades = kwargs.get('n_trades', 252)      # One year of trades
        win_prob = kwargs.get('win_prob', 0.5)      # 50% win rate
        bound_conf = kwargs.get('bound_conf', 0.95)  # 95% confidence
        bootstrap_reps = kwargs.get('bootstrap_reps', 100)  # Reduced for faster testing
        quantile_reps = kwargs.get('quantile_reps', 100)    # Reduced for faster testing
        test_reps = kwargs.get('test_reps', 10)             # Reduced for faster testing

        return [
            self.executable_path,
            str(n_changes),
            str(n_trades),
            str(win_prob),
            str(bound_conf),
            str(bootstrap_reps),
            str(quantile_reps),
            str(test_reps)
        ]

    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse DRAWDOWN output

        Expected output includes drawdown quantiles and confidence intervals
        """
        results = {
            "algorithm": "DRAWDOWN",
            "drawdown_001": None,
            "drawdown_01": None,
            "drawdown_05": None,
            "drawdown_10": None,
            "confidence_001": None,
            "confidence_01": None,
            "confidence_05": None,
            "confidence_10": None,
            "mean_return_bounds": {},
            "drawdown_bounds": {}
        }

        try:
            with open(output_file, 'r') as f:
                content = f.read()

            # Parse drawdown quantiles
            patterns = {
                "drawdown_001": r"0\.001\s+([\d\-\.]+)\s+([\d\-\.]+)",
                "drawdown_01": r"0\.01\s+([\d\-\.]+)\s+([\d\-\.]+)",
                "drawdown_05": r"0\.05\s+([\d\-\.]+)\s+([\d\-\.]+)",
                "drawdown_10": r"0\.1\s+([\d\-\.]+)\s+([\d\-\.]+)"
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    incorrect_val = float(match.group(1))
                    correct_val = float(match.group(2))

                    # Store both incorrect and correct bounds
                    results[f"{key}_incorrect"] = incorrect_val
                    results[f"{key}_correct"] = correct_val

                    # For main key, use the correct method
                    if key == "drawdown_001":
                        results["drawdown_001"] = correct_val
                    elif key == "drawdown_01":
                        results["drawdown_01"] = correct_val
                    elif key == "drawdown_05":
                        results["drawdown_05"] = correct_val
                    elif key == "drawdown_10":
                        results["drawdown_10"] = correct_val

        except Exception as e:
            results["parse_error"] = str(e)

        return results

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse DRAWDOWN results from stdout"""
        results = {
            "algorithm": "DRAWDOWN",
            "raw_output": stdout
        }

        try:
            lines = stdout.strip().split('\n')

            # Look for the summary table in stdout
            for line in lines:
                if 'Drawdown' in line and 'Actual' in line and 'Incorrect' in line:
                    # This is the header line
                    continue
                elif re.match(r'\s*0\.\d+', line):
                    # This is a data line
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 3:
                        quantile = parts[0]
                        incorrect = float(parts[1])
                        correct = float(parts[2])

                        key = f"drawdown_{quantile.replace('.', '')}"
                        results[f"{key}_incorrect"] = incorrect
                        results[f"{key}_correct"] = correct

                        # Store main value using correct method
                        results[key] = correct

        except Exception as e:
            results["parse_error"] = str(e)

        return results

    def get_drawdown_bounds(self, confidence_level: float = 0.95) -> Dict[str, float]:
        """Get drawdown confidence bounds for specified confidence level

        Args:
            confidence_level: Confidence level (0.95 = 95%)

        Returns:
            Dictionary with drawdown bounds
        """
        # This would be called after execution to extract bounds
        # For now, return placeholder structure
        return {
            "99th_percentile": None,
            "95th_percentile": None,
            "90th_percentile": None,
            "confidence_level": confidence_level
        }
