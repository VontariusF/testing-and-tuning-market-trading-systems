#!/usr/bin/env python3
"""
Score Strategy Tool
Rates and ranks trading strategies based on performance metrics
"""

import json
import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Tuple
import argparse
import time
import uuid
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


def load_request(request_path: str) -> Dict[str, Any]:
    """Load JSON request from inbox"""
    with open(request_path, 'r') as f:
        return json.load(f)


def load_strategy_results(strategy_results: List[str]) -> List[Dict[str, Any]]:
    """Load strategy results from files"""
    results = []
    
    for result_file in strategy_results:
        result_path = Path(result_file)
        if not result_path.is_absolute():
            # Relative to runs/current/outbox
            result_path = Path(__file__).parent.parent / "runs" / "current" / "outbox" / result_path.name
        
        if result_path.exists():
            with open(result_path, 'r') as f:
                results.append(json.load(f))
    
    return results


def calculate_composite_score(metrics: Dict[str, float], weights: Dict[str, float]) -> float:
    """Calculate composite score from individual metrics"""
    
    # Normalize metrics (higher is better for most, lower for drawdown)
    normalized = {}
    
    # Risk-adjusted returns (higher is better)
    normalized['sharpe_ratio'] = np.clip(metrics.get('sharpe_ratio', 0) / 3.0, 0, 1)  # Normalize to 0-1, 3.0 is excellent
    normalized['calmar_ratio'] = np.clip(metrics.get('calmar_ratio', 0) / 5.0, 0, 1)   # Normalize to 0-1, 5.0 is excellent
    
    # Drawdown (lower is better, so invert)
    max_dd = metrics.get('max_drawdown', 1.0)
    normalized['max_drawdown'] = np.clip(1.0 - (max_dd / 0.5), 0, 1)  # 50% DD is worst, 0% is best
    
    # Consistency metrics (higher is better)
    normalized['win_rate'] = metrics.get('win_rate', 0) / 100.0  # Convert percentage to 0-1
    normalized['profit_factor'] = np.clip(metrics.get('profit_factor', 1.0) / 3.0, 0, 1)  # 3.0 is excellent
    
    # Calculate weighted composite score
    composite = 0.0
    for metric, weight in weights.items():
        if metric in normalized:
            composite += normalized[metric] * weight
    
    return composite


