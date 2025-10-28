#pragma once

#include "strategy.h"
#include <vector>
#include <string>
#include <memory>
#include <functional>

// Strategy test configuration
struct StrategyTestConfig {
  std::string strategy_name;
  std::vector<double> parameters;
  std::string symbol = "DEMO";
  double initial_capital = 100000.0;
  int max_bars = 1000;
  bool enable_risk_management = true;
  bool enable_volatility_sizing = true;
  bool enable_atr_stops = true;
};

// Strategy performance metrics for evaluation
struct StrategyMetrics {
  std::string strategy_name;
  std::vector<double> parameters;
  std::string symbol;

  // Performance metrics
  double total_return = 0.0;
  double sharpe_ratio = 0.0;
  double max_drawdown = 0.0;
  double win_rate = 0.0;
  double profit_factor = 0.0;
  double avg_trade = 0.0;
  int total_trades = 0;

  // Risk metrics
  double calmar_ratio = 0.0;
  double sortino_ratio = 0.0;
  double var_95 = 0.0;  // 95% Value at Risk
  double expected_shortfall = 0.0;

  // Strategy characteristics
  double avg_hold_period = 0.0;
  double max_adverse_excursion = 0.0;
  double max_favorable_excursion = 0.0;

  // Ranking score
  double composite_score = 0.0;

  // Original market data for statistical validation (lookahead bias detection)
  std::vector<Bar> market_data;

  // Helper method to calculate composite score
  void calculate_composite_score();
};

// Strategy parameter generation configuration
struct ParameterGenConfig {
  std::string strategy_type;
  std::vector<std::pair<double, double>> parameter_ranges;  // min, max for each parameter
  int num_samples = 100;  // Number of parameter combinations to generate
  std::string generation_method = "random";  // "random", "grid", "lhs"
  double mutation_rate = 0.1;  // For genetic algorithm approaches
};

// Strategy testing framework
class StrategyTester {
public:
  StrategyTester() = default;
  ~StrategyTester() = default;

  // Test a single strategy configuration
  StrategyMetrics test_strategy(const StrategyTestConfig& config, const std::vector<Bar>& data);

  // Generate multiple strategy configurations
  std::vector<StrategyTestConfig> generate_strategy_configs(const ParameterGenConfig& gen_config);

  // Test multiple strategies and return ranked results
  std::vector<StrategyMetrics> test_multiple_strategies(
      const std::vector<StrategyTestConfig>& configs,
      const std::vector<Bar>& data);

  // Select top performing strategies
  std::vector<StrategyMetrics> select_top_strategies(
      const std::vector<StrategyMetrics>& results,
      int num_top = 10);

  // Generate strategy evolution (genetic algorithm approach)
  std::vector<StrategyTestConfig> evolve_strategies(
      const std::vector<StrategyMetrics>& current_generation,
      const ParameterGenConfig& gen_config);

private:
  // Metrics calculation helpers
  double calculate_sharpe_ratio(const std::vector<double>& returns);
  double calculate_sortino_ratio(const std::vector<double>& returns);
  double calculate_max_drawdown(const std::vector<double>& portfolio_values);
  double calculate_var(const std::vector<double>& returns, double confidence = 0.95);
  double calculate_expected_shortfall(const std::vector<double>& returns, double confidence = 0.95);

  // Parameter generation methods (can also be made public if needed)
  std::vector<double> generate_random_parameters(const std::vector<std::pair<double, double>>& ranges);

public:
  static std::vector<double> generate_random_parameters_static(const std::vector<std::pair<double, double>>& ranges);
  std::vector<double> generate_grid_parameters(const std::vector<std::pair<double, double>>& ranges, int samples);
  std::vector<double> mutate_parameters(const std::vector<double>& params, double mutation_rate);

  // Strategy creation helpers
  std::unique_ptr<Strategy> create_sma_strategy(const std::vector<double>& params);

  // Utility methods
  std::vector<double> run_strategy_simulation(
      std::unique_ptr<Strategy>& strategy,
      const std::vector<Bar>& data);

public:
  void print_strategy_metrics(const StrategyMetrics& metrics);
  void print_strategy_comparison(const std::vector<StrategyMetrics>& metrics);

  // Data integrity validation methods
  static void validate_chronological_order(const std::vector<Bar>& data);
  static void validate_data_integrity(const std::vector<Bar>& data);
  static void validate_ohlc_relationships(const std::vector<Bar>& data);
};

// Strategy portfolio for combining multiple strategies
struct StrategyPortfolio {
  std::vector<StrategyMetrics> strategies;
  std::vector<double> weights;  // Weight for each strategy in portfolio
  double portfolio_return = 0.0;
  double portfolio_sharpe = 0.0;
  double portfolio_max_dd = 0.0;

  // Portfolio construction methods
  void equal_weight();
  void sharpe_weight();
  void risk_parity_weight();
  void calculate_portfolio_metrics();
};

// Global functions for easy access
namespace StrategyGeneration {

  // Generate SMA strategy configurations
  std::vector<StrategyTestConfig> generate_sma_configs(
      int num_configs = 50,
      int short_min = 5, int short_max = 50,
      int long_min = 20, int long_max = 200);

  // Generate RSI strategy configurations
  std::vector<StrategyTestConfig> generate_rsi_configs(
      int num_configs = 30,
      int period_min = 7, int period_max = 25,
      double overbought_min = 65.0, double overbought_max = 85.0,
      double oversold_min = 15.0, double oversold_max = 35.0,
      int confirm_min = 1, int confirm_max = 4);

  // Generate MACD strategy configurations
  std::vector<StrategyTestConfig> generate_macd_configs(
      int num_configs = 30,
      int fast_min = 8, int fast_max = 15,
      int slow_min = 20, int slow_max = 35,
      int signal_min = 5, int signal_max = 12,
      double overbought_min = 0.5, double overbought_max = 1.5,
      double oversold_min = -1.5, double oversold_max = -0.5);

  // Generate comprehensive strategy test suite
  std::vector<StrategyTestConfig> generate_comprehensive_test_suite();

  // Quick strategy testing with default parameters
  StrategyMetrics quick_test_strategy(const std::string& strategy_type,
                                    const std::vector<double>& params,
                                    const std::vector<Bar>& data);

}
