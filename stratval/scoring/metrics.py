"""
Performance metrics and scoring calculations
"""

import numpy as np
from typing import Dict, Any, List, Optional


class PerformanceMetrics:
    """Calculate performance metrics from strategy results"""

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio

        Args:
            returns: List of return values
            risk_free_rate: Risk-free rate (annual)

        Returns:
            Sharpe ratio
        """
        if not returns:
            return 0.0

        returns_array = np.array(returns)
        excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate

        if len(returns) < 2:
            return 0.0

        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns, ddof=1)

        if std_excess == 0:
            return 0.0

        # Annualize
        annual_sharpe = mean_excess / std_excess * np.sqrt(252)
        return annual_sharpe

    @staticmethod
    def calculate_calmar_ratio(returns: List[float], max_drawdown: float) -> float:
        """Calculate Calmar ratio

        Args:
            returns: List of return values
            max_drawdown: Maximum drawdown (positive value)

        Returns:
            Calmar ratio
        """
        if not returns or max_drawdown == 0:
            return 0.0

        total_return = np.prod([1 + r for r in returns]) - 1

        if total_return <= 0:
            return 0.0

        # Annualize total return (assuming daily returns)
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1

        if annual_return <= 0:
            return 0.0

        calmar_ratio = annual_return / max_drawdown
        return calmar_ratio

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve

        Args:
            equity_curve: List of portfolio values over time

        Returns:
            Maximum drawdown (positive value)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for value in equity_curve[1:]:
            if value > peak:
                peak = value
            else:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd

        return max_dd

    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
        """Calculate win rate from trade data

        Args:
            trades: List of trade dictionaries with 'return' or 'pnl' keys

        Returns:
            Win rate (0-1)
        """
        if not trades:
            return 0.0

        winning_trades = 0
        total_trades = len(trades)

        for trade in trades:
            pnl = trade.get('return', trade.get('pnl', 0))
            if pnl > 0:
                winning_trades += 1

        return winning_trades / total_trades if total_trades > 0 else 0.0

    @staticmethod
    def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
        """Calculate profit factor

        Args:
            trades: List of trade dictionaries with 'return' or 'pnl' keys

        Returns:
            Profit factor
        """
        if not trades:
            return 0.0

        gross_profit = 0.0
        gross_loss = 0.0

        for trade in trades:
            pnl = trade.get('return', trade.get('pnl', 0))
            if pnl > 0:
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def calculate_total_return(returns: List[float]) -> float:
        """Calculate total return

        Args:
            returns: List of return values

        Returns:
            Total return (not annualized)
        """
        if not returns:
            return 0.0

        total_return = 1.0
        for ret in returns:
            total_return *= (1 + ret)

        return total_return - 1

    @staticmethod
    def calculate_volatility(returns: List[float]) -> float:
        """Calculate return volatility

        Args:
            returns: List of return values

        Returns:
            Volatility (annualized)
        """
        if not returns or len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)
        daily_vol = np.std(returns_array, ddof=1)

        # Annualize
        annual_vol = daily_vol * np.sqrt(252)
        return annual_vol


class StatisticalMetrics:
    """Calculate statistical validation metrics"""

    @staticmethod
    def evaluate_significance(pvalue: float) -> Dict[str, Any]:
        """Evaluate statistical significance

        Args:
            pvalue: p-value from statistical test

        Returns:
            Significance evaluation
        """
        if pvalue is None:
            return {"level": "unknown", "significant": False}

        if pvalue < 0.01:
            level = "highly_significant"
            significant = True
        elif pvalue < 0.05:
            level = "significant"
            significant = True
        elif pvalue < 0.10:
            level = "marginally_significant"
            significant = True
        else:
            level = "not_significant"
            significant = False

        return {
            "level": level,
            "significant": significant,
            "pvalue": pvalue
        }

    @staticmethod
    def evaluate_bias(bias_value: float) -> Dict[str, Any]:
        """Evaluate bias level

        Args:
            bias_value: Bias metric (training bias, selection bias, etc.)

        Returns:
            Bias evaluation
        """
        if bias_value is None:
            return {"level": "unknown", "acceptable": False}

        abs_bias = abs(bias_value)

        if abs_bias < 0.01:
            level = "very_low"
            acceptable = True
        elif abs_bias < 0.05:
            level = "low"
            acceptable = True
        elif abs_bias < 0.10:
            level = "moderate"
            acceptable = True
        elif abs_bias < 0.20:
            level = "high"
            acceptable = False
        else:
            level = "very_high"
            acceptable = False

        return {
            "level": level,
            "acceptable": acceptable,
            "bias": bias_value
        }

    @staticmethod
    def evaluate_skill(skill_value: float) -> Dict[str, Any]:
        """Evaluate skill level

        Args:
            skill_value: Skill estimate from MCPT

        Returns:
            Skill evaluation
        """
        if skill_value is None:
            return {"level": "unknown", "positive": False}

        if skill_value > 0.02:
            level = "excellent"
            positive = True
        elif skill_value > 0.01:
            level = "good"
            positive = True
        elif skill_value > 0.005:
            level = "moderate"
            positive = True
        elif skill_value > 0.0:
            level = "weak"
            positive = True
        else:
            level = "negative"
            positive = False

        return {
            "level": level,
            "positive": positive,
            "skill": skill_value
        }


class RiskMetrics:
    """Calculate risk metrics"""

    @staticmethod
    def evaluate_drawdown_risk(max_drawdown: float, drawdown_95: float = None) -> Dict[str, Any]:
        """Evaluate drawdown risk

        Args:
            max_drawdown: Maximum drawdown observed
            drawdown_95: 95th percentile drawdown estimate

        Returns:
            Risk evaluation
        """
        if max_drawdown is None:
            return {"level": "unknown", "acceptable": False}

        # Evaluate based on maximum drawdown
        if max_drawdown < 0.10:
            level = "very_low"
            acceptable = True
        elif max_drawdown < 0.20:
            level = "low"
            acceptable = True
        elif max_drawdown < 0.30:
            level = "moderate"
            acceptable = True
        elif max_drawdown < 0.50:
            level = "high"
            acceptable = False
        else:
            level = "very_high"
            acceptable = False

        return {
            "level": level,
            "acceptable": acceptable,
            "max_drawdown": max_drawdown,
            "drawdown_95": drawdown_95
        }

    @staticmethod
    def evaluate_volatility(volatility: float) -> Dict[str, Any]:
        """Evaluate volatility level

        Args:
            volatility: Annualized volatility

        Returns:
            Volatility evaluation
        """
        if volatility is None:
            return {"level": "unknown", "acceptable": False}

        if volatility < 0.15:
            level = "very_low"
            acceptable = True
        elif volatility < 0.25:
            level = "low"
            acceptable = True
        elif volatility < 0.40:
            level = "moderate"
            acceptable = True
        elif volatility < 0.60:
            level = "high"
            acceptable = False
        else:
            level = "very_high"
            acceptable = False

        return {
            "level": level,
            "acceptable": acceptable,
            "volatility": volatility
        }
