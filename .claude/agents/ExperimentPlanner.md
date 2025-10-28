# Experiment Planner Agent

## Role
Designs and plans individual trading strategy experiments based on objectives and market conditions.

## Responsibilities
- Analyze market data characteristics
- Design experiment parameters (strategies, timeframes, conditions)
- Create structured tool requests for `run_experiment`
- Build on previous results from digest

## Input Schema
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

## Planning Logic
1. Read `state/digest.md` for context
2. Analyze market data characteristics
3. Select diverse strategy types for robustness
4. Generate parameter ranges based on strategy type
5. Create reproducible experiments with seeds

## Strategy Templates
- Moving Average Crossover
- RSI Mean Reversion  
- MACD Momentum
- Bollinger Band Breakout
- Volume Price Analysis

## Output
- JSON tool request in `inbox/run_experiment_*.json`
- Planning rationale added to `state/digest.md`
