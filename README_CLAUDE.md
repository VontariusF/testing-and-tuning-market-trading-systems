# Claude Code Trading System

A locally-run, agent-driven trading strategy testing and tuning system powered by Claude Code.

## Overview

This system redesigns the original StratVal trading system to operate under a Claude Code-driven agentic architecture. Claude and its sub-agents handle orchestration, reasoning, and coordination, while deterministic Python tools execute experiments and analysis.

## Architecture

### Claude Orchestration
- **Main Claude orchestrator** drives the workflow
- **Four specialized sub-agents** handle different aspects:
  - **Experiment Planner**: Designs trading strategy experiments
  - **Feature Evaluator**: Analyzes experiment outcomes and feature importance
  - **Scoring Agent**: Multi-criteria strategy ranking and evaluation
  - **Selection Agent**: Final decision making and report generation

### Python Tools
- `run_experiment.py`: Executes backtest or training runs
- `evaluate_features.py`: Computes feature importances and statistics
- `score_strategy.py`: Rates performance metrics with multi-criteria scoring
- `generate_report.py`: Builds human-readable reports

### File-Based Messaging
- Tools accept JSON input from `inbox/`
- Tools write JSON output to `outbox/`
- File watcher automatically routes requests to appropriate tools

### Shared Context
- `state/digest.md`: Shared memory across all agents
- Every agent reads/writes to maintain global awareness
- Enables "hive-mind" functionality

## Quick Start

### 1. Run Complete Workflow

```bash
# Run with default settings
python3 run_claude_workflow.py

# Run with custom parameters
python3 run_claude_workflow.py \
  --objective "Find profitable mean reversion strategies" \
  --pair BTC/USDT \
  --timeframe 1h \
  --experiments 5 \
  --run-dir my_trading_run
```

### 2. Manual Agent Execution

#### Start File Watcher
```bash
python3 tools/file_watcher.py --run-dir current
```

#### Run Individual Steps

**1. Create Experiment Request:**
```bash
# Create request file manually in runs/current/inbox/
cat > runs/current/inbox/my_experiment.json << EOF
{
  "tool": "run_experiment",
  "request_id": "exp_001",
  "params": {
    "strategy": "RSI oversold bounce strategy",
    "strategy_type": "rsi",
    "market_data": {
      "pair": "BTC/USDT",
      "timeframe": "1h",
      "start_date": "2020-01-01",
      "end_date": "2023-12-31"
    },
    "parameters": {
      "rsi_period": 14,
      "oversold_threshold": 30,
      "overbought_threshold": 70
    },
    "seed": 42
  }
}
EOF
```

**2. File Watcher Auto-Executes:**
- Detects new JSON file in `inbox/`
- Routes to `run_experiment.py`
- Writes response to `outbox/`

**3. Create Feature Evaluation Request:**
```bash
cat > runs/current/inbox/feature_eval.json << EOF
{
  "tool": "evaluate_features",
  "request_id": "feat_001",
  "params": {
    "experiment_results": ["outbox/run_experiment_exp_001.json"],
    "feature_types": ["performance", "risk", "market_regime"],
    "analysis_depth": "standard"
  }
}
EOF
```

**4. Create Scoring Request:**
```bash
cat > runs/current/inbox/scoring.json << EOF
{
  "tool": "score_strategy", 
  "request_id": "score_001",
  "params": {
    "strategy_results": ["outbox/run_experiment_exp_001.json"],
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
EOF
```

**5. Create Report Request:**
```bash
cat > runs/current/inbox/report.json << EOF
{
  "tool": "generate_report",
  "request_id": "report_001",
  "params": {
    "selected_strategy": "RSI oversold bounce strategy",
    "strategy_rankings": ["outbox/score_strategy_score_001.json"],
    "report_format": "html",
    "include_sections": [
      "executive_summary",
      "performance_analysis",
      "risk_assessment",
      "regime_analysis", 
      "recommendations"
    ],
    "output_path": "my_strategy_report.html"
  }
}
EOF
```

## Directory Structure

