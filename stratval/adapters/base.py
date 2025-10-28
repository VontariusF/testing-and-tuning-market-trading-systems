"""
Base adapter framework for algorithm wrappers
"""

import os
import subprocess
import tempfile
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
import re
import json
from datetime import datetime

try:
    from stratval.utils.config import get_config
except ImportError:  # Allow direct script usage
    from utils.config import get_config


class AlgorithmAdapter(ABC):
    """Base class for algorithm adapters"""

    def __init__(self, algorithm_name: str):
        """Initialize adapter

        Args:
            algorithm_name: Name of the algorithm (e.g., 'MCPT_BARS')
        """
        self.algorithm_name = algorithm_name
        self.config = get_config()
        self.build_config = self.config.get_build_config()

        # Find executable path
        self.executable_path = self._find_executable()

        if not self.executable_path:
            raise FileNotFoundError(f"Could not find executable for {algorithm_name}")

    def _find_executable(self) -> Optional[str]:
        """Find the algorithm executable"""
        build_dir = self.build_config.get("algorithm_build_dir", "build")

        # Get the project root directory (parent of stratval)
        # Use resolve() so lookups succeed regardless of import context
        project_root = Path(__file__).resolve().parent.parent.parent

        # Look for executable in build directory from project root
        exe_path = project_root / build_dir / self.algorithm_name

        # Check common executable extensions
        for ext in ["", ".exe"]:
            full_path = exe_path.with_suffix(ext)
            if full_path.exists():
                return str(full_path)

        return None

    @abstractmethod
    def prepare_input(self, strategy_results: Dict[str, Any], **kwargs) -> str:
        """Prepare input file for algorithm

        Args:
            strategy_results: Results from strategy backtest
            **kwargs: Additional parameters

        Returns:
            Path to prepared input file
        """
        pass

    @abstractmethod
    def get_command_args(self, input_path: str, **kwargs) -> List[str]:
        """Get command line arguments for algorithm

        Args:
            input_path: Path to input file
            **kwargs: Additional parameters

        Returns:
            List of command arguments
        """
        pass

    @abstractmethod
    def parse_output(self, output_file: str) -> Dict[str, Any]:
        """Parse algorithm output

        Args:
            output_file: Path to algorithm output file

        Returns:
            Parsed results as dictionary
        """
        pass

    def execute(self, strategy_results: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute algorithm with strategy results

        Args:
            strategy_results: Results from strategy backtest
            **kwargs: Additional parameters

        Returns:
            Algorithm results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Prepare input file
            input_file = self.prepare_input(strategy_results, temp_dir=str(temp_path), **kwargs)

            # Get command arguments
            cmd_args = self.get_command_args(str(input_file), **kwargs)

            # Execute algorithm
            try:
                result = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=kwargs.get('timeout', 300),
                    cwd=str(temp_path)
                )

                if result.returncode != 0:
                    return {
                        "error": f"Algorithm {self.algorithm_name} failed with return code {result.returncode}",
                        "stdout": result.stdout,
                        "stderr": result.stderr
                    }

                # Parse output
                output_file = temp_path / f"{self.algorithm_name}.LOG"
                if output_file.exists():
                    return self.parse_output(str(output_file))
                else:
                    # Try to parse from stdout
                    return self.parse_output_from_stdout(result.stdout)

            except subprocess.TimeoutExpired:
                return {"error": f"Algorithm {self.algorithm_name} timed out"}

            except Exception as e:
                return {"error": f"Error executing {self.algorithm_name}: {str(e)}"}

    def parse_output_from_stdout(self, stdout: str) -> Dict[str, Any]:
        """Parse results from stdout if no output file

        Args:
            stdout: Algorithm stdout output

        Returns:
            Parsed results
        """
        # Default implementation - override in subclasses if needed
        return {
            "raw_output": stdout,
            "parsed_from_stdout": True
        }


