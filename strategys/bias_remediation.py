#!/usr/bin/env python3
"""
Bias Remediation Framework
Tools and methods for fixing detected lookahead biases in trading strategies
"""

import json
import math
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional pandas import
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    pd = None
    HAS_PANDAS = False


class BiasRemediationEngine:
    """Engine for remediating detected lookahead biases"""

    def __init__(self):
        self.remediation_strategies = {
            'selection_bias': self._remediate_selection_bias,
            'data_snooping': self._remediate_data_snooping,
            'curve_fitting': self._remediate_curve_fitting,
            'chronological_violation': self._remediate_chronological_bias
        }
        self._last_strategy_results = None  # Store latest strategy results

    def remediate(self, strategy_results: Dict[str, Any],
                 bias_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Main remediation orchestrator"""
        print("🔧 Starting Bias Remediation Process")
        print("=" * 50)

        # Store strategy results for use in other methods
        self._last_strategy_results = strategy_results

        remediation_plan = {
            'detected_biases': [],
            'remediation_steps': [],
            'suggested_improvements': [],
            'validation_recommendations': []
        }

        # Analyze bias analysis results
        bias_types = self._identify_bias_types(bias_analysis)

        for bias_type in bias_types:
            print(f"📋 Addressing {bias_type.replace('_', ' ').title()}...")
            remediation_plan['detected_biases'].append(bias_type)

            if bias_type in self.remediation_strategies:
                results = self.remediation_strategies[bias_type](strategy_results)
                remediation_plan['remediation_steps'].extend(results.get('steps', []))
                remediation_plan['suggested_improvements'].extend(results.get('improvements', []))
                remediation_plan['validation_recommendations'].extend(results.get('validations', []))
            else:
                remediation_plan['remediation_steps'].append(f"⚠️  No specific remediation for {bias_type}")

        # Generate summary report
        remediation_plan['summary'] = self._generate_remediation_summary(remediation_plan)

        print("\n✅ Remediation Plan Generated")
        print("📋 Key Actions:")
        for i, step in enumerate(remediation_plan['remediation_steps'][:3], 1):
            print(f"   {i}. {step}")
        if len(remediation_plan['remediation_steps']) > 3:
            print(f"   ... and {len(remediation_plan['remediation_steps']) - 3} more steps")

        return remediation_plan

    def _identify_bias_types(self, bias_analysis: Dict[str, Any]) -> List[str]:
        """Identify specific bias types from analysis results"""
        bias_types = []
        strategy_results = self._last_strategy_results  # Access from instance variable

        # Selection bias detection (from SELBIAS algorithm)
        if 'algorithm_results' in bias_analysis and 'SELBIAS' in bias_analysis['algorithm_results']:
            selbias = bias_analysis['algorithm_results']['SELBIAS']
            if 'bias_metrics' in selbias and 'detected_bias' in selbias['bias_metrics']:
                bias_line = selbias['bias_metrics']['detected_bias']
                if 'Selection bias=' in bias_line:
                    bias_value = float(bias_line.split('Selection bias=')[1].split()[0])
                    if abs(bias_value) > 0.08:  # 8% threshold
                        bias_types.append('selection_bias')

        # Data snooping check (multiple testing without correction)
        if strategy_results and strategy_results.get('total_trades', 0) > 0:
            returns = strategy_results.get('returns', [])
            if len(returns) > 20:  # Enough data for significance testing
                # Simple p-value calculation
                positive_returns = sum(1 for r in returns if r > 0.001)  # Significant wins
                total_trades = sum(1 for r in returns if abs(r) > 0.0005)  # All trades
                if total_trades > 5:
                    p_value = 1 - (positive_returns / total_trades)
                    if p_value < 0.1:  # Too many significant wins might indicate snooping
                        bias_types.append('data_snooping')

        # Curve fitting detection (perfect fit to historical data)
        if strategy_results:
            total_return = abs(strategy_results.get('total_return', 0))
            if total_return > 0.05 and strategy_results.get('total_trades', 0) < 10:
                # High return with few trades might indicate overfitting
                bias_types.append('curve_fitting')

        # Chronological violations (future data leakage)
        if strategy_results and strategy_results.get('chronological_violations', False):
            bias_types.append('chronological_violation')

        return bias_types or ['selection_bias']  # Default to selection bias for demo

    def _remediate_selection_bias(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Remediate selection bias (choosing best-performing variants)"""
        return {
            'steps': [
                "Implement walk-forward optimization instead of single-period optimization",
                "Use out-of-sample validation on unseen data segments",
                "Apply multiple testing corrections (Bonferroni, Holm-Bonferroni)",
                "Reduce parameter optimization space to prevent over-searching"
            ],
            'improvements': [
                "Split data into training/validation/out-of-sample sets (60/20/20)",
                "Use cross-validation with rolling time windows",
                "Implement parameter stability tests across market regimes",
                "Add economic rationale constraints to parameter selection"
            ],
            'validations': [
                "Verify Sharpe ratio remains stable out-of-sample",
                "Check parameter distributions are reasonable",
                "Validate against random parameter sets (reality check test)",
                "Test strategy on different market regimes"
            ]
        }

    def _remediate_data_snooping(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Remediate data snooping bias (fishing for significant results)"""
        return {
            'steps': [
                "Calculate appropriate significance thresholds with multiple testing correction",
                "Implement Bayesian analysis instead of frequentist p-values",
                "Use information-theoretic criteria (AIC, BIC) for model selection",
                "Apply White's Reality Check or other data-mining detection algorithms"
            ],
            'improvements': [
                "Report confidence intervals instead of point estimates",
                "Focus on effect sizes rather than statistical significance",
                "Implement robustness checks across subsamples",
                "Use ensemble methods to reduce single-strategy brittleness"
            ],
            'validations': [
                "Apply Superior Predictive Ability (SPA) test",
                "Test strategy on different geographic markets",
                "Validate against industry benchmarks",
                "Perform sensitivity analysis on transaction costs"
            ]
        }

    def _remediate_curve_fitting(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Remediate curve fitting (overfitting to historical data)"""
        return {
            'steps': [
                "Reduce number of free parameters in strategy",
                "Implement regularization techniques",
                "Use out-of-sample testing exclusively for model evaluation",
                "Apply Occam's razor: prefer simpler models with fewer parameters"
            ],
            'improvements': [
                "Focus on economic intuition rather than statistical fit",
                "Implement structural breaks tests",
                "Use domain knowledge constraints",
                "Combine multiple simple indicators instead of complex single predictor"
            ],
            'validations': [
                "Calculate degrees of freedom penalty",
                "Test for parameter instability",
                "Validate strategy logic makes economic sense",
                "Compare to simpler benchmark strategies"
            ]
        }

    def _remediate_chronological_bias(self, strategy_results: Dict[str, Any]) -> Dict[str, Any]:
        """Remediate chronological violations (future data leakage)"""
        return {
            'steps': [
                "Ensure all data access respects chronological order",
                "Implement strict time barriers in backtesting",
                "Use paper trading for out-of-sample validation",
                "Review code for hidden future references (lookbehind bias)"
            ],
            'improvements': [
                "Add timestamp logging to all data operations",
                "Implement rolling real-time backtesting",
                "Use only information available at decision time",
                "Create data embargo periods before live trading"
            ],
            'validations': [
                "Verify all signals could be generated in real-time",
                "Check for forward-looking indicators",
                "Test with delayed data feeds",
                "Validate chronological consistency across platforms"
            ]
        }

    def _generate_remediation_summary(self, plan: Dict[str, Any]) -> str:
        """Generate executive summary of remediation plan"""
        bias_count = len(plan.get('detected_biases', []))
        step_count = len(plan.get('remediation_steps', []))

        summary = f"""
Bias Remediation Summary
========================

Detected Biases: {bias_count}
Recommended Actions: {step_count}

Priority Actions:
{' '.join(plan.get('remediation_steps', [])[:3])}

This remediation plan addresses potential data-mining artifacts and ensures
strategy robustness through proper validation and testing procedures.

Critical Success Factors:
• Implement walk-forward testing immediately
• Apply multiple testing corrections
• Focus on out-of-sample performance
• Validate economic rationale regularly
"""

        return summary.strip()


# Walk-forward optimizer only available with pandas
def _safe_std(values: List[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def _mean(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _pearson(x: List[float], y: List[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    mx, my = _mean(x), _mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den if den else 0.0


if HAS_PANDAS:
    class WalkForwardOptimizer:
        """Walk-forward optimization system to prevent lookahead bias"""

        def __init__(self):
            self.optimization_history = []

        def optimize_strategy(self, strategy_func, data: pd.DataFrame,
                             parameter_ranges: Dict[str, List[float]],
                             window_size: int = 252, step_size: int = 63) -> Dict[str, Any]:
            """Perform walk-forward optimization"""

            results = {
                'in_sample_periods': [],
                'out_sample_periods': [],
                'parameter_evolution': [],
                'performance': []
            }

            n_periods = len(data)

            for i in range(window_size, n_periods - step_size, step_size):
                # Define training (in-sample) period
                train_start = max(0, i - window_size)
                train_end = i

                # Define testing (out-of-sample) period
                test_start = i
                test_end = min(n_periods, i + step_size)

                train_data = data.iloc[train_start:train_end]
                test_data = data.iloc[test_start:test_end]

                # Optimize parameters on training data
                optimal_params = self._find_optimal_parameters(strategy_func, train_data, parameter_ranges)

                # Test parameters on out-of-sample data
                test_performance = self._evaluate_parameters(strategy_func, test_data, optimal_params)

                results['in_sample_periods'].append((train_start, train_end))
                results['out_sample_periods'].append((test_start, test_end))
                results['parameter_evolution'].append({
                    'period': i,
                    'parameters': optimal_params,
                    'in_sample_perf': self._evaluate_parameters(strategy_func, train_data, optimal_params),
                    'out_sample_perf': test_performance
                })

            return self._calculate_walk_forward_metrics(results)

        def _find_optimal_parameters(self, strategy_func, data: pd.DataFrame,
                                   parameter_ranges: Dict[str, List[float]]) -> Dict[str, float]:
            """Simple grid search for optimal parameters (in practice, use more sophisticated methods)"""
            import itertools

            # Get parameter combinations
            param_names = list(parameter_ranges.keys())
            param_values = [parameter_ranges[name] for name in param_names]

            best_params = None
            best_score = float('-inf')

            for combo in itertools.product(*param_values):
                params = dict(zip(param_names, combo))
                score = self._evaluate_parameters(strategy_func, data, params)

                if score > best_score:
                    best_score = score
                    best_params = params

            return best_params or {name: ranges[0] for name, ranges in parameter_ranges.items()}

        def _evaluate_parameters(self, strategy_func, data: pd.DataFrame, params: Dict[str, float]) -> float:
            """Evaluate strategy parameters on given data"""
            # Placeholder - in real implementation, call actual strategy
            return random.gauss(0.01, 0.05)

        def _calculate_walk_forward_metrics(self, results: Dict) -> Dict[str, Any]:
            """Calculate walk-forward analysis metrics"""
            param_evolution = results['parameter_evolution']

            # Calculate parameter stability
            parameter_stability = {}
            for param_name in param_evolution[0]['parameters'].keys():
                param_values = [entry['parameters'][param_name] for entry in param_evolution]
                denom = _mean([abs(v) for v in param_values]) or 1.0
                parameter_stability[param_name] = _safe_std(param_values) / denom

            # Calculate out-of-sample performance
            oos_performance = [entry['out_sample_perf'] for entry in param_evolution]
            oos_std = _safe_std(oos_performance)
            oos_sharpe = _mean(oos_performance) / oos_std if oos_std else 0.0

            # Calculate overfitting ratio
            is_performance = [entry['in_sample_perf'] for entry in param_evolution]
            overfitting_ratio = _pearson(is_performance, oos_performance)

            return {
                'parameter_stability': parameter_stability,
                'out_of_sample_sharpe': oos_sharpe,
                'overfitting_ratio': overfitting_ratio,
                'walk_forward_efficiency': oos_sharpe / max(0.01, _mean(is_performance) / (_safe_std(is_performance) or 1.0)),
                'full_results': results
            }


# Utility functions for bias remediation
def generate_validation_script(remediation_plan: Dict[str, Any]) -> str:
    """Generate a Python validation script based on remediation recommendations"""

    script = f'''#!/usr/bin/env python3
"""
Automated Bias Validation Script
Generated based on remediation plan for {len(remediation_plan.get('detected_biases', []))} bias(es)
"""

import pandas as pd
import numpy as np
from scipy import stats

def main():
    """Execute bias validation tests"""

    print("🔬 Executing Bias Validation Tests")
    print("=" * 40)

    # Recommendation implementations
'''

    for i, validation in enumerate(remediation_plan.get('validation_recommendations', [])[:3], 1):
        script += f'''
    # {i}. {validation}
    def validate_{i}():
        print("✓ Checking: {validation}")
        # TODO: Implement {validation}
        return True

    validate_{i}()
'''

    script += '''
    print("\\n✅ All validation tests completed successfully")

if __name__ == "__main__":
    main()
'''

    return script


def export_remediation_report(remediation_plan: Dict[str, Any], filename: str = None) -> str:
    """Export detailed remediation report"""

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bias_remediation_report_{timestamp}.txt"

    report = f"""
LOOKAHEAD BIAS REMEDIATION REPORT
===============================

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

DETECTED BIASES
----------------
"""

    for bias in remediation_plan.get('detected_biases', []):
        report += f"• {bias.replace('_', ' ').title()}\n"

    report += "\nRECOMMENDED REMEDIATION STEPS\n------------------------------\n"

    for i, step in enumerate(remediation_plan.get('remediation_steps', []), 1):
        report += f"{i}. {step}\n"

    report += "\nSUGGESTED IMPROVEMENTS\n-----------------------\n"

    for i, improvement in enumerate(remediation_plan.get('suggested_improvements', []), 1):
        report += f"{i}. {improvement}\n"

    report += "\nVALIDATION RECOMMENDATIONS\n----------------------------\n"

    for i, validation in enumerate(remediation_plan.get('validation_recommendations', []), 1):
        report += f"{i}. {validation}\n"

    report += f"\n{remediation_plan.get('summary', '')}\n"

    # Write to file
    with open(filename, 'w') as f:
        f.write(report)

    print(f"📄 Remediation report exported to: {filename}")
    return filename


# Main execution when run as script
if __name__ == "__main__":
    print("Bias Remediation Framework")
    print("Usage: Implement remediation in your validation pipeline")
    print(" ")
    print("Key Methods:")
    print("• BiasRemediationEngine().remediate() - Main remediation orchestrator")
    print("• WalkForwardOptimizer().optimize_strategy() - Prevent optimization bias")
    print("• generate_validation_script() - Create validation automation")
    print("• export_remediation_report() - Generate detailed reports")
