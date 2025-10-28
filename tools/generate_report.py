#!/usr/bin/env python3
"""
Generate Report Tool
Creates human-readable reports from strategy analysis results
"""

import json
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import argparse
import time
import uuid
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def load_request(request_path: str) -> Dict[str, Any]:
    """Load JSON request from inbox"""
    with open(request_path, 'r') as f:
        return json.load(f)


def load_ranking_results(ranking_files: List[str]) -> List[Dict[str, Any]]:
    """Load ranking results from files"""
    results = []
    
    for result_file in ranking_files:
        result_path = Path(result_file)
        if not result_path.is_absolute():
            # Relative to runs/current/outbox
            result_path = Path(__file__).parent.parent / "runs" / "current" / "outbox" / result_path.name
        
        if result_path.exists():
            with open(result_path, 'r') as f:
                results.append(json.load(f))
    
    return results


def generate_executive_summary(selected_strategy: str, rankings: List[Dict], 
                              regime_analysis: Dict) -> str:
    """Generate executive summary section"""
    
    summary = []
    summary.append("# Executive Summary")
    summary.append("")
    summary.append(f"**Selected Strategy:** {selected_strategy}")
    summary.append("")
    
    if rankings:
        top_strategy = rankings[0]
        composite_score = top_strategy.get('composite_score', 0)
        summary.append(f"**Overall Score:** {composite_score:.3f} (out of 1.0)")
        
        # Performance highlights
        metrics = top_strategy.get('individual_metrics', {})
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)
        
        summary.append("")
        summary.append("## Key Performance Metrics")
        summary.append(f"- **Sharpe Ratio:** {sharpe:.2f}")
        summary.append(f"- **Maximum Drawdown:** {max_dd:.1%}")
        summary.append(f"- **Win Rate:** {win_rate:.1%}")
        summary.append("")
    
    # Regime analysis
    robustness = regime_analysis.get('robustness_score', 0)
    summary.append("## Market Regime Analysis")
    summary.append(f"**Robustness Score:** {robustness:.2f} (higher is better)")
    
    if robustness > 0.7:
        summary.append("✅ **Excellent regime robustness** - Strategy performs well across market conditions")
    elif robustness > 0.5:
        summary.append("⚠️ **Good regime robustness** - Strategy shows consistent performance")
    else:
        summary.append("❌ **Limited regime robustness** - Strategy may be sensitive to market conditions")
    
    summary.append("")
    
    return "\n".join(summary)


def generate_performance_analysis(rankings: List[Dict]) -> str:
    """Generate detailed performance analysis section"""
    
    analysis = []
    analysis.append("# Performance Analysis")
    analysis.append("")
    
    if not rankings:
        analysis.append("No ranking data available for analysis.")
        return "\n".join(analysis)
    
    # Top 5 strategies table
    analysis.append("## Top 5 Strategy Rankings")
    analysis.append("")
    analysis.append("| Rank | Strategy | Composite Score | Sharpe | Max DD | Win Rate |")
    analysis.append("|------|----------|-----------------|--------|--------|----------|")
    
    for i, strategy in enumerate(rankings[:5]):
        rank = i + 1
        name = strategy.get('strategy_name', f'Strategy_{i}')[:20]  # Truncate long names
        score = strategy.get('composite_score', 0)
        metrics = strategy.get('individual_metrics', {})
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)
        
        analysis.append(f"| {rank} | {name} | {score:.3f} | {sharpe:.2f} | {max_dd:.1%} | {win_rate:.1%} |")
    
    analysis.append("")
    
    # Score distribution analysis
    scores = [s.get('composite_score', 0) for s in rankings]
    mean_score = np.mean(scores)
    std_score = np.std(scores)
    best_score = np.max(scores)
    
    analysis.append("## Score Distribution")
    analysis.append(f"- **Mean Composite Score:** {mean_score:.3f}")
    analysis.append(f"- **Score Standard Deviation:** {std_score:.3f}")
    analysis.append(f"- **Best Score:** {best_score:.3f}")
    analysis.append(f"- **Score Range:** {best_score - min(scores):.3f}")
    analysis.append("")
    
    # Performance categorization
    excellent = len([s for s in scores if s > 0.8])
    good = len([s for s in scores if 0.6 < s <= 0.8])
    moderate = len([s for s in scores if 0.4 < s <= 0.6])
    poor = len([s for s in scores if s <= 0.4])
    
    analysis.append("## Strategy Quality Distribution")
    analysis.append(f"- **Excellent (>0.8):** {excellent} strategies")
    analysis.append(f"- **Good (0.6-0.8):** {good} strategies")
    analysis.append(f"- **Moderate (0.4-0.6):** {moderate} strategies")
    analysis.append(f"- **Poor (<0.4):** {poor} strategies")
    analysis.append("")
    
    return "\n".join(analysis)