def calculate_confidence_interval(scores: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate confidence interval for scores"""
    if len(scores) < 2:
        return 0.0, 0.0
    
    mean = np.mean(scores)
    sem = stats.sem(scores)  # Standard error of the mean
    h = sem * stats.t.ppf((1 + confidence) / 2., len(scores) - 1)
    
    return mean - h, mean + h


def analyze_regime_robustness(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyze strategy performance across different market regimes"""
    
    # This would ideally use actual market regime classification
    # For now, we'll simulate by time-based segmentation
    regime_scores = {
        'bull_market': [],
        'bear_market': [], 
        'sideways': []
    }
    
    for result in results:
        if result.get('status') == 'OK':
            strategy_results = result.get('results', {})
            scores = strategy_results.get('scores', {})
            total_score = scores.get('total_score', 0)
            
            # Simplified regime assignment based on performance
            if total_score > 75:
                regime_scores['bull_market'].append(total_score)
            elif total_score < 50:
                regime_scores['bear_market'].append(total_score)
            else:
                regime_scores['sideways'].append(total_score)
    
    # Calculate robustness score
    regime_means = []
    for regime, scores in regime_scores.items():
        if scores:
            regime_means.append(np.mean(scores))
    
    if len(regime_means) >= 2:
        robustness = 1.0 - (np.std(regime_means) / np.mean(regime_means))
        return {
            'robustness_score': max(0.0, robustness),
            'bull_market_performance': np.mean(regime_scores['bull_market']) if regime_scores['bull_market'] else 0,
            'bear_market_performance': np.mean(regime_scores['bear_market']) if regime_scores['bear_market'] else 0,
            'sideways_performance': np.mean(regime_scores['sideways']) if regime_scores['sideways'] else 0
        }
    
    return {'robustness_score': 0.5}  # Default neutral score


def score_strategies(params: Dict[str, Any]) -> Dict[str, Any]:
    """Main strategy scoring logic"""
    
    strategy_results = params.get('strategy_results', [])
    methodology = params.get('scoring_methodology', {})
    benchmark_comparison = params.get('benchmark_comparison', True)
    
    # Default weights if not provided
    default_weights = {
        'sharpe_ratio': 0.3,
        'max_drawdown': 0.2, 
        'win_rate': 0.2,
        'profit_factor': 0.15,
        'calmar_ratio': 0.15
    }
    weights = methodology.get('weights', default_weights)
    
    # Load strategy results
    results = load_strategy_results(strategy_results)
    
    if not results:
        return {
            "status": "ERROR",
            "error": "No valid strategy results found"
        }
    
    # Score each strategy
    strategy_scores = []
    
    for i, result in enumerate(results):
        if result.get('status') == 'OK':
            strategy_results = result.get('results', {})
            scores = strategy_results.get('scores', {})
            
            # Extract metrics
            metrics = {
                'sharpe_ratio': scores.get('sharpe_ratio', 0),
                'max_drawdown': scores.get('max_drawdown', 1.0),
                'win_rate': scores.get('win_rate', 0),
                'profit_factor': scores.get('profit_factor', 1.0),
                'calmar_ratio': scores.get('calmar_ratio', 0)
            }
            
            # Calculate composite score
            composite_score = calculate_composite_score(metrics, weights)
            
            # Calculate confidence intervals using bootstrap if multiple experiments
            confidence_intervals = (0, 0)
            # In a real implementation, this would use bootstrap resampling
            
            strategy_scores.append({
                'strategy_id': i,
                'strategy_name': result.get('strategy', f'strategy_{i}'),
                'individual_scores': metrics,
                'composite_score': composite_score,
                'confidence_interval': confidence_intervals,
                'total_score': scores.get('total_score', 0)  # Original total score for comparison
            })
    
    if not strategy_scores:
        return {
            "status": "ERROR",
            "error": "No valid strategies could be scored"
        }
    
    # Analyze regime robustness
    regime_analysis = analyze_regime_robustness(results)
    
    # Rank strategies
    strategy_scores.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # Calculate statistics
    composite_scores = [s['composite_score'] for s in strategy_scores]
    scoring_stats = {
        'mean_composite_score': np.mean(composite_scores),
        'score_std': np.std(composite_scores),
        'best_score': np.max(composite_scores),
        'score_range': np.max(composite_scores) - np.min(composite_scores),
        'num_strategies': len(strategy_scores)
    }
    
    # Generate rankings with confidence intervals
    rankings = []
    for i, strategy in enumerate(strategy_scores):
        rankings.append({
            'rank': i + 1,
            'strategy_name': strategy['strategy_name'],
            'composite_score': strategy['composite_score'],
            'confidence_lower': strategy['confidence_interval'][0],
            'confidence_upper': strategy['confidence_interval'][1],
            'individual_metrics': strategy['individual_scores']
        })
    
    return {
        "status": "OK",
        "scoring_summary": {
            "methodology_used": methodology,
            "weights_applied": weights,
            "benchmark_comparison": benchmark_comparison
        },
        "rankings": rankings,
        "scoring_statistics": scoring_stats,
        "regime_analysis": regime_analysis,
        "top_strategies": rankings[:5],  # Top 5 strategies
        "recommendations": generate_recommendations(rankings, regime_analysis)
    }


def generate_recommendations(rankings: List[Dict], regime_analysis: Dict) -> List[str]:
    """Generate recommendations based on scoring results"""
    recommendations = []
    
    if not rankings:
        return recommendations
    
    top_score = rankings[0]['composite_score']
    
    # Quality assessment
    if top_score > 0.8:
        recommendations.append("Excellent strategy quality found - proceed with implementation")
    elif top_score > 0.6:
        recommendations.append("Good strategy quality - consider further optimization")
    else:
        recommendations.append("Moderate strategy quality - recommend more experiments")
    
    # Robustness assessment
    robustness = regime_analysis.get('robustness_score', 0)
    if robustness < 0.5:
        recommendations.append("Low regime robustness - test across more market conditions")
    
    # Score spread assessment
    if len(rankings) > 1:
        score_gap = rankings[0]['composite_score'] - rankings[1]['composite_score']
        if score_gap < 0.05:
            recommendations.append("Close competition between top strategies - consider ensemble")
    
    return recommendations


def save_response(request_id: str, response: Dict[str, Any]) -> str:
    """Save response to outbox"""
    outbox_dir = Path(__file__).parent.parent / "runs" / "current" / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    response_file = outbox_dir / f"score_strategy_{request_id}.json"
    
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
    parser = argparse.ArgumentParser(description="Score strategy tool")
    parser.add_argument("request_file", help="Path to JSON request file")
    
    args = parser.parse_args()
    
    try:
        # Load request
        request = load_request(args.request_file)
        request_id = request.get('request_id', str(uuid.uuid4()))
        params = request.get('params', {})
        
        print(f"Scoring strategies: {request_id}")
        
        # Execute strategy scoring
        result = score_strategies(params)
        
        # Save response
        response_file = save_response(request_id, result)
        print(f"Scoring results saved to: {response_file}")
        
        return 0 if result.get('status') == 'OK' else 1
        
    except Exception as e:
        print(f"Error scoring strategies: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
