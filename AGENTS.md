# Claude Code Trading System Agents

This document describes the Claude sub-agents that orchestrate the trading system workflow using deterministic tools.

## Overview

The Claude Code trading system uses a multi-agent architecture:
- **Orchestrator**: Main coordinator driving the workflow
- **ExperimentPlanner**: Designs and plans strategy experiments  
- **FeatureEvaluator**: Analyzes experiment outcomes and feature importance
- **ScoringAgent**: Ranks strategies using multi-criteria scoring
- **SelectionAgent**: Makes final decisions and generates reports

All agents communicate through file-based messaging and maintain shared context in `state/digest.md`.

---

## Orchestrator Agent

**File**: `.claude/agents/Orchestrator.md`

**Role**: Main coordinator that drives the entire trading system workflow

**Key Responsibilities**:
- Initialize new trading system runs
- Coordinate handoffs between sub-agents  
- Maintain global state and context
- Make final decisions based on agent recommendations
- Ensure reproducibility and proper logging

**Workflow**:
1. Start new run by creating `runs/<run_id>/` structure
2. Trigger ExperimentPlanner for initial experiment design
3. Receive experiment results and trigger FeatureEvaluator
4. Receive feature analysis and trigger ScoringAgent  
5. Receive scoring results and trigger SelectionAgent
6. Compile final results and generate summary

**Input Example**:
```json
{
  "command": "start_run",
  "params": {
    "objective": "Find profitable mean reversion strategies for BTC/USDT",
    "strategy_types": ["moving_average", "rsi", "bollinger"],
    "market_data": {
      "pair": "BTC/USDT",
      "timeframe": "1h", 
      "date_range": ["2020-01-01", "2023-12-31"]
    },
    "experiment_count": 10
  }
}
```

**Output**: Updates to `state/digest.md`, tool requests, final summary

---

## ExperimentPlanner Agent

**File**: `.claude/agents/ExperimentPlanner.md`

**Role**: Designs and plans individual trading strategy experiments

**Key Responsibilities**:
- Analyze market data characteristics
- Design experiment parameters (strategies, timeframes, conditions)
- Create structured tool requests for `run_experiment`
- Build on previous results from digest

**Strategy Templates**:
- Moving Average Crossover
- RSI Mean Reversion
- MACD Momentum  
- Bollinger Band Breakout
- Volume Price Analysis

**Tool Request Examples**:

**RSI Strategy Example**:
```json
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
```

**Bollinger Band Strategy Example**:
```json
{
  "tool": "run_experiment",
  "request_id": "exp_002",
  "params": {
    "strategy": "Bollinger band mean reversion strategy",
    "strategy_type": "bollinger",
    "market_data": {
      "pair": "BTC/USDT",
      "timeframe": "1h",
      "start_date": "2020-01-01", 
      "end_date": "2023-12-31"
    },
    "parameters": {
      "period": 20,
      "deviation": 2.0
    },
    "seed": 43
  }
}
```

**Moving Average Crossover Example**:
```json
{
  "tool": "run_experiment",
  "request_id": "exp_003",
  "params": {
    "strategy": "Moving average crossover strategy",
    "strategy_type": "moving_average",
    "market_data": {
      "pair": "BTC/USDT",
      "timeframe": "1h",
      "start_date": "2020-01-01", 
      "end_date": "2023-12-31"
    },
    "parameters": {
      "fast_period": 10,
      "slow_period": 30
    },
    "seed": 44
  }
}
```

**Output**: JSON tool request in `inbox/run_experiment_*.json`, rationale in digest

---

## FeatureEvaluator Agent

**File**: `.claude/agents/FeatureEvaluator.md`

**Role**: Analyzes experiment outcomes to identify important features and patterns

**Key Responsibilities**:
- Analyze experiment results for feature importance
- Identify statistical significance and patterns
- Request additional experiments if needed
- Evaluate feature stability across conditions

**Evaluation Criteria**:
- Performance metrics consistency
- Risk-adjusted returns stability
- Market regime robustness
- Feature correlation analysis

**Tool Request Example**:
```json
{
  "tool": "evaluate_features",
  "request_id": "feat_001", 
  "params": {
    "experiment_results": [
      "outbox/run_experiment_exp_001.json",
      "outbox/run_experiment_exp_002.json"
    ],
    "feature_types": ["performance", "risk", "market_regime"],
    "analysis_depth": "standard"
  }
}
```

**Output**: Feature analysis request, importance findings, recommendations

---

## ScoringAgent Agent

**File**: `.claude/agents/ScoringAgent.md`

**Role**: Scores and ranks trading strategies based on multiple performance dimensions

**Key Responsibilities**:
- Apply multi-criteria scoring methodology
- Rank strategies across different market conditions
- Evaluate consistency and robustness
- Generate composite scores with confidence intervals

**Scoring Methodology**:
1. **Risk-Adjusted Returns**: Sharpe, Sortino, Calmar ratios
2. **Drawdown Analysis**: Maximum drawdown, drawdown duration
3. **Consistency Metrics**: Win rate, profit factor, expectancy
4. **Regime Robustness**: Performance across market conditions
5. **Statistical Significance**: p-values, confidence intervals

