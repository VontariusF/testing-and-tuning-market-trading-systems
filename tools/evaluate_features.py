#!/usr/bin/env python3
"""
Evaluate Features Tool
Computes feature importances and statistical analysis from experiment results
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
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


def load_request(request_path: str) -> Dict[str, Any]:
    """Load JSON request from inbox"""
    with open(request_path, 'r') as f:
        return json.load(f)


def load_experiment_results(result_files: List[str]) -> List[Dict[str, Any]]:
    """Load experiment results from outbox"""
    results = []
    
    for result_file in result_files:
        result_path = Path(result_file)
        if not result_path.is_absolute():
            # Relative to runs/current/outbox
            result_path = Path(__file__).parent.parent / "runs" / "current" / "outbox" / result_path.name
        
        if result_path.exists():
            with open(result_path, 'r') as f:
                results.append(json.load(f))
    
    return results


def extract_performance_metrics(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Extract performance metrics from experiment results"""
    metrics_data = []
    
    for i, result in enumerate(results):
        if result.get('status') == 'OK':
            strategy_results = result.get('results', {})
            scores = strategy_results.get('scores', {})
            
            # Extract key metrics
            metrics = {
                'experiment_id': i,
                'strategy': result.get('strategy', f'experiment_{i}'),
                'total_score': scores.get('total_score', 0),
                'sharpe_ratio': scores.get('sharpe_ratio', 0),
                'max_drawdown': scores.get('max_drawdown', 0),
                'win_rate': scores.get('win_rate', 0),
                'profit_factor': scores.get('profit_factor', 0),
                'total_return': scores.get('total_return', 0),
                'calmar_ratio': scores.get('calmar_ratio', 0)
            }
            metrics_data.append(metrics)
    
    return pd.DataFrame(metrics_data)


def analyze_feature_importance(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze feature importance across experiments"""
    
    # Correlation analysis
    numeric_cols = ['sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor', 'total_return', 'calmar_ratio']
    correlation_matrix = df[numeric_cols].corr()
    
    # Feature importance based on correlation with total_score
    correlations_with_score = correlation_matrix['total_score'].abs().sort_values(ascending=False)
    
    # Statistical significance testing
    significant_features = {}
    for feature in numeric_cols:
        if feature != 'total_score':
            correlation, p_value = stats.pearsonr(df[feature], df['total_score'])
            significant_features[feature] = {
                'correlation': correlation,
                'p_value': p_value,
                'significant': p_value < 0.05
            }
    
    return {
        'correlation_matrix': correlation_matrix.to_dict(),
        'feature_importance': correlations_with_score.to_dict(),
        'statistical_significance': significant_features
    }


def analyze_strategy_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze patterns across strategy types"""
    
    # Extract strategy types from strategy names
    df['strategy_type'] = df['strategy'].apply(lambda x: 
        'moving_average' if 'moving average' in x.lower() else
        'rsi' if 'rsi' in x.lower() else
        'macd' if 'macd' in x.lower() else
        'bollinger' if 'bollinger' in x.lower() else
        'volume' if 'volume' in x.lower() else
        'other'
    )
    
    # Group by strategy type
    strategy_stats = df.groupby('strategy_type').agg({
        'total_score': ['mean', 'std', 'count'],
        'sharpe_ratio': ['mean', 'std'],
        'max_drawdown': ['mean', 'std'],
        'win_rate': ['mean', 'std']
    }).round(3)
    
    return {
        'strategy_type_performance': strategy_stats.to_dict(),
        'best_strategy_type': df.groupby('strategy_type')['total_score'].mean().idxmax(),
        'most_consistent_type': df.groupby('strategy_type')['total_score'].std().idxmin()
    }


def evaluate_features(params: Dict[str, Any]) -> Dict[str, Any]:
    """Main feature evaluation logic"""
    
    experiment_results = params.get('experiment_results', [])
    analysis_depth = params.get('analysis_depth', 'standard')
    
    # Load experiment results
    results = load_experiment_results(experiment_results)
    
    if not results:
        return {
            "status": "ERROR",
            "error": "No valid experiment results found"
        }
    
    # Extract metrics
    df = extract_performance_metrics(results)
    
    if df.empty:
        return {
            "status": "ERROR", 
            "error": "No performance metrics could be extracted"
        }
    
    # Perform analyses
    feature_importance = analyze_feature_importance(df)
    strategy_patterns = analyze_strategy_patterns(df)
    
    # Generate recommendations
    recommendations = []
    
    # Check for overfitting indicators
    if feature_importance['feature_importance'].get('sharpe_ratio', 0) > 0.9:
        recommendations.append("High correlation with Sharpe ratio - check for overfitting")
    
    # Check for insufficient diversity
    if len(df['strategy_type'].unique()) < 3:
        recommendations.append("Increase strategy type diversity for robust analysis")
    
    # Check statistical significance
    significant_count = sum(1 for feat in feature_importance['statistical_significance'].values() 
                          if feat['significant'])
    if significant_count < 2:
        recommendations.append("Few statistically significant features - consider more experiments")
    
    return {
        "status": "OK",
        "analysis_summary": {
            "total_experiments": len(results),
            "successful_experiments": len(df),
            "strategy_types_analyzed": len(df['strategy_type'].unique()),
            "analysis_depth": analysis_depth
        },
        "feature_importance": feature_importance,
        "strategy_patterns": strategy_patterns,
        "recommendations": recommendations,
        "statistics": {
            "mean_score": df['total_score'].mean(),
            "score_std": df['total_score'].std(),
            "best_score": df['total_score'].max(),
            "score_range": df['total_score'].max() - df['total_score'].min()
        }
    }


def save_response(request_id: str, response: Dict[str, Any]) -> str:
    """Save response to outbox"""
    outbox_dir = Path(__file__).parent.parent / "runs" / "current" / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    
    response_file = outbox_dir / f"evaluate_features_{request_id}.json"
    
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
    parser = argparse.ArgumentParser(description="Evaluate features tool")
    parser.add_argument("request_file", help="Path to JSON request file")
    
    args = parser.parse_args()
    
    try:
        # Load request
        request = load_request(args.request_file)
        request_id = request.get('request_id', str(uuid.uuid4()))
        params = request.get('params', {})
        
        print(f"Evaluating features: {request_id}")
        
        # Execute feature evaluation
        result = evaluate_features(params)
        
        # Save response
        response_file = save_response(request_id, result)
        print(f"Analysis saved to: {response_file}")
        
        return 0 if result.get('status') == 'OK' else 1
        
    except Exception as e:
        print(f"Error evaluating features: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
