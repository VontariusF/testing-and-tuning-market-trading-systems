"""
Terminal report generator for validation results
"""

from typing import Dict, Any
import time


class TerminalReporter:
    """Generate formatted terminal reports"""

    def __init__(self):
        self.colors = {
            'green': '\033[92m',
            'red': '\033[91m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'bold': '\033[1m',
            'reset': '\033[0m'
        }

    def generate(self, results: Dict[str, Any]) -> None:
        """Generate and print terminal report

        Args:
            results: Complete validation results
        """
        self._print_header(results)
        self._print_performance_section(results)
        self._print_statistical_section(results)
        self._print_risk_section(results)
        self._print_recommendations(results)
        self._print_footer(results)

    def _print_header(self, results: Dict[str, Any]) -> None:
        """Print report header"""
        print()
        print("=" * 70)
        print(f"{self.colors['bold']}STRATEGY VALIDATION REPORT{self.colors['reset']}")
        print("=" * 70)

        mode = results.get('validation_mode', 'unknown').upper()
        print(f"Validation Mode: {self.colors['cyan']}{mode}{self.colors['reset']}")

        # Show overall score and grade
        scores = results.get('scores', {})
        total_score = scores.get('total_score', 0)
        grade = scores.get('grade', 'F')

        grade_color = self._get_grade_color(grade)
        print(f"Overall Score: {self.colors['bold']}{total_score}/100{self.colors['reset']}")
        print(f"Grade: {grade_color}{grade}{self.colors['reset']}")

        print("-" * 70)
        print()

    def _print_performance_section(self, results: Dict[str, Any]) -> None:
        """Print performance metrics section"""
        print(f"{self.colors['bold']}{self.colors['green']}📈 PERFORMANCE METRICS{self.colors['reset']}")
        print()

        scores = results.get('scores', {})
        details = scores.get('details', {}).get('performance', {})

        if details:
            metrics = [
                ("Sharpe Ratio", details.get('sharpe_ratio', 0), "Higher is better"),
                ("Total Return", f"{details.get('total_return', 0):.2%}", "Overall return"),
                ("Win Rate", f"{details.get('win_rate', 0):.1%}", "Percentage of winning trades"),
                ("Profit Factor", f"{details.get('profit_factor', 0):.2f}", "Gross profit / gross loss"),
                ("Max Drawdown", f"{details.get('max_drawdown', 0):.1%}", "Largest peak-to-trough decline"),
                ("Volatility", f"{details.get('volatility', 0):.1%}", "Return volatility")
            ]

            for name, value, description in metrics:
                color = self._get_metric_color(name, value)
                print(f"  {name:15} {color}{value:8}{self.colors['reset']} ({description})")

        print()

    def _print_statistical_section(self, results: Dict[str, Any]) -> None:
        """Print statistical validation section"""
        print(f"{self.colors['bold']}{self.colors['blue']}🔬 STATISTICAL VALIDATION{self.colors['reset']}")
        print()

        algorithm_results = results.get('algorithm_results', {})

        # MCPT_BARS results
        if 'MCPT_BARS' in algorithm_results:
            mcpt = algorithm_results['MCPT_BARS']

            print("  Monte Carlo Permutation Test:")
            pvalue = mcpt.get('pvalue')
            if pvalue is not None:
                color = self.colors['green'] if pvalue < 0.05 else self.colors['red']
                print(f"    p-value      {color}{pvalue:.4f}{self.colors['reset']}")

            skill = mcpt.get('skill')
            if skill is not None:
                color = self._get_skill_color(skill)
                print(f"    True Skill   {color}{skill:.4f}{self.colors['reset']}")

            bias = mcpt.get('training_bias')
            if bias is not None:
                color = self._get_bias_color(bias)
                print(f"    Training Bias {color}{bias:.4f}{self.colors['reset']}")

        print()

    def _print_risk_section(self, results: Dict[str, Any]) -> None:
        """Print risk analysis section"""
        print(f"{self.colors['bold']}{self.colors['yellow']}⚠️  RISK ANALYSIS{self.colors['reset']}")
        print()

        scores = results.get('scores', {})
        details = scores.get('details', {}).get('risk', {})

        if details:
            print("  Risk Metrics:")
            max_dd = details.get('max_drawdown', 0)
            color = self.colors['green'] if max_dd < 0.20 else self.colors['yellow'] if max_dd < 0.50 else self.colors['red']
            print(f"    Max DD       {color}{max_dd:.1%}{self.colors['reset']}")

            vol = details.get('volatility', 0)
            color = self.colors['green'] if vol < 0.25 else self.colors['yellow'] if vol < 0.50 else self.colors['red']
            print(f"    Volatility   {color}{vol:.1%}{self.colors['reset']}")

            calmar = details.get('calmar_ratio', 0)
            color = self.colors['green'] if calmar > 1.0 else self.colors['yellow'] if calmar > 0.5 else self.colors['red']
            print(f"    Calmar Ratio {color}{calmar:.2f}{self.colors['reset']}")

        print()

    def _print_recommendations(self, results: Dict[str, Any]) -> None:
        """Print recommendations section"""
        scores = results.get('scores', {})

        if 'recommendations' in scores and scores['recommendations']:
            print(f"{self.colors['bold']}{self.colors['magenta']}💡 RECOMMENDATIONS{self.colors['reset']}")
            print()

            for rec in scores['recommendations']:
                print(f"  • {rec}")

            print()

    def _print_footer(self, results: Dict[str, Any]) -> None:
        """Print report footer"""
        print("-" * 70)

        # Show algorithms that were run
        algorithms = results.get('algorithms_run', [])
        if algorithms:
            print(f"Algorithms run: {', '.join(algorithms)}")

        # Show timestamp
        timestamp = results.get('timestamp')
        if timestamp:
            date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            print(f"Report generated: {date_str}")

        print("=" * 70)
        print()

    def _get_grade_color(self, grade: str) -> str:
        """Get color for grade"""
        grade_colors = {
            'A': self.colors['green'],
            'B': self.colors['blue'],
            'C': self.colors['yellow'],
            'D': self.colors['magenta'],
            'F': self.colors['red']
        }
        return grade_colors.get(grade, self.colors['reset'])

    def _get_metric_color(self, name: str, value) -> str:
        """Get color for metric value"""
        try:
            # Convert to float if it's a string
            if isinstance(value, str):
                value = float(value.replace('%', '')) if '%' in value else float(value)
        except (ValueError, AttributeError):
            return self.colors['reset']

        if name == "Sharpe Ratio":
            return self.colors['green'] if value > 1.0 else self.colors['yellow'] if value > 0.5 else self.colors['red']
        elif name == "Total Return":
            return self.colors['green'] if value > 0.10 else self.colors['yellow'] if value > 0.0 else self.colors['red']
        elif name == "Win Rate":
            return self.colors['green'] if value > 0.55 else self.colors['yellow'] if value > 0.45 else self.colors['red']
        elif name == "Profit Factor":
            return self.colors['green'] if value > 1.5 else self.colors['yellow'] if value > 1.0 else self.colors['red']
        elif name == "Max Drawdown":
            return self.colors['green'] if value < 0.20 else self.colors['yellow'] if value < 0.40 else self.colors['red']
        elif name == "Volatility":
            return self.colors['green'] if value < 0.25 else self.colors['yellow'] if value < 0.40 else self.colors['red']
        else:
            return self.colors['reset']

    def _get_skill_color(self, skill: float) -> str:
        """Get color for skill value"""
        if skill > 0.02:
            return self.colors['green']
        elif skill > 0.01:
            return self.colors['blue']
        elif skill > 0.005:
            return self.colors['yellow']
        elif skill > 0.0:
            return self.colors['magenta']
        else:
            return self.colors['red']

    def _get_bias_color(self, bias: float) -> str:
        """Get color for bias value"""
        abs_bias = abs(bias)
        if abs_bias < 0.01:
            return self.colors['green']
        elif abs_bias < 0.05:
            return self.colors['blue']
        elif abs_bias < 0.10:
            return self.colors['yellow']
        else:
            return self.colors['red']
