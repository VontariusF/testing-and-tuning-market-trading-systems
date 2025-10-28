"""
BOOT_RATIO algorithm adapter
Bootstrap confidence intervals for profit factor and Sharpe ratio
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, register_adapter


@register_adapter("BOOT_RATIO")
class BOOTRATIOAdapter(AlgorithmAdapter):
    """Adapter for BOOT_RATIO algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """BOOT_RATIO generates its own synthetic trade data, no external input needed"""
        temp_dir = kwargs.get('temp_dir', '.')
        return str(Path(temp_dir) / "boot_ratio_input.txt")  # Placeholder, not used

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for BOOT_RATIO

        Expected format: BOOT_RATIO nsamples nboot ntries prob
        """
        # Extract parameters or use defaults
        nsamples = kwargs.get('nsamples', 1000)
        nboot = kwargs.get('nboot', 10)
        ntries = kwargs.get('ntries', 100)
        prob = kwargs.get('prob', 0.7)

        return [
            self.executable_path,
            str(nsamples),
            str(nboot),
            str(ntries),
            str(prob)
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse BOOT_RATIO results from stdout"""
        results = {
            "algorithm": "BOOT_RATIO",
            "profit_factor_results": {},
            "sharpe_ratio_results": {},
            "parameters": {}
        }

        try:
            lines = stdout.strip().split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                # Parse parameters
                if 'nsamps=' in line and 'nboot=' in line and 'ntries=' in line and 'prob=' in line:
                    # nsamps=1000  nboot=10  ntries=100  prob=0.700
                    match = re.search(r'nsamps=(\d+)\s+nboot=(\d+)\s+ntries=(\d+)\s+prob=([\d\.]+)', line)
                    if match:
                        results["parameters"] = {
                            "nsamples": int(match.group(1)),
                            "nboot": int(match.group(2)),
                            "ntries": int(match.group(3)),
                            "prob": float(match.group(4))
                        }

                # Detect profit factor section
                if 'Final profit factor...' in line:
                    current_section = "profit_factor"

                # Detect Sharpe ratio section
                elif 'Final Sharpe ratio...' in line:
                    current_section = "sharpe_ratio"

                # Parse summary statistics
                if 'Mean' in line and 'true =' in line:
                    if 'log pf =' in line:
                        match = re.search(r'Mean log pf = ([\d\-\.]+) true = ([\d\-\.]+)', line)
                        if match:
                            results[current_section]["mean_log_pf"] = float(match.group(1))
                            results[current_section]["true_log_pf"] = float(match.group(2))
                    elif 'sr =' in line:
                        match = re.search(r'Mean sr = ([\d\-\.]+) true = ([\d\-\.]+)', line)
                        if match:
                            results[current_section]["mean_sr"] = float(match.group(1))
                            results[current_section]["true_sr"] = float(match.group(2))

                # Parse confidence interval methods
                elif any(method in line for method in ['Pctile', 'BCa', 'Pivot']):
                    method = line.split()[0]
                    if current_section:
                        # Extract percentages: "Pctile 2.5: (X.XX Y.YY) 5: (X.XX Y.YY) 10: (X.XX Y.YY)"
                        parts = line.split(':')[1:]
                        if len(parts) >= 3:
                            results[current_section][f"{method.lower()}_2p5_coverage"] = parts[0].strip('() ')
                            results[current_section][f"{method.lower()}_5_coverage"] = parts[1].strip('() ')
                            results[current_section][f"{method.lower()}_10_coverage"] = parts[2].strip('() ')

        except Exception as e:
            results["parse_error"] = str(e)

        results["raw_output"] = stdout
        return results