class DataFormat:
    """Data format utilities"""

    @staticmethod
    def write_ohlc_data(file_path: str, bars: List[Dict]) -> None:
        """Write OHLC data in algorithm format

        Args:
            file_path: Output file path
            bars: List of OHLC bars with keys: date, open, high, low, close
        """
        with open(file_path, 'w') as f:
            for bar in bars:
                # Format: YYYYMMDD Open High Low Close
                date_value = bar.get('date')

                if not date_value and bar.get('timestamp') is not None:
                    timestamp = bar['timestamp']
                    try:
                        ts_int = int(float(timestamp))
                        if ts_int > 10**12:
                            ts_int //= 1000
                        date_value = datetime.utcfromtimestamp(ts_int).strftime('%Y%m%d')
                    except Exception:
                        date_value = None

                if not date_value:
                    date_value = bar.get('timestamp')

                if not date_value:
                    date_value = 19700101

                date_str = str(date_value)
                line = f"{date_str} {bar['open']:.6f} {bar['high']:.6f} {bar['low']:.6f} {bar['close']:.6f}\n"
                f.write(line)

    @staticmethod
    def write_close_data(file_path: str, closes: List[float]) -> None:
        """Write close price data in algorithm format

        Args:
            file_path: Output file path
            closes: List of close prices
        """
        with open(file_path, 'w') as f:
            for i, close in enumerate(closes):
                # Format: YYYYMMDD Price (use sequential dates)
                date = 20200101 + i  # Arbitrary starting date
                f.write(f"{date} {close:.6f}\n")

    @staticmethod
    def write_returns_data(file_path: str, returns: List[float]) -> None:
        """Write returns data for algorithms that need trade returns

        Args:
            file_path: Output file path
            returns: List of return values
        """
        with open(file_path, 'w') as f:
            for ret in returns:
                f.write(f"{ret:.6f}\n")

    @staticmethod
    def extract_ohlc_from_strategy(strategy_results: Dict[str, Any]) -> List[Dict]:
        """Extract OHLC bars from strategy results

        Args:
            strategy_results: Strategy backtest results

        Returns:
            List of OHLC bars
        """
        bars = []

        # Try different possible locations for OHLC data
        if 'ohlc_bars' in strategy_results:
            bars = strategy_results['ohlc_bars']
        elif 'bars' in strategy_results:
            bars = strategy_results['bars']
        elif 'market_data' in strategy_results:
            market_data = strategy_results['market_data']
            # Convert C++ Bar structure to Python dict format
            if market_data and isinstance(market_data, list):
                for bar_data in market_data:
                    if isinstance(bar_data, dict):
                        # Already in dict format
                        formatted_bar = {
                            'date': bar_data.get('date', 0),
                            'open': float(bar_data.get('open', 0)),
                            'high': float(bar_data.get('high', 0)),
                            'low': float(bar_data.get('low', 0)),
                            'close': float(bar_data.get('close', 0))
                        }
                        bars.append(formatted_bar)
                    elif hasattr(bar_data, '__dict__'):
                        # Convert object attributes to dict
                        formatted_bar = {
                            'date': getattr(bar_data, 'date', 0),
                            'open': float(getattr(bar_data, 'open', 0)),
                            'high': float(getattr(bar_data, 'high', 0)),
                            'low': float(getattr(bar_data, 'low', 0)),
                            'close': float(getattr(bar_data, 'close', 0))
                        }
                        bars.append(formatted_bar)

        # Ensure required fields exist for any remaining bars
        formatted_bars = []
        for bar in bars:
            if isinstance(bar, dict):
                formatted_bar = {
                    'date': bar.get('date', 0),
                    'timestamp': bar.get('timestamp'),
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0))
                }
                formatted_bars.append(formatted_bar)

        return formatted_bars

    @staticmethod
    def extract_returns_from_strategy(strategy_results: Dict[str, Any]) -> List[float]:
        """Extract trade returns from strategy results

        Args:
            strategy_results: Strategy backtest results

        Returns:
            List of return values
        """
        # Try different possible locations for returns
        if 'trade_returns' in strategy_results:
            return strategy_results['trade_returns']
        elif 'returns' in strategy_results:
            return strategy_results['returns']
        elif 'trades' in strategy_results:
            # Extract returns from trade data
            trades = strategy_results['trades']
            returns = []
            for trade in trades:
                if 'return' in trade:
                    returns.append(float(trade['return']))
                elif 'pnl' in trade:
                    returns.append(float(trade['pnl']))
            return returns

        return []

    @staticmethod
    def extract_equity_curve(strategy_results: Dict[str, Any]) -> List[float]:
        """Extract equity curve from strategy results

        Args:
            strategy_results: Strategy backtest results

        Returns:
            List of equity values over time
        """
        # Try different possible locations for equity curve
        if 'equity_curve' in strategy_results:
            return strategy_results['equity_curve']
        elif 'equity' in strategy_results:
            return strategy_results['equity']
        elif 'portfolio_value' in strategy_results:
            return strategy_results['portfolio_value']

        return []


class AlgorithmRegistry:
    """Registry for algorithm adapters"""

    _adapters = {}

    @classmethod
    def register(cls, algorithm_name: str, adapter_class):
        """Register an adapter class for an algorithm"""
        cls._adapters[algorithm_name] = adapter_class

    @classmethod
    def get_adapter(cls, algorithm_name: str) -> AlgorithmAdapter:
        """Get adapter instance for algorithm"""
        if algorithm_name not in cls._adapters:
            raise ValueError(f"No adapter registered for algorithm: {algorithm_name}")

        adapter_class = cls._adapters[algorithm_name]
        return adapter_class(algorithm_name)

    @classmethod
    def get_available_algorithms(cls) -> List[str]:
        """Get list of available algorithms"""
        return list(cls._adapters.keys())


def register_adapter(algorithm_name: str):
    """Decorator to register algorithm adapters"""
    def decorator(adapter_class):
        AlgorithmRegistry.register(algorithm_name, adapter_class)
        return adapter_class
    return decorator


# Import all adapter modules to register them
try:
    from . import cd_ma
    from . import bnd_ret
    from . import boot_ratio
    from . import bound_mean
    from . import dev_ma
    from . import selbias
    from . import mcpt_trn
    from . import drawdown
    from . import mcpt_bars
except ImportError:
    # Some adapters may not be implemented yet
    pass