**Tool Request Example**:
```json
{
  "tool": "score_strategy",
  "request_id": "score_001",
  "params": {
    "strategy_results": [
      "outbox/run_experiment_exp_001.json",
      "outbox/run_experiment_exp_002.json"
    ],
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

**Output**: Scoring request, detailed rankings, confidence intervals

---

## SelectionAgent Agent

**File**: `.claude/agents/SelectionAgent.md`

**Role**: Makes final strategy selection decisions and generates comprehensive reports

**Key Responsibilities**:
- Analyze scored strategies and rankings
- Make final selection with justification
- Generate human-readable reports
- Document decision rationale

**Selection Criteria**:
1. **Score Thresholds**: Minimum performance benchmarks
2. **Robustness**: Consistency across market regimes
3. **Risk Management**: Acceptable drawdown profiles
4. **Practicality**: Implementation feasibility
5. **Diversification**: Correlation with existing strategies

**Tool Request Example**:
```json
{
  "tool": "generate_report", 
  "request_id": "report_001",
  "params": {
    "selected_strategy": "RSI oversold bounce with 14 period",
    "strategy_rankings": [
      "outbox/score_strategy_score_001.json"
    ],
    "report_format": "html",
    "include_sections": [
      "executive_summary",
      "performance_analysis", 
      "risk_assessment",
      "regime_analysis",
      "recommendations"
    ],
    "output_path": "strategy_analysis_report.html"
  }
}
```

**Output**: Report generation request, final decision rationale, workflow completion

---

## Agent Communication Pattern

### File-Based Messaging

1. **Request Creation**: Agent writes JSON request to `inbox/tool_name_*.json`
2. **Automatic Execution**: File watcher detects and executes appropriate tool
3. **Response Processing**: Tool writes JSON response to `outbox/tool_name_*.json`
4. **Context Update**: Agent reads response and updates `state/digest.md`

### Shared Context (Digest)

All agents maintain shared context in `state/digest.md`:

```markdown
# Trading System Run Digest - 2025-10-28

## Run Initialization
- Objective: Find profitable mean reversion strategies for BTC/USDT
- Market Data: BTC/USDT 1h timeframe (2020-2023)
- Target: 10 experiments across 3 strategy families

## Experiment Planning (ExperimentPlanner)
- Exp 001: RSI oversold bounce (rsi_period=14, threshold=30)
- Exp 002: Moving average crossover (fast=10, slow=30)  
- Exp 003: Bollinger band mean reversion (period=20, dev=2.0)
- Rationale: Diverse parameter space exploration with reproducible seeds

## Experiment Results
- Exp 001: Total Score 72.3, Sharpe 1.45, Max DD 18.2%
- Exp 002: Total Score 68.1, Sharpe 1.32, Max DD 22.1% 
- Exp 003: Total Score 75.8, Sharpe 1.58, Max DD 15.7%

## Feature Analysis (FeatureEvaluator)
- Key Features: Sharpe ratio (0.89 correlation), Max drawdown (-0.76)
- Strategy Performance: Bollinger > RSI > Moving Average
- Recommendation: Additional experiments needed for statistical significance

## Strategy Scoring (ScoringAgent)  
- Top Strategy: Bollinger band mean reversion (Composite: 0.78)
- Robustness: 0.71 (good across market regimes)
- Confidence: ±0.05 (95% CI)

## Final Selection (SelectionAgent)
- Selected: Bollinger band mean reversion strategy
- Rationale: Highest composite score, good robustness, acceptable risk
- Next Steps: Forward testing, position sizing optimization
```

---

## Agent Execution Flow

### Initialization Phase
```
Orchestrator → creates run structure → triggers ExperimentPlanner
```

### Experiment Phase  
```
ExperimentPlanner → writes tool requests → File watcher → run_experiment
                → reads results → updates digest → triggers FeatureEvaluator
```

### Analysis Phase
```
FeatureEvaluator → writes analysis request → File watcher → evaluate_features  
               → reads analysis → updates digest → triggers ScoringAgent
```

### Scoring Phase
```
ScoringAgent → writes scoring request → File watcher → score_strategy
            → reads rankings → updates digest → triggers SelectionAgent
```

### Selection Phase
```
SelectionAgent → writes report request → File watcher → generate_report
              → reads report → updates digest → signals completion to Orchestrator
```

### Completion Phase
```
Orchestrator → compiles final summary → archives run → reports results
```

---

## Agent Prompts and Context

Each agent operates with:
- **Specific role definition** from their `.md` file
- **Current run context** from `state/digest.md`
- **Tool schema knowledge** from `TOOLS.md`
- **Previous agent decisions** from digest history
- **Reproducible deterministic behavior** through structured prompts

This architecture ensures all reasoning, decisions, and tool interactions are traceable, reproducible, and locally contained within the Claude Code environment.