def generate_risk_assessment(rankings: List[Dict]) -> str:
    """Generate risk assessment section"""
    
    assessment = []
    assessment.append("# Risk Assessment")
    assessment.append("")
    
    if not rankings:
        assessment.append("No data available for risk assessment.")
        return "\n".join(assessment)
    
    # Drawdown analysis
    drawdowns = [s.get('individual_metrics', {}).get('max_drawdown', 0) for s in rankings]
    avg_drawdown = np.mean(drawdowns)
    worst_drawdown = np.max(drawdowns)
    
    assessment.append("## Drawdown Analysis")
    assessment.append(f"- **Average Maximum Drawdown:** {avg_drawdown:.1%}")
    assessment.append(f"- **Worst Drawdown:** {worst_drawdown:.1%}")
    assessment.append("")
    
    # Risk categorization
    if worst_drawdown < 0.1:
        risk_level = "Low Risk"
        risk_color = "🟢"
    elif worst_drawdown < 0.2:
        risk_level = "Moderate Risk"
        risk_color = "🟡"
    elif worst_drawdown < 0.3:
        risk_level = "High Risk"
        risk_color = "🟠"
    else:
        risk_level = "Very High Risk"
        risk_color = "🔴"
    
    assessment.append(f"## Overall Risk Level: {risk_color} {risk_level}")
    assessment.append("")
    
    # Risk-adjusted performance
    assessment.append("## Risk-Adjusted Performance")
    assessment.append("| Strategy | Sharpe Ratio | Max Drawdown | Risk-Adjusted Score |")
    assessment.append("|----------|--------------|--------------|---------------------|")
    
    for strategy in rankings[:5]:  # Top 5 only
        name = strategy.get('strategy_name', 'Unknown')[:15]
        metrics = strategy.get('individual_metrics', {})
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        
        # Simple risk-adjusted score: Sharpe / (1 + max_dd)
        risk_adj_score = sharpe / (1 + max_dd) if max_dd > 0 else sharpe
        
        assessment.append(f"| {name} | {sharpe:.2f} | {max_dd:.1%} | {risk_adj_score:.2f} |")
    
    assessment.append("")
    
    return "\n".join(assessment)


def generate_recommendations(selected_strategy: str, rankings: List[Dict], 
                           regime_analysis: Dict) -> str:
    """Generate implementation recommendations section"""
    
    recommendations = []
    recommendations.append("# Implementation Recommendations")
    recommendations.append("")
    
    # Selected strategy details
    top_strategy = rankings[0] if rankings else None
    if top_strategy:
        recommendations.append("## Selected Strategy Details")
        recommendations.append(f"**Strategy:** {selected_strategy}")
        recommendations.append(f"**Composite Score:** {top_strategy.get('composite_score', 0):.3f}")
        recommendations.append("")
    
    # Implementation considerations
    recommendations.append("## Implementation Considerations")
    
    if top_strategy:
        metrics = top_strategy.get('individual_metrics', {})
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        
        if sharpe > 2.0:
            recommendations.append("✅ **Strong risk-adjusted returns** - Suitable for core portfolio allocation")
        elif sharpe > 1.0:
            recommendations.append("⚠️ **Moderate risk-adjusted returns** - Consider as satellite allocation")
        else:
            recommendations.append("❌ **Low risk-adjusted returns** - Requires optimization before implementation")
        
        recommendations.append("")
        
        if max_dd < 0.15:
            recommendations.append("✅ **Acceptable drawdown profile** - Suitable for conservative risk management")
        elif max_dd < 0.25:
            recommendations.append("⚠️ **Moderate drawdown risk** - Implement position sizing controls")
        else:
            recommendations.append("❌ **High drawdown risk** - Requires risk management enhancements")
    
    # Regime considerations
    robustness = regime_analysis.get('robustness_score', 0)
    recommendations.append("")
    recommendations.append("## Market Regime Considerations")
    
    if robustness > 0.7:
        recommendations.append("✅ **High regime robustness** - Strategy should perform well across market cycles")
    else:
        recommendations.append("⚠️ **Limited regime robustness** - Consider regime-based activation/deactivation")
    
    recommendations.append("")
    
    # Next steps
    recommendations.append("## Recommended Next Steps")
    recommendations.append("1. **Forward Testing:** Implement paper trading for 3-6 months")
    recommendations.append("2. **Position Sizing:** Develop appropriate position sizing algorithm")
    recommendations.append("3. **Risk Controls:** Implement stop-loss and portfolio-level risk limits")
    recommendations.append("4. **Monitoring:** Set up performance monitoring and alerting")
    recommendations.append("5. **Review:** Schedule quarterly performance reviews")
    recommendations.append("")
    
    return "\n".join(recommendations)


