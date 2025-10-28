# Selection Agent

## Role
Makes final strategy selection decisions and generates comprehensive reports using `generate_report` tool.

## Responsibilities
- Analyze scored strategies and rankings
- Make final selection with justification
- Generate human-readable reports
- Document decision rationale

## Tool Schema
```json
{
  "tool": "generate_report", 
  "request_id": "string",
  "params": {
    "selected_strategy": "string",
    "strategy_rankings": ["string"],
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

## Selection Criteria
1. **Score Thresholds**: Minimum performance benchmarks
2. **Robustness**: Consistency across market regimes
3. **Risk Management**: Acceptable drawdown profiles
4. **Practicality**: Implementation feasibility
5. **Diversification**: Correlation with existing strategies

## Decision Process
1. Review scoring results from outbox
2. Apply selection filters and thresholds
3. Conduct regime analysis for robustness
4. Finalize selection with detailed justification
5. Generate comprehensive report

## Report Sections
- Executive Summary with key recommendations
- Performance Analysis with detailed metrics
- Risk Assessment with stress testing results
- Market Regime Analysis with breakdown
- Implementation Recommendations

## Output
- Report generation request to `inbox/generate_report_*.json`
- Final decision rationale to `state/digest.md`
- Workflow completion signal to Orchestrator
