"""
Main scoring system that combines all metrics into overall grade
"""

from typing import Dict, Any, List
import numpy as np

from .metrics import PerformanceMetrics, StatisticalMetrics, RiskMetrics

try:
    from stratval.utils.config import get_config
except ImportError:
    from utils.config import get_config


class StrategyScorer:
    """Main scoring system for strategies"""

    def __init__(self):
        """Initialize scorer with configuration"""
        self.config = get_config()
        self.weights = self.config.get_scoring_weights()
        self.grade_thresholds = self.config.get_grade_thresholds()

    def calculate_score(self, strategy_results: Dict[str, Any],
                       algorithm_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive strategy score

        Args:
            strategy_results: Results from strategy backtest
            algorithm_results: Results from validation algorithms

        Returns:
            Comprehensive scoring results
        """
        # Extract data from strategy results
        returns = self._extract_returns(strategy_results)
        equity_curve = self._extract_equity_curve(strategy_results)
        trades = self._extract_trades(strategy_results)

        # Calculate performance metrics
        performance_score = self._calculate_performance_score(returns, equity_curve, trades)

        # Calculate statistical validation score
        statistical_score = self._calculate_statistical_score(algorithm_results)

        # Calculate risk score
        risk_score = self._calculate_risk_score(returns, equity_curve, algorithm_results)

        # Combine scores
        total_score = (
            performance_score * self.weights["performance"] +
            statistical_score * self.weights["statistical"] +
            risk_score * self.weights["risk"]
        )

        # Determine grade
        grade = self._calculate_grade(total_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            performance_score, statistical_score, risk_score, algorithm_results
        )

        return {
            "total_score": round(total_score, 1),
            "grade": grade,
            "performance_score": round(performance_score, 1),
            "statistical_score": round(statistical_score, 1),
            "risk_score": round(risk_score, 1),
            "weights_used": self.weights,
            "recommendations": recommendations,
            "details": {
                "performance": self._get_performance_details(returns, equity_curve, trades),
                "statistical": self._get_statistical_details(algorithm_results),
                "risk": self._get_risk_details(returns, equity_curve, algorithm_results)
            }
        }

    def _extract_returns(self, strategy_results: Dict[str, Any]) -> List[float]:
        """Extract returns from strategy results"""
        # Try multiple possible locations
        if 'returns' in strategy_results:
            return strategy_results['returns']
        elif 'trade_returns' in strategy_results:
            return strategy_results['trade_returns']
        elif 'trades' in strategy_results:
            # Extract from trades
            trades = strategy_results['trades']
            returns = []
            for trade in trades:
                pnl = trade.get('return', trade.get('pnl', 0))
                returns.append(pnl)
            return returns
        return []

    def _extract_equity_curve(self, strategy_results: Dict[str, Any]) -> List[float]:
        """Extract equity curve from strategy results"""
        if 'equity_curve' in strategy_results:
            return strategy_results['equity_curve']
        elif 'equity' in strategy_results:
            return strategy_results['equity']
        elif 'portfolio_value' in strategy_results:
            return strategy_results['portfolio_value']
        return []

    def _extract_trades(self, strategy_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trades from strategy results"""
        if 'trades' in strategy_results:
            return strategy_results['trades']
        elif 'trade_log' in strategy_results:
            return strategy_results['trade_log']
        return []

    def _calculate_performance_score(self, returns: List[float],
                                   equity_curve: List[float],
                                   trades: List[Dict[str, Any]]) -> float:
        """Calculate performance score (0-100)"""
        if not returns:
            return 0.0

        score_components = []

        # Sharpe ratio (40% of performance score)
        sharpe = PerformanceMetrics.calculate_sharpe_ratio(returns)
        sharpe_score = self._normalize_metric(sharpe, target=2.0, max_score=40)
        score_components.append(("sharpe", sharpe_score))

        # Total return (30% of performance score)
        total_return = PerformanceMetrics.calculate_total_return(returns)
        return_score = self._normalize_metric(total_return, target=0.5, max_score=30)
        score_components.append(("return", return_score))

        # Win rate (15% of performance score)
        win_rate = PerformanceMetrics.calculate_win_rate(trades)
        win_rate_score = win_rate * 15
        score_components.append(("win_rate", win_rate_score))

        # Profit factor (15% of performance score)
        profit_factor = PerformanceMetrics.calculate_profit_factor(trades)
        if profit_factor == float('inf'):
            pf_score = 15
        elif profit_factor >= 2.0:
            pf_score = 15
        elif profit_factor >= 1.5:
            pf_score = 10
        elif profit_factor >= 1.0:
            pf_score = 5
        else:
            pf_score = 0
        score_components.append(("profit_factor", pf_score))

        total_performance_score = sum(score for _, score in score_components)

        # Cap at 100
        return min(total_performance_score, 100.0)

    def _calculate_statistical_score(self, algorithm_results: Dict[str, Any]) -> float:
        """Calculate statistical validation score (0-100)"""
        score = 0.0

        # MCPT_BARS results (up to 40 points)
        if 'MCPT_BARS' in algorithm_results:
            mcpt_results = algorithm_results['MCPT_BARS']

            # P-value significance (30%)
            pvalue = mcpt_results.get('pvalue')
            if pvalue is not None:
                if pvalue < 0.01:
                    pvalue_score = 20
                elif pvalue < 0.05:
                    pvalue_score = 15
                elif pvalue < 0.10:
                    pvalue_score = 10
                else:
                    pvalue_score = 0
                score += pvalue_score

            # Skill evaluation (30%)
            skill = mcpt_results.get('skill')
            if skill is not None:
                if skill > 0.02:
                    skill_score = 20
                elif skill > 0.01:
                    skill_score = 15
                elif skill > 0.005:
                    skill_score = 10
                elif skill > 0.0:
                    skill_score = 5
                else:
                    skill_score = 0
                score += skill_score

        # MCPT_TRN results (up to 20 points)
        if 'MCPT_TRN' in algorithm_results:
            trn_results = algorithm_results['MCPT_TRN']
            trn_score = 0

            trn_pvalue = trn_results.get('p_value')
            if trn_pvalue is not None:
                if trn_pvalue < 0.01:
                    trn_score += 12
                elif trn_pvalue < 0.05:
                    trn_score += 9
                elif trn_pvalue < 0.10:
                    trn_score += 6

            rejection = trn_results.get('null_hypothesis_rejected')
            if rejection is True:
                trn_score += 8
            elif rejection is None:
                test_stat = trn_results.get('test_statistic')
                if test_stat is not None and abs(test_stat) >= 1.96:
                    trn_score += 5

            score += min(trn_score, 20)

        # Bias evaluation (40% of statistical score)
        total_bias_score = 0

        # Training bias
        training_bias = None
        for results in algorithm_results.values():
            if 'training_bias' in results:
                training_bias = results['training_bias']
                break

        if training_bias is not None:
            abs_bias = abs(training_bias)
            if abs_bias < 0.01:
                total_bias_score += 20
            elif abs_bias < 0.05:
                total_bias_score += 15
            elif abs_bias < 0.10:
                total_bias_score += 10
            else:
                total_bias_score += 0

        # Selection bias (if available)
        selection_bias = None
        for results in algorithm_results.values():
            if 'selection_bias' in results:
                selection_bias = results['selection_bias']
                break

        if selection_bias is not None:
            abs_bias = abs(selection_bias)
            if abs_bias < 0.01:
                total_bias_score += 20
            elif abs_bias < 0.05:
                total_bias_score += 15
            elif abs_bias < 0.10:
                total_bias_score += 10
            else:
                total_bias_score += 0

        score += total_bias_score

        return min(score, 100.0)

    def _calculate_risk_score(self, returns: List[float],
                            equity_curve: List[float],
                            algorithm_results: Dict[str, Any]) -> float:
        """Calculate risk score (0-100)"""
        score = 0.0

        # Maximum drawdown (50% of risk score)
        max_dd = PerformanceMetrics.calculate_max_drawdown(equity_curve)
        if max_dd < 0.10:
            dd_score = 50
        elif max_dd < 0.20:
            dd_score = 40
        elif max_dd < 0.30:
            dd_score = 30
        elif max_dd < 0.50:
            dd_score = 20
        else:
            dd_score = 0
        score += dd_score

        # Volatility (30% of risk score)
        volatility = PerformanceMetrics.calculate_volatility(returns)
        if volatility < 0.15:
            vol_score = 30
        elif volatility < 0.25:
            vol_score = 25
        elif volatility < 0.40:
            vol_score = 20
        elif volatility < 0.60:
            vol_score = 10
        else:
            vol_score = 0
        score += vol_score

        # Calmar ratio (20% of risk score)
        if returns and max_dd > 0:
            calmar = PerformanceMetrics.calculate_calmar_ratio(returns, max_dd)
            if calmar > 2.0:
                calmar_score = 20
            elif calmar > 1.0:
                calmar_score = 15
            elif calmar > 0.5:
                calmar_score = 10
            else:
                calmar_score = 0
            score += calmar_score

        return min(score, 100.0)

    def _normalize_metric(self, value: float, target: float, max_score: float) -> float:
        """Normalize a metric to a score"""
        if value >= target:
            return max_score

        # Linear interpolation from 0 to target
        return (value / target) * max_score

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from numeric score"""
        for grade, threshold in sorted(self.grade_thresholds.items(), reverse=True):
            if score >= threshold:
                return grade

        return 'F'

    def _generate_recommendations(self, performance_score: float,
                                statistical_score: float,
                                risk_score: float,
                                algorithm_results: Dict[str, Any]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        if performance_score < 60:
            recommendations.append("Performance needs improvement - consider parameter optimization")

        if statistical_score < 60:
            recommendations.append("Statistical significance is weak - strategy may be overfit")

        if risk_score < 60:
            recommendations.append("Risk management needs attention - consider reducing position sizes")

        # Check for specific algorithm warnings
        for algo_name, results in algorithm_results.items():
            if 'error' in results:
                recommendations.append(f"Algorithm {algo_name} failed - check configuration")

        # Check for high bias
        for results in algorithm_results.values():
            if 'training_bias' in results and abs(results['training_bias']) > 0.10:
                recommendations.append("High training bias detected - use longer out-of-sample period")

        return recommendations

    def _get_performance_details(self, returns: List[float],
                               equity_curve: List[float],
                               trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed performance metrics"""
        return {
            "sharpe_ratio": PerformanceMetrics.calculate_sharpe_ratio(returns),
            "total_return": PerformanceMetrics.calculate_total_return(returns),
            "volatility": PerformanceMetrics.calculate_volatility(returns),
            "max_drawdown": PerformanceMetrics.calculate_max_drawdown(equity_curve),
            "win_rate": PerformanceMetrics.calculate_win_rate(trades),
            "profit_factor": PerformanceMetrics.calculate_profit_factor(trades),
            "num_trades": len(trades),
            "num_returns": len(returns)
        }

    def _get_statistical_details(self, algorithm_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed statistical validation metrics"""
        details = {}

        for algo_name, results in algorithm_results.items():
            if algo_name == 'MCPT_BARS':
                details['mcpt_pvalue'] = results.get('pvalue')
                details['mcpt_skill'] = results.get('skill')
                details['mcpt_training_bias'] = results.get('training_bias')
            elif algo_name == 'MCPT_TRN':
                details['mcpt_trn_pvalue'] = results.get('p_value')
                details['mcpt_trn_test_statistic'] = results.get('test_statistic')
                details['mcpt_trn_significance'] = results.get('significance_level')
                details['mcpt_trn_rejected'] = results.get('null_hypothesis_rejected')
            elif algo_name == 'DRAWDOWN':
                details['drawdown_95'] = results.get('drawdown_05')  # Approximate
                details['drawdown_99'] = results.get('drawdown_01')  # Approximate

        return details

    def _get_risk_details(self, returns: List[float],
                         equity_curve: List[float],
                         algorithm_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed risk metrics"""
        max_dd = PerformanceMetrics.calculate_max_drawdown(equity_curve)
        volatility = PerformanceMetrics.calculate_volatility(returns)

        # Get drawdown bounds from algorithms
        drawdown_95 = None
        drawdown_99 = None

        for results in algorithm_results.values():
            if 'drawdown_05' in results:
                drawdown_95 = results['drawdown_05']
            if 'drawdown_01' in results:
                drawdown_99 = results['drawdown_01']

        return {
            "max_drawdown": max_dd,
            "volatility": volatility,
            "drawdown_95": drawdown_95,
            "drawdown_99": drawdown_99,
            "calmar_ratio": PerformanceMetrics.calculate_calmar_ratio(returns, max_dd) if max_dd > 0 else 0
        }
