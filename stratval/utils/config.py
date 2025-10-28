"""
Configuration management for StratVal system
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for StratVal"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration

        Args:
            config_path: Path to config file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config()
        self._config = self._load_config()

    def _find_config(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        search_paths = [
            Path.cwd() / "stratval.json",
            Path.home() / ".stratval" / "config.json",
            Path(__file__).parent.parent / "config.json"
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        return None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")

        # Default configuration with FreqTrade DB integration
        return {
            "database": {
                "connection_string": os.getenv('STRATVAL_DB_URL',
                    'postgresql://freqtrade_user:Vontarius97$@localhost:5432/freqtrade_db'),
                "default_pair": "BTC/USDT",
                "default_timeframe": "1h",
                "max_candles": 1000
            },
            "build": {
                "cmake_path": "cmake",
                "build_dir": "build",
                "algorithm_build_dir": "build"
            },
            "validation": {
                "quick": {
                    "algorithms": ["MCPT_BARS", "DRAWDOWN"],
                    "max_iterations": 100,
                    "timeout": 30
                },
                "standard": {
                    "algorithms": ["MCPT_BARS", "MCPT_TRN", "DRAWDOWN", "CONFTEST", "SELBIAS"],
                    "max_iterations": 1000,
                    "timeout": 480
                },
                "thorough": {
                    "algorithms": ["all"],
                    "max_iterations": 5000,
                    "timeout": 300
                }
            },
            "scoring": {
                "performance_weight": 0.4,
                "statistical_weight": 0.3,
                "risk_weight": 0.3,
                "grade_thresholds": {
                    "A": 85,
                    "B": 70,
                    "C": 55,
                    "D": 40,
                    "F": 0
                }
            },
            "reporting": {
                "default_format": "terminal",
                "output_dir": "./reports",
                "html_template": "default"
            },
            "strategy_generation": {
                "default_template": "ma_crossover",
                "ai_model": "basic",
                "max_tokens": 1000
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None):
        """Save configuration to file"""
        save_path = path or self.config_path or "stratval.json"

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'w') as f:
            json.dump(self._config, f, indent=2)

    def get_validation_config(self, mode: str) -> Dict[str, Any]:
        """Get validation configuration for specified mode"""
        return self.get(f"validation.{mode}", {})

    def get_algorithms_for_mode(self, mode: str) -> list:
        """Get list of algorithms to run for validation mode"""
        config = self.get_validation_config(mode)

        if not config or "algorithms" not in config:
            return []

        algorithms = config["algorithms"]
        return algorithms if algorithms != ["all"] else self._get_all_algorithms()

    def _get_all_algorithms(self) -> list:
        """Get list of all available algorithms"""
        # This would scan the build directory for available executables
        # For now, return a comprehensive list
        return [
            "MCPT_BARS", "MCPT_TRN", "DRAWDOWN", "CD_MA", "CONFTEST",
            "SELBIAS", "TRNBIAS", "STATN", "CSCV_MKT", "DEV_MA",
            "BND_RET", "BOOT_RATIO", "BOUND_MEAN", "CHOOSER",
            "CHOOSER_DD", "ENTROPY", "OVERLAP", "PER_WHAT", "XVW"
        ]

    def get_scoring_weights(self) -> Dict[str, float]:
        """Get scoring weights for different components"""
        return {
            "performance": self.get("scoring.performance_weight", 0.4),
            "statistical": self.get("scoring.statistical_weight", 0.3),
            "risk": self.get("scoring.risk_weight", 0.3)
        }

    def get_grade_thresholds(self) -> Dict[str, int]:
        """Get grade thresholds"""
        return self.get("scoring.grade_thresholds", {})

    def get_build_config(self) -> Dict[str, str]:
        """Get build configuration"""
        return self.get("build", {})

    def get_reporting_config(self) -> Dict[str, Any]:
        """Get reporting configuration"""
        return self.get("reporting", {})

    def get_strategy_generation_config(self) -> Dict[str, Any]:
        """Get strategy generation configuration"""
        return self.get("strategy_generation", {})


# Global configuration instance
_config_instance = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
