"""
StratVal - Strategy Validator
AI-powered trading strategy creation, validation, and optimization system
"""

__version__ = "1.0.0"
__author__ = "StratVal Team"

from .cli.stratval import StratValCLI
from .generator.strategy_generator import StrategyGenerator
from .pipeline.orchestrator import ValidationOrchestrator
from .scoring.scorer import StrategyScorer

__all__ = [
    'StratValCLI',
    'StrategyGenerator',
    'ValidationOrchestrator',
    'StrategyScorer'
]