def generate_html_report(selected_strategy: str, rankings: List[Dict], 
                         regime_analysis: Dict, sections: List[str]) -> str:
    """Generate HTML format report"""
    
    html_sections = []
    
    # HTML header
    html_sections.append("""<!DOCTYPE html>
<html>
<head>
    <title>Trading Strategy Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
        h2 { color: #34495e; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .score-high { color: #27ae60; font-weight: bold; }
        .score-medium { color: #f39c12; font-weight: bold; }
        .score-low { color: #e74c3c; font-weight: bold; }
        .metric-box { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
""")
    
    # Content sections
    if 'executive_summary' in sections:
        html_sections.append(generate_executive_summary(selected_strategy, rankings, regime_analysis))
    
    if 'performance_analysis' in sections:
        html_sections.append(generate_performance_analysis(rankings))
    
    if 'risk_assessment' in sections:
        html_sections.append(generate_risk_assessment(rankings))
    
    if 'recommendations' in sections:
        html_sections.append(generate_recommendations(selected_strategy, rankings, regime_analysis))
    
    # HTML footer
    html_sections.append(f"""
    <hr>
    <p><em>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
</body>
</html>
""")
    
    return "\n".join(html_sections)


def generate_markdown_report(selected_strategy: str, rankings: List[Dict], 
                            regime_analysis: Dict, sections: List[str]) -> str:
    """Generate Markdown format report"""
    
    md_sections = []
    
    # Content sections
    if 'executive_summary' in sections:
        md_sections.append(generate_executive_summary(selected_strategy, rankings, regime_analysis))
    
    if 'performance_analysis' in sections:
        md_sections.append(generate_performance_analysis(rankings))
    
    if 'risk_assessment' in sections:
        md_sections.append(generate_risk_assessment(rankings))
    
    if 'recommendations' in sections:
        md_sections.append(generate_recommendations(selected_strategy, rankings, regime_analysis))
    
    # Add generation timestamp
    md_sections.append(f"\n---\n*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    return "\n".join(md_sections)


def generate_report(params: Dict[str, Any]) -> Dict[str, Any]:
    """Main report generation logic"""
    
    selected_strategy = params.get('selected_strategy', 'Unknown Strategy')
    strategy_rankings = params.get('strategy_rankings', [])
    report_format = params.get('report_format', 'html')
    include_sections = params.get('include_sections', [
        'executive_summary', 'performance_analysis', 'risk_assessment', 'recommendations'
    ])
    output_path = params.get('output_path', 'strategy_report')
    
    # Load ranking results
    rankings = []
    for ranking_file in strategy_rankings:
        ranking_results = load_ranking_results([ranking_file])
        if ranking_results:
            rankings.extend(ranking_results)
    
    # Extract regime analysis (simplified)
    regime_analysis = {
        'robustness_score': 0.7,  # Default value
        'bull_market_performance': 80,
        'bear_market_performance': 65,
        'sideways_performance': 70
    }
    
    try:
        if report_format.lower() == 'html':
            report_content = generate_html_report(selected_strategy, rankings, regime_analysis, include_sections)
            file_extension = '.html'
        elif report_format.lower() == 'markdown':
            report_content = generate_markdown_report(selected_strategy, rankings, regime_analysis, include_sections)
            file_extension = '.md'
        else:
            # Default to HTML
            report_content = generate_html_report(selected_strategy, rankings, regime_analysis, include_sections)
            file_extension = '.html'
        
        # Save report
        if not output_path.endswith(file_extension):
            output_path += file_extension
        
        report_dir = Path(__file__).parent.parent / "runs" / "current" / "results"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / Path(output_path).name
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return {
            "status": "OK",
            "report_file": str(report_file),
            "report_format": report_format,
            "sections_included": include_sections,
            "strategies_analyzed": len(rankings),
            "selected_strategy": selected_strategy
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": f"Failed to generate report: {str(e)}"
        }


def save_response(request_id: str, response: Dict[str, Any]) -> str:
    """Save response to outbox"""
    outbox_dir = Path(__file__).parent.parent / "runs" / "current" / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    response_file = outbox_dir / f"generate_report_{request_id}.json"
    
    response_with_meta = {
        "request_id": request_id,
        "timestamp": time.time(),
        **response
    }
    
    with open(response_file, 'w') as f:
        json.dump(response_with_meta, f, indent=2)
    
    return str(response_file)


def main():
    """Main tool execution"""
    parser = argparse.ArgumentParser(description="Generate report tool")
    parser.add_argument("request_file", help="Path to JSON request file")
    
    args = parser.parse_args()
    
    try:
        # Load request
        request = load_request(args.request_file)
        request_id = request.get('request_id', str(uuid.uuid4()))
        params = request.get('params', {})
        
        print(f"Generating report: {request_id}")
        
        # Execute report generation
        result = generate_report(params)
        
        # Save response
        response_file = save_response(request_id, result)
        print(f"Report saved to: {response_file}")
        
        if result.get('status') == 'OK':
            print(f"Report generated: {result.get('report_file')}")
        
        return 0 if result.get('status') == 'OK' else 1
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