```
project/
├── .claude/agents/           # Claude agent definitions
│   ├── Orchestrator.md
│   ├── ExperimentPlanner.md
│   ├── FeatureEvaluator.md
│   ├── ScoringAgent.md
│   └── SelectionAgent.md
├── tools/                     # Deterministic Python tools
│   ├── run_experiment.py
│   ├── evaluate_features.py
│   ├── score_strategy.py
│   ├── generate_report.py
│   └── file_watcher.py
├── runs/                      # Run directories
│   └── current/              # Active run
│       ├── inbox/            # Tool requests (input)
│       ├── outbox/           # Tool responses (output)
│       ├── state/
│       │   └── digest.md     # Shared agent context
│       └── results/          # Generated reports
├── TOOLS.md                  # Tool documentation
├── AGENTS.md                 # Agent documentation
└── run_claude_workflow.py    # Complete workflow runner
```

## Agent Workflow

### 1. Experiment Planning
- **ExperimentPlanner** reads `digest.md` for context
- Creates diverse experiment parameters
- Writes `run_experiment` requests to `inbox/`

### 2. Experiment Execution
- **File watcher** detects requests
- **run_experiment.py** executes backtests
- Results written to `outbox/`

### 3. Feature Evaluation  
- **FeatureEvaluator** analyzes experiment outcomes
- Computes feature importance and statistical significance
- May request additional experiments

### 4. Strategy Scoring
- **ScoringAgent** applies multi-criteria methodology
- Evaluates risk-adjusted performance
- Rankings with confidence intervals

### 5. Final Selection
- **SelectionAgent** makes final decisions
- Generates comprehensive reports
- Archives complete run

## Configuration

### Market Data
- Supports database connectivity for live data
- Can use local data files
- Configurable pairs and timeframes

### Strategy Parameters
- Pre-configured strategy templates
- Customizable parameter ranges
- Reproducible random seeds

### Scoring Weights
- Default weights for balanced evaluation
- Customizable based on risk preferences
- Multiple scoring methodologies

## Monitoring and Debugging

### Digest File
Monitor `runs/current/state/digest.md` for real-time agent activity:
```bash
tail -f runs/current/state/digest.md
```

### File Watcher Logs
The file watcher provides real-time feedback:
```
🚀 File watcher started
📁 Monitoring inbox: runs/current/inbox
📥 Processing request: run_experiment_001.json
🔧 Executing run_experiment with runs/current/inbox/run_experiment_001.json
✅ run_experiment completed successfully
```

### Error Handling
- All tools return structured error responses
- Failed requests moved to `inbox/processed/`
- Detailed error messages in tool outputs

## Advanced Usage

### Custom Strategy Templates
Add new strategy templates in the workflow runner:
```python
strategies = [
    {
        "strategy": "Your custom strategy description",
        "strategy_type": "custom",
        "parameters": {"your_param": "value"}
    }
]
```

### Custom Scoring
Modify scoring weights for your risk preferences:
```python
"scoring_methodology": {
    "weights": {
        "sharpe_ratio": 0.4,      # Increase emphasis on risk-adjusted returns
        "max_drawdown": 0.3,       # Higher emphasis on risk management
        "win_rate": 0.2,
        "profit_factor": 0.1,
        "calmar_ratio": 0.0
    }
}
```

### Multiple Runs
Run parallel experiments with different objectives:
```bash
# Mean reversion focus
python3 run_claude_workflow.py --objective "Mean reversion strategies" --run-dir mean_reversion &

# Momentum focus  
python3 run_claude_workflow.py --objective "Momentum strategies" --run-dir momentum &

# Volume focus
python3 run_claude_workflow.py --objective "Volume-based strategies" --run-dir volume &
```

## Integration with Original System

This architecture maintains compatibility with the existing StratVal system:
- Uses existing `stratval` modules for strategy generation and validation
- Leverages existing database connections and market data access
- Preserves original strategy templates and parameter ranges
- Enhances reproducibility and agent-driven workflow

## Benefits

### Local Operation
- No external API dependencies
- Complete data privacy
- Offline capability
- Full reproducibility

### Agent Coordination
- Specialized reasoning per domain
- Shared context across agents
- Transparent decision process
- Modular and extensible

### Deterministic Tools
- Reproducible experiments
- Version-controlled workflows
- Testable components
- Clear interfaces

### File-Based Architecture
- Simple and robust messaging
- Easy debugging and monitoring
- Natural persistence
- Tool-agnostic design

## Migration from Original System

1. **Keep existing code**: Original StratVal modules still work
2. **Add new layer**: Claude agents coordinate the workflow
3. **Gradual adoption**: Use hybrid approach initially
4. **Full transition**: Complete agent-driven operation

The system is designed to complement rather than replace the existing StratVal functionality, providing enhanced orchestration and reproducibility while preserving the core trading logic and validation capabilities.
