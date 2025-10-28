# Claude Code Trading System Tools

This document describes the core Python tools that implement deterministic, side-effect-free operations for the Claude Code trading system.

## Overview

All tools follow a consistent interface:
- Accept JSON input from `inbox/` directory
- Write JSON response to `outbox/` directory  
- Are deterministic and reproducible
- Return structured error information

## Available Tools

### 1. run_experiment.py

**Purpose**: Executes backtest or training runs for trading strategies

**Input Schema**:
```json
{
  "tool": "run_experiment",
  "request_id": "string",
  "params": {
    "strategy": "string",
    "strategy_type": "string", 
    "market_data": {
      "pair": "string",
      "timeframe": "string", 
      "start_date": "string",
      "end_date": "string"
    },
    "parameters": {
      "fast_period": "number",
      "slow_period": "number",
      "rsi_period": "number",
      "threshold": "number"
    },
    "seed": "number"
  }
}
```

**Output Schema**:
```json
{
  "request_id": "string",
  "timestamp": "number",
  "status": "OK|ERROR",
  "strategy": "string",
  "results": {
    "scores": {
      "total_score": "number",
      "sharpe_ratio": "number", 
      "max_drawdown": "number",
      "win_rate": "number",
      "profit_factor": "number",
      "total_return": "number",
      "calmar_ratio": "number"
    }
  },
  "artifacts": {
    "log_file": "string"
  },
  "error": "string"  // Only if status=ERROR
}
```

**Usage Example**:
```bash
python tools/run_experiment.py inbox/run_experiment_001.json
```

---

### 2. evaluate_features.py

**Purpose**: Computes feature importances and statistical analysis from experiment results

**Input Schema**:
```json
{
  "tool": "evaluate_features",
  "request_id": "string",
  "params": {
    "experiment_results": ["string"],  // List of result file paths
    "feature_types": ["performance", "risk", "market_regime"],
    "analysis_depth": "standard|thorough"
  }
}
```

**Output Schema**:
```json
{
  "request_id": "string", 
  "timestamp": "number",
  "status": "OK|ERROR",
  "analysis_summary": {
    "total_experiments": "number",
    "successful_experiments": "number",
    "strategy_types_analyzed": "number"
  },
  "feature_importance": {
    "correlation_matrix": {},
    "feature_importance": {},
    "statistical_significance": {}
  },
  "strategy_patterns": {
    "strategy_type_performance": {},
    "best_strategy_type": "string",
    "most_consistent_type": "string"
  },
  "recommendations": ["string"],
  "statistics": {
    "mean_score": "number",
    "score_std": "number", 
    "best_score": "number",
    "score_range": "number"
  }
}
```

**Usage Example**:
```bash
python tools/evaluate_features.py inbox/evaluate_features_001.json
```

---

### 3. score_strategy.py

**Purpose**: Rates and ranks trading strategies based on multi-criteria performance metrics

**Input Schema**:
```json
{
  "tool": "score_strategy",
  "request_id": "string",
  "params": {
    "strategy_results": ["string"],  // List of result file paths
    "scoring_methodology": {
      "weights": {
        "sharpe_ratio": 0.3,
        "max_drawdown": 0.2,
        "win_rate": 0.2, 
        "profit_factor": 0.15,
        "calmar_ratio": 0.15
      },
      "risk_adjustment": true,
      "regime_analysis": true
    },
    "benchmark_comparison": true
  }
}
```

**Output Schema**:
```json
{
  "request_id": "string",
  "timestamp": "number", 
  "status": "OK|ERROR",
  "scoring_summary": {
    "methodology_used": {},
    "weights_applied": {},
    "benchmark_comparison": boolean
  },
  "rankings": [
    {
      "rank": "number",
      "strategy_name": "string",
      "composite_score": "number",
      "confidence_lower": "number",
      "confidence_upper": "number", 
      "individual_metrics": {}
    }
  ],
  "scoring_statistics": {
    "mean_composite_score": "number",
    "score_std": "number",
    "best_score": "number",
    "score_range": "number",
    "num_strategies": "number"
  },
  "regime_analysis": {
    "robustness_score": "number",
    "bull_market_performance": "number",
    "bear_market_performance": "number", 
    "sideways_performance": "number"
  },
  "top_strategies": [],
  "recommendations": ["string"]
}
```

**Usage Example**:
```bash
python tools/score_strategy.py inbox/score_strategy_001.json
```

---

### 4. generate_report.py

**Purpose**: Creates human-readable reports from strategy analysis results

**Input Schema**:
```json
{
  "tool": "generate_report",
  "request_id": "string", 
  "params": {
    "selected_strategy": "string",
    "strategy_rankings": ["string"],  // List of ranking file paths
    "report_format": "html|json|markdown",
    "include_sections": [
      "executive_summary",
      "performance_analysis",
      "risk_assessment", 
      "regime_analysis",
      "recommendations"
    ],
    "output_path": "string"
  }
}
```

**Output Schema**:
```json
{
  "request_id": "string",
  "timestamp": "number",
  "status": "OK|ERROR", 
  "report_file": "string",
  "report_format": "string",
  "sections_included": ["string"],
  "strategies_analyzed": "number",
  "selected_strategy": "string"
}
```

**Usage Example**:
```bash
python tools/generate_report.py inbox/generate_report_001.json
```

---

## File Watcher System

### file_watcher.py

**Purpose**: Monitors `inbox/` directory and automatically executes corresponding tools

**Features**:
- Automatically detects new JSON request files in `inbox/`
- Routes requests to appropriate tool based on `tool` field
- Moves processed requests to `inbox/processed/`
- Provides real-time feedback on execution status

**Usage**:
```bash
# Start watcher for current run
python tools/file_watcher.py --run-dir current

# Start watcher for specific run
python tools/file_watcher.py --run-dir run_20251028_001
```

## Directory Structure

```
runs/
└── current/                     # Active run directory
    ├── inbox/                   # Tool requests (input)
    │   ├── run_experiment_001.json
    │   ├── evaluate_features_001.json
    │   └── processed/           # Completed requests
    ├── outbox/                  # Tool responses (output)
    │   ├── run_experiment_001.json
    │   ├── evaluate_features_001.json
    │   └── score_strategy_001.json
    ├── state/
    │   └── digest.md           # Shared agent context
    └── results/                 # Generated reports
        └── strategy_report.html
```

## Error Handling

All tools follow consistent error handling:

1. **Input Validation**: Validate JSON schema before processing
2. **Graceful Degradation**: Return structured error information
3. **Logging**: Detailed error messages for debugging
4. **Non-zero Exit**: Return exit code 1 for errors, 0 for success

## Dependencies

Tools require the following Python packages:
- `numpy`, `pandas` for data processing
- `scipy` for statistical analysis
- `watchdog` for file system monitoring
- Existing `stratval` trading system components

## Integration with Claude Code

Tools are designed to be called from Claude agents:

1. **Agent writes JSON request** to `inbox/tool_name_*.json`
2. **File watcher detects** new file automatically
3. **Appropriate tool executes** with JSON input
4. **Tool writes JSON response** to `outbox/tool_name_*.json`
5. **Agent reads response** and continues workflow

This file-based messaging enables reproducible, traceable execution while maintaining Claude's local operation model.
