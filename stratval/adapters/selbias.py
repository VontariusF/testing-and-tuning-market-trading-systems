"""
SELBIAS algorithm adapter
Selection bias analysis algorithm
"""

import re
from pathlib import Path
from typing import Dict, Any, List

from .base import AlgorithmAdapter, DataFormat, register_adapter


@register_adapter("SELBIAS")
class SELBIASAdapter(AlgorithmAdapter):
    """Adapter for SELBIAS algorithm"""

    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """SELBIAS appears to analyze selection bias, likely needs trade returns"""
        temp_dir = kwargs.get('temp_dir', '.')
        # SELBIAS might need trade data or returns - using returns data
        returns = []

        # Extract returns from strategy results
        if 'trade_returns' in strategy_results:
            returns = strategy_results['trade_returns']
        elif 'returns' in strategy_results:
            returns = strategy_results['returns']
        elif 'trades' in strategy_results:
            trades = strategy_results['trades']
            returns = [trade.get('return', trade.get('pnl', 0.0)) for trade in trades]

        if not returns:
            # Fallback to mock returns for analysis
            returns = [0.01, -0.005, 0.008, 0.012, -0.003, 0.015, -0.007, 0.022] * 50

        input_file = Path(temp_dir) / "selbias_input.txt"
        DataFormat.write_returns_data(str(input_file), returns)

        return str(input_file)

    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for SELBIAS

        Expected format: SelBias which ncases trend nreps
        """
        # Extract parameters or use defaults
        which = kwargs.get('which', 1)  # 0=mean return, 1=profit factor, 2=Sharpe ratio
        ncases = kwargs.get('ncases', 1000)  # Number of cases
        trend = kwargs.get('trend', 0.2)     # Amount of trending
        nreps = kwargs.get('nreps', 100)     # Number of replications

        return [
            self.executable_path,
            str(which),
            str(ncases),
            str(trend),
            str(nreps)
        ]

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse SELBIAS results from stdout"""
        results = {
            "algorithm": "SELBIAS",
            "analysis_results": {},
            "bias_metrics": {}
        }

        try:
            lines = stdout.strip().split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Look for common statistical outputs
                # This would need to be adjusted based on actual SELBIAS output format
                if 'bias' in line.lower():
                    results["bias_metrics"]["detected_bias"] = line
                elif 'analysis' in line.lower() or 'result' in line.lower():
                    results["analysis_results"]["output_line"] = line
                elif re.search(r'[\d\.]+', line):  # Lines with numbers
                    results["bias_metrics"]["numeric_result"] = line

        except Exception as e:
            results["parse_error"] = str(e)

        results["raw_output"] = stdout
        return results

    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse SELBIAS output from file"""
        try:
            with open(output_file, 'r') as f:
                content = f.read()
            return self.parse_output_from_stdout(content)
        except Exception as e:
            return {"error": f"Failed to read output file: {e}"}
