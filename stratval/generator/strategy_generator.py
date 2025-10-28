"""
AI-powered strategy generator from natural language descriptions
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

try:
    from stratval.utils.config import get_config
except ImportError:  # Allow direct execution without package context
    from utils.config import get_config


class StrategyTemplate(ABC):
    """Base class for strategy templates"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def generate_code(self, params: Dict[str, Any]) -> str:
        """Generate C++ strategy code

        Args:
            params: Strategy parameters

        Returns:
            Complete C++ strategy implementation
        """
        pass

    @abstractmethod
    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for this template"""
        pass

    @abstractmethod
    def parse_description(self, description: str) -> Dict[str, Any]:
        """Parse natural language description into parameters"""
        pass


class MACrossoverTemplate(StrategyTemplate):
    """Moving Average Crossover strategy template"""

    def __init__(self):
        super().__init__(
            "ma_crossover",
            "Moving Average Crossover strategy with fast and slow periods"
        )

    def generate_code(self, params: Dict[str, Any]) -> str:
        """Generate MA crossover strategy code"""
        fast_period = params.get('fast_period', 10)
        slow_period = params.get('slow_period', 50)
        symbol = params.get('symbol', 'STRATEGY')

        code = f'''#include "strategy.h"
#include <vector>
#include <string>

class MACrossoverStrategy : public Strategy {{
public:
    MACrossoverStrategy(int fast_period, int slow_period)
        : fast_period_(fast_period), slow_period_(slow_period) {{
        if (fast_period_ >= slow_period_) {{
            fast_period_ = 10;
            slow_period_ = 50;
        }}
    }}

    void on_start() override {{
        closes_.clear();
        position_ = 0;
        trades_ = 0;
    }}

    void on_bar(const Bar& b) override {{
        double price = b.close;
        closes_.push_back(price);

        if (closes_.size() < (size_t)slow_period_) {{
            return;
        }}

        // Calculate moving averages
        double fast_sum = 0.0, slow_sum = 0.0;
        for (int i = 0; i < fast_period_; ++i) {{
            fast_sum += closes_[closes_.size() - 1 - i];
        }}
        for (int i = 0; i < slow_period_; ++i) {{
            slow_sum += closes_[closes_.size() - 1 - i];
        }}

        double fast_ma = fast_sum / fast_period_;
        double slow_ma = slow_sum / slow_period_;

        // Generate signals
        int desired_position = 0;
        if (fast_ma > slow_ma) {{
            desired_position = 1;  // Long
        }} else if (fast_ma < slow_ma) {{
            desired_position = -1; // Short
        }}

        // Execute trades
        if (desired_position != position_) {{
            position_ = desired_position;
            ++trades_;
        }}
    }}

    void on_finish() override {{
        printf("MA Crossover Strategy: Fast=%d, Slow=%d, Trades=%d\\n",
               fast_period_, slow_period_, trades_);
    }}

private:
    int fast_period_;
    int slow_period_;
    std::vector<double> closes_;
    int position_ = 0;
    int trades_ = 0;
}};

// Factory function
Strategy* make_{symbol.lower()}_strategy() {{
    return new MACrossoverStrategy({fast_period}, {slow_period});
}}
'''
        return code

    def get_default_params(self) -> Dict[str, Any]:
        return {
            'fast_period': 10,
            'slow_period': 50,
            'symbol': 'MA_CROSSOVER'
        }

    def parse_description(self, description: str) -> Dict[str, Any]:
        """Parse description like 'MA crossover with 10 and 50 periods'"""
        params = self.get_default_params()

        # Look for period numbers
        numbers = re.findall(r'\\b\\d+\\b', description)

        if len(numbers) >= 2:
            params['fast_period'] = int(numbers[0])
            params['slow_period'] = int(numbers[1])
        elif len(numbers) == 1:
            params['fast_period'] = int(numbers[0])
            params['slow_period'] = int(numbers[0]) * 5  # Default ratio

        return params


class RSIStrategyTemplate(StrategyTemplate):
    """RSI strategy template"""

    def __init__(self):
        super().__init__(
            "rsi_strategy",
            "RSI overbought/oversold strategy"
        )

    def generate_code(self, params: Dict[str, Any]) -> str:
        """Generate RSI strategy code"""
        period = params.get('period', 14)
        overbought = params.get('overbought', 70)
        oversold = params.get('oversold', 30)
        symbol = params.get('symbol', 'RSI')

        code = f'''#include "strategy.h"
#include <vector>
#include <string>

class RSIStrategy : public Strategy {{
public:
    RSIStrategy(int period, double overbought, double oversold)
        : period_(period), overbought_(overbought), oversold_(oversold) {{
    }}

    void on_start() override {{
        closes_.clear();
        gains_.clear();
        losses_.clear();
        position_ = 0;
        trades_ = 0;
    }}

    void on_bar(const Bar& b) override {{
        double price = b.close;
        closes_.push_back(price);

        if (closes_.size() < 2) return;

        // Calculate gains and losses
        double change = price - closes_[closes_.size() - 2];
        gains_.push_back(change > 0 ? change : 0);
        losses_.push_back(change < 0 ? -change : 0);

        if (gains_.size() < (size_t)period_) return;

        // Calculate RSI
        double avg_gain = 0.0, avg_loss = 0.0;
        for (int i = gains_.size() - period_; i < gains_.size(); ++i) {{
            avg_gain += gains_[i];
            avg_loss += losses_[i];
        }}
        avg_gain /= period_;
        avg_loss /= period_;

        double rs = avg_loss != 0 ? avg_gain / avg_loss : 0;
        double rsi = 100.0 - (100.0 / (1.0 + rs));

        // Generate signals
        int desired_position = 0;
        if (rsi < oversold_) {{
            desired_position = 1;  // Long
        }} else if (rsi > overbought_) {{
            desired_position = -1; // Short
        }}

        // Execute trades
        if (desired_position != position_) {{
            position_ = desired_position;
            ++trades_;
        }}
    }}

    void on_finish() override {{
        printf("RSI Strategy: Period=%d, OB=%g, OS=%g, Trades=%d\\n",
               period_, overbought_, oversold_, trades_);
    }}

private:
    int period_;
    double overbought_;
    double oversold_;
    std::vector<double> closes_;
    std::vector<double> gains_;
    std::vector<double> losses_;
    int position_ = 0;
    int trades_ = 0;
}};

// Factory function
Strategy* make_{symbol.lower()}_strategy() {{
    return new RSIStrategy({period}, {overbought}, {oversold});
}}
'''
        return code

    def get_default_params(self) -> Dict[str, Any]:
        return {
            'period': 14,
            'overbought': 70,
            'oversold': 30,
            'symbol': 'RSI'
        }

    def parse_description(self, description: str) -> Dict[str, Any]:
        """Parse description like 'RSI with period 14 and 30/70 levels'"""
        params = self.get_default_params()

        # Look for period
        period_match = re.search(r'period\\s*(\\d+)', description, re.IGNORECASE)
        if period_match:
            params['period'] = int(period_match.group(1))

        # Look for overbought/oversold levels
        levels = re.findall(r'\\b\\d+\\b', description)
        if len(levels) >= 2:
            params['oversold'] = int(levels[0])
            params['overbought'] = int(levels[1])

        return params


class StrategyGenerator:
    """Main strategy generator"""

    def __init__(self):
        self.config = get_config()
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, StrategyTemplate]:
        """Load available strategy templates"""
        templates = {
            'ma_crossover': MACrossoverTemplate(),
            'rsi_strategy': RSIStrategyTemplate(),
        }

        # Add more templates here as they are implemented
        # 'bollinger': BollingerTemplate(),
        # 'macd': MACDTemplate(),
        # etc.

        return templates

    def from_natural_language(self, description: str) -> str:
        """Generate strategy from natural language description

        Args:
            description: Natural language strategy description

        Returns:
            Complete C++ strategy code
        """
        # Determine which template to use
        template = self._select_template(description)

        # Parse parameters from description
        params = template.parse_description(description)

        # Generate code
        code = template.generate_code(params)

        return code

    def from_template(self, template_name: str, params: Dict[str, Any]) -> str:
        """Generate strategy from template with parameters

        Args:
            template_name: Name of template to use
            params: Strategy parameters

        Returns:
            Complete C++ strategy code
        """
        if template_name not in self.templates:
            available = ', '.join(self.templates.keys())
            raise ValueError(f"Unknown template: {template_name}. Available: {available}")

        template = self.templates[template_name]

        # Merge with defaults
        default_params = template.get_default_params()
        merged_params = {**default_params, **params}

        return template.generate_code(merged_params)

    def _select_template(self, description: str) -> StrategyTemplate:
        """Select appropriate template based on description"""
        desc_lower = description.lower()

        if 'ma' in desc_lower or 'moving average' in desc_lower or 'crossover' in desc_lower:
            return self.templates['ma_crossover']
        elif 'rsi' in desc_lower:
            return self.templates['rsi_strategy']
        else:
            # Default to MA crossover for now
            return self.templates['ma_crossover']

    def get_available_templates(self) -> List[str]:
        """Get list of available template names"""
        return list(self.templates.keys())

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a template"""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")

        template = self.templates[template_name]
        return {
            'name': template.name,
            'description': template.description,
            'default_params': template.get_default_params()
        }
