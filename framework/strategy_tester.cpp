#include "strategy_tester.h"
#include "strategy.h"
#include "strategy_factory.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <numeric>
#include <random>
#include <cmath>
#include <iomanip>

// Calculate composite score for strategy ranking
void StrategyMetrics::calculate_composite_score() {
  // Weighted composite score favoring:
  // 1. High Sharpe ratio (40% weight)
  // 2. Low max drawdown (30% weight)
  // 3. High total return (20% weight)
  // 4. Reasonable number of trades (10% weight)

  double sharpe_score = std::min(sharpe_ratio / 2.0, 1.0);  // Normalize Sharpe
  double drawdown_score = std::max(0.0, 1.0 - max_drawdown);  // Lower drawdown = higher score
  double return_score = std::min(total_return / 0.5, 1.0);   // Normalize returns
  double trade_score = std::min(static_cast<double>(total_trades) / 50.0, 1.0);  // Prefer adequate trading

  composite_score = (sharpe_score * 0.4) + (drawdown_score * 0.3) +
                   (return_score * 0.2) + (trade_score * 0.1);
}

// Test a single strategy configuration
StrategyMetrics StrategyTester::test_strategy(const StrategyTestConfig& config, const std::vector<Bar>& data) {
  StrategyMetrics metrics;
  metrics.strategy_name = config.strategy_name;
  metrics.parameters = config.parameters;
  metrics.symbol = config.symbol;

  try {
    // Phase 1: Data Integrity Validation
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "PHASE 1: DATA INTEGRITY VALIDATION" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    // Validate data integrity to prevent lookahead bias
    validate_chronological_order(data);
    validate_data_integrity(data);
    validate_ohlc_relationships(data);

    std::cout << "\n✅ Data validation complete - proceeding with strategy testing\n" << std::endl;

    // Create strategy based on name and parameters
    std::unique_ptr<Strategy> strategy = StrategyFactory::create_strategy(
        config.strategy_name, config.parameters, config.symbol);

    if (!strategy) {
      std::cout << "Failed to create strategy: " << config.strategy_name << std::endl;
      return metrics;
    }

    // Configure risk management
    // Note: This would need to be implemented in the strategy classes

    // Run strategy simulation
    std::vector<double> portfolio_values = run_strategy_simulation(strategy, data);

    if (portfolio_values.empty()) {
      std::cout << "No portfolio values generated for strategy" << std::endl;
      return metrics;
    }

    // Calculate returns from portfolio values
    std::vector<double> returns;
    for (size_t i = 1; i < portfolio_values.size(); ++i) {
      double prev = portfolio_values[i - 1];
      if (prev == 0.0) continue;
      double ret = (portfolio_values[i] - prev) / prev;
      returns.push_back(ret);
    }

    // Calculate metrics
    if (!returns.empty()) {
      metrics.total_return = (portfolio_values.back() - config.initial_capital) / config.initial_capital;
      metrics.sharpe_ratio = calculate_sharpe_ratio(returns);
      metrics.max_drawdown = calculate_max_drawdown(portfolio_values);
      metrics.var_95 = calculate_var(returns, 0.95);
      metrics.expected_shortfall = calculate_expected_shortfall(returns, 0.95);
    }

    // Get strategy-specific metrics
    metrics.total_trades = strategy->get_trade_count();

    const auto trades = strategy->get_trades();
    if (!trades.empty()) {
      double total_wins = 0.0;
      double total_losses = 0.0;
      int winning_trades = 0;
      int completed_trades = 0;

      for (const auto& trade : trades) {
        if (trade.type != Trade::Type::EXIT) continue;
        ++completed_trades;
        if (trade.pnl > 0.0) {
          total_wins += trade.pnl;
          ++winning_trades;
        } else if (trade.pnl < 0.0) {
          total_losses += std::abs(trade.pnl);
        }
      }

      if (completed_trades > 0) {
        metrics.total_trades = completed_trades;
        metrics.win_rate = static_cast<double>(winning_trades) / completed_trades;
        metrics.avg_trade = (total_wins - total_losses) / completed_trades;

        if (total_losses > 0.0) {
          metrics.profit_factor = total_wins / total_losses;
        } else if (total_wins > 0.0) {
          metrics.profit_factor = 1000.0;
        }
      }
    }

    // Calculate Calmar ratio (Return / Max Drawdown)
    if (metrics.max_drawdown > 0) {
      metrics.calmar_ratio = metrics.total_return / metrics.max_drawdown;
    }

    // Calculate Sortino ratio (similar to Sharpe but only downside volatility)
    metrics.sortino_ratio = calculate_sortino_ratio(returns);

    // Calculate composite score
    metrics.calculate_composite_score();

    // Store the original market data for statistical validation
    // This is crucial for lookahead bias detection algorithms
    metrics.market_data = data;

  } catch (const std::exception& e) {
    std::cout << "Error testing strategy " << config.strategy_name << ": " << e.what() << std::endl;
  }

  return metrics;
}

// Generate multiple strategy configurations
std::vector<StrategyTestConfig> StrategyTester::generate_strategy_configs(const ParameterGenConfig& gen_config) {
  std::vector<StrategyTestConfig> configs;

  auto random_between = [](double min_val, double max_val) {
    return min_val + (max_val - min_val) * (static_cast<double>(rand()) / RAND_MAX);
  };

  std::string type = gen_config.strategy_type;
  std::transform(type.begin(), type.end(), type.begin(), [](unsigned char c) {
    return static_cast<char>(std::toupper(c));
  });

  const auto& ranges = gen_config.parameter_ranges;

  if (type == "SMA") {
    std::pair<double, double> short_range = ranges.size() > 0 ? ranges[0] : std::make_pair(5.0, 50.0);
    std::pair<double, double> long_range = ranges.size() > 1 ? ranges[1] : std::make_pair(20.0, 200.0);
    std::pair<double, double> fee_range = ranges.size() > 2 ? ranges[2] : std::make_pair(0.0001, 0.0010);

    for (int i = 0; i < gen_config.num_samples; ++i) {
      StrategyTestConfig config;
      config.strategy_name = "SMA";
      config.symbol = "DEMO";

      int short_win = static_cast<int>(random_between(short_range.first, short_range.second));
      int long_win = static_cast<int>(random_between(long_range.first, long_range.second));
      if (short_win >= long_win) {
        long_win = short_win + 5;
      }
      double fee = random_between(fee_range.first, fee_range.second);

      config.parameters = {static_cast<double>(short_win), static_cast<double>(long_win), fee};
      configs.push_back(config);
    }
  } else if (type == "RSI") {
    std::vector<std::pair<double, double>> defaults = {
      {5.0, 30.0},    // period
      {65.0, 90.0},   // overbought
      {10.0, 40.0},   // oversold
      {1.0, 5.0},     // confirmation periods
      {0.0001, 0.001} // fee
    };

    for (int i = 0; i < gen_config.num_samples; ++i) {
      StrategyTestConfig config;
      config.strategy_name = "RSI";
      config.symbol = "DEMO";

      std::vector<double> params;
      for (size_t idx = 0; idx < defaults.size(); ++idx) {
        auto range = (idx < ranges.size()) ? ranges[idx] : defaults[idx];
        params.push_back(random_between(range.first, range.second));
      }

      int period = std::max(2, static_cast<int>(params[0]));
      double overbought = params[1];
      double oversold = params[2];
      if (overbought <= oversold) {
        overbought = oversold + 10.0;
      }
      int confirmation = std::max(1, static_cast<int>(params[3]));
      double fee_val = params[4];

      config.parameters = {
        static_cast<double>(period),
        overbought,
        oversold,
        static_cast<double>(confirmation),
        fee_val
      };
      configs.push_back(config);
    }
  } else if (type == "MACD") {
    std::vector<std::pair<double, double>> defaults = {
      {8.0, 16.0},    // fast period
      {20.0, 40.0},   // slow period
      {5.0, 15.0},    // signal period
      {0.5, 1.5},     // overbought threshold
      {-1.5, -0.5},   // oversold threshold
      {0.0001, 0.001} // fee
    };

    for (int i = 0; i < gen_config.num_samples; ++i) {
      StrategyTestConfig config;
      config.strategy_name = "MACD";
      config.symbol = "DEMO";

      std::vector<double> params;
      for (size_t idx = 0; idx < defaults.size(); ++idx) {
        auto range = (idx < ranges.size()) ? ranges[idx] : defaults[idx];
        params.push_back(random_between(range.first, range.second));
      }

      int fast = std::max(2, static_cast<int>(params[0]));
      int slow = std::max(fast + 4, static_cast<int>(params[1]));
      int signal = std::max(2, static_cast<int>(params[2]));
      double overbought = params[3];
      double oversold = params[4];
      double fee_val = params[5];

      config.parameters = {
        static_cast<double>(fast),
        static_cast<double>(slow),
        static_cast<double>(signal),
        overbought,
        oversold,
        fee_val
      };
      configs.push_back(config);
    }
  }

  return configs;
}

// Test multiple strategies and return ranked results
std::vector<StrategyMetrics> StrategyTester::test_multiple_strategies(
    const std::vector<StrategyTestConfig>& configs,
    const std::vector<Bar>& data) {

  std::vector<StrategyMetrics> results;
  std::cout << "\n" << std::string(80, '=') << std::endl;
  std::cout << "STRATEGY TESTING BATCH - " << configs.size() << " configurations" << std::endl;
  std::cout << std::string(80, '=') << std::endl;

  for (size_t i = 0; i < configs.size(); ++i) {
    const auto& config = configs[i];

    std::cout << "Testing " << (i + 1) << "/" << configs.size() << ": "
              << config.strategy_name;

    if (!config.parameters.empty()) {
      std::cout << " (";
      for (size_t j = 0; j < config.parameters.size(); ++j) {
        std::cout << config.parameters[j];
        if (j < config.parameters.size() - 1) std::cout << ", ";
      }
      std::cout << ")";
    }
    std::cout << std::endl;

    StrategyMetrics metrics = test_strategy(config, data);
    results.push_back(metrics);

    // Print immediate results
    std::cout << "  Result: Return=" << (metrics.total_return * 100.0) << "%, "
              << "Sharpe=" << metrics.sharpe_ratio << ", "
              << "MaxDD=" << (metrics.max_drawdown * 100.0) << "%, "
              << "Trades=" << metrics.total_trades << std::endl;
  }

  // Sort by composite score (descending)
  std::sort(results.begin(), results.end(),
    [](const StrategyMetrics& a, const StrategyMetrics& b) {
      return a.composite_score > b.composite_score;
    });

  std::cout << std::string(80, '=') << std::endl;
  std::cout << "BATCH TESTING COMPLETE" << std::endl;

  return results;
}

// Select top performing strategies
std::vector<StrategyMetrics> StrategyTester::select_top_strategies(
    const std::vector<StrategyMetrics>& results,
    int num_top) {

  int selection_count = std::min(num_top, static_cast<int>(results.size()));

  std::cout << "\n" << std::string(80, '=') << std::endl;
  std::cout << "SELECTING TOP " << selection_count << " STRATEGIES" << std::endl;
  std::cout << std::string(80, '=') << std::endl;

  std::vector<StrategyMetrics> top_strategies(results.begin(), results.begin() + selection_count);

  print_strategy_comparison(top_strategies);

  return top_strategies;
}

// Helper methods implementation - simplified to use factory only
std::unique_ptr<Strategy> StrategyTester::create_sma_strategy(const std::vector<double>& params) {
  if (params.size() >= 3) {
    int short_win = std::max(2, static_cast<int>(params[0]));
    int long_win = std::max(short_win + 5, static_cast<int>(params[1]));
    double fee = params[2];
    return StrategyFactory::create_sma_strategy(short_win, long_win, fee, "DEMO");
  }
  return nullptr;
}

double StrategyTester::calculate_sharpe_ratio(const std::vector<double>& returns) {
  if (returns.size() < 2) return 0.0;

  double mean_return = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();

  double variance = 0.0;
  for (double ret : returns) {
    variance += (ret - mean_return) * (ret - mean_return);
  }
  variance /= (returns.size() - 1);

  double std_dev = std::sqrt(variance);
  if (std_dev == 0.0) return 0.0;

  double risk_free_rate = 0.02;  // 2% annual risk-free rate
  double annualized_return = mean_return * 252;  // Assuming daily returns

  return (annualized_return - risk_free_rate) / (std_dev * std::sqrt(252));
}

double StrategyTester::calculate_max_drawdown(const std::vector<double>& portfolio_values) {
  if (portfolio_values.size() < 2) return 0.0;

  double peak = portfolio_values[0];
  double max_dd = 0.0;

  for (size_t i = 1; i < portfolio_values.size(); ++i) {
    if (portfolio_values[i] > peak) {
      peak = portfolio_values[i];
    } else {
      double dd = (peak - portfolio_values[i]) / peak;
      if (dd > max_dd) {
        max_dd = dd;
      }
    }
  }

  return max_dd;
}

double StrategyTester::calculate_var(const std::vector<double>& returns, double confidence) {
  if (returns.empty()) return 0.0;

  std::vector<double> sorted_returns = returns;
  std::sort(sorted_returns.begin(), sorted_returns.end());

  size_t index = static_cast<size_t>((1.0 - confidence) * sorted_returns.size());
  if (index >= sorted_returns.size()) index = sorted_returns.size() - 1;

  return -sorted_returns[index];  // VaR is positive value representing loss
}

double StrategyTester::calculate_expected_shortfall(const std::vector<double>& returns, double confidence) {
  if (returns.empty()) return 0.0;

  double var_threshold = calculate_var(returns, confidence);

  double sum_losses = 0.0;
  int count_losses = 0;

  for (double ret : returns) {
    if (-ret >= var_threshold) {  // Losses exceeding VaR threshold
      sum_losses += -ret;
      count_losses++;
    }
  }

  return count_losses > 0 ? sum_losses / count_losses : 0.0;
}

double StrategyTester::calculate_sortino_ratio(const std::vector<double>& returns) {
  if (returns.size() < 2) return 0.0;

  double mean_return = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();

  // Calculate downside variance (only negative returns)
  double downside_variance = 0.0;
  int downside_count = 0;

  for (double ret : returns) {
    if (ret < 0) {
      downside_variance += ret * ret;
      downside_count++;
    }
  }

  if (downside_count == 0 || downside_variance == 0.0) return 0.0;

  downside_variance /= downside_count;
  double downside_std_dev = std::sqrt(downside_variance);

  double risk_free_rate = 0.02;
  double annualized_return = mean_return * 252;

  return (annualized_return - risk_free_rate) / (downside_std_dev * std::sqrt(252));
}

std::vector<double> StrategyTester::generate_random_parameters(const std::vector<std::pair<double, double>>& ranges) {
  std::vector<double> params;
  for (const auto& range : ranges) {
    double param = range.first + (range.second - range.first) * (static_cast<double>(rand()) / RAND_MAX);
    params.push_back(param);
  }
  return params;
}

std::vector<double> StrategyTester::generate_random_parameters_static(const std::vector<std::pair<double, double>>& ranges) {
  std::vector<double> params;
  for (const auto& range : ranges) {
    double param = range.first + (range.second - range.first) * (static_cast<double>(rand()) / RAND_MAX);
    params.push_back(param);
  }
  return params;
}

std::vector<double> StrategyTester::run_strategy_simulation(
    std::unique_ptr<Strategy>& strategy,
    const std::vector<Bar>& data) {

  std::vector<double> portfolio_values;

  // Initialize strategy
  strategy->on_start();

  // Run through each bar
  for (const auto& bar : data) {
    // Update strategy with bar data
    strategy->on_bar(bar);

    // Get actual portfolio value from the strategy
    double current_portfolio_value = strategy->get_portfolio_value();
    portfolio_values.push_back(current_portfolio_value);
  }

  strategy->on_finish();

  double final_value = strategy->get_portfolio_value();
  if (portfolio_values.empty() || std::abs(portfolio_values.back() - final_value) > 1e-6) {
    portfolio_values.push_back(final_value);
  }

  return portfolio_values;
}

void StrategyTester::print_strategy_metrics(const StrategyMetrics& metrics) {
  std::cout << "\n" << std::string(60, '-') << std::endl;
  std::cout << "STRATEGY: " << metrics.strategy_name << std::endl;
  std::cout << "PARAMETERS: ";
  for (size_t i = 0; i < metrics.parameters.size(); ++i) {
    std::cout << metrics.parameters[i];
    if (i < metrics.parameters.size() - 1) std::cout << ", ";
  }
  std::cout << std::endl;

  std::cout << "PERFORMANCE:" << std::endl;
  std::cout << "  Total Return: " << std::fixed << std::setprecision(2) << (metrics.total_return * 100.0) << "%" << std::endl;
  std::cout << "  Sharpe Ratio: " << std::setprecision(3) << metrics.sharpe_ratio << std::endl;
  std::cout << "  Max Drawdown: " << std::setprecision(2) << (metrics.max_drawdown * 100.0) << "%" << std::endl;
  std::cout << "  Win Rate: " << std::setprecision(1) << (metrics.win_rate * 100.0) << "%" << std::endl;
  std::cout << "  Profit Factor: " << std::setprecision(2) << metrics.profit_factor << std::endl;
  std::cout << "  Total Trades: " << metrics.total_trades << std::endl;

  std::cout << "RISK METRICS:" << std::endl;
  std::cout << "  Calmar Ratio: " << std::setprecision(3) << metrics.calmar_ratio << std::endl;
  std::cout << "  Sortino Ratio: " << std::setprecision(3) << metrics.sortino_ratio << std::endl;
  std::cout << "  VaR 95%: " << std::setprecision(2) << (metrics.var_95 * 100.0) << "%" << std::endl;

  std::cout << "COMPOSITE SCORE: " << std::setprecision(4) << metrics.composite_score << std::endl;
  std::cout << std::string(60, '-') << std::endl;
}

void StrategyTester::print_strategy_comparison(const std::vector<StrategyMetrics>& metrics) {
  std::cout << "\n" << std::string(100, '=') << std::endl;
  std::cout << "TOP STRATEGIES COMPARISON" << std::endl;
  std::cout << std::string(100, '=') << std::endl;

  std::cout << std::left << std::setw(15) << "Rank"
            << std::setw(12) << "Strategy"
            << std::setw(10) << "Return%"
            << std::setw(10) << "Sharpe"
            << std::setw(10) << "MaxDD%"
            << std::setw(8) << "Win%"
            << std::setw(10) << "Trades"
            << std::setw(12) << "Score" << std::endl;
  std::cout << std::string(100, '-') << std::endl;

  for (size_t i = 0; i < metrics.size(); ++i) {
    const auto& m = metrics[i];
    std::cout << std::left << std::setw(15) << (i + 1)
              << std::setw(12) << m.strategy_name.substr(0, 11)
              << std::setw(10) << std::fixed << std::setprecision(1) << (m.total_return * 100.0)
              << std::setw(10) << std::setprecision(2) << m.sharpe_ratio
              << std::setw(10) << std::setprecision(1) << (m.max_drawdown * 100.0)
              << std::setw(8) << std::setprecision(0) << (m.win_rate * 100.0)
              << std::setw(10) << m.total_trades
              << std::setw(12) << std::setprecision(4) << m.composite_score << std::endl;
  }

  std::cout << std::string(100, '=') << std::endl;
}

// Data integrity validation methods
void StrategyTester::validate_chronological_order(const std::vector<Bar>& data) {
  if (data.size() < 2) {
    std::cout << "✓ Chronological Validation: Dataset too small for validation" << std::endl;
    return;
  }

  std::cout << "🔍 Validating chronological order of " << data.size() << " bars..." << std::endl;

  int violations = 0;
  std::vector<size_t> violation_indices;

  for (size_t i = 1; i < data.size(); ++i) {
    if (data[i].date <= data[i-1].date) {
      violations++;
      violation_indices.push_back(i);
    }
  }

  if (violations == 0) {
    std::cout << "✅ Chronological Order: All " << data.size() << " bars are in correct chronological order" << std::endl;
  } else {
    std::cout << "❌ Chronological Order: Found " << violations << " violations!" << std::endl;
    for (size_t idx : violation_indices) {
      std::cout << "   Violation at index " << idx << ": "
                << "Date " << data[idx].date
                << " <= Previous date " << data[idx-1].date << std::endl;
    }
    throw std::runtime_error("Data is NOT in chronological order! Lookahead bias possible.");
  }
}

void StrategyTester::validate_data_integrity(const std::vector<Bar>& data) {
  if (data.empty()) {
    throw std::runtime_error("Data integrity validation failed: No data provided");
  }

  std::cout << "🔍 Validating data integrity of " << data.size() << " bars..." << std::endl;

  int issues_found = 0;

  // Check for missing dates
  for (size_t i = 0; i < data.size(); ++i) {
    if (data[i].date == 0) {
      issues_found++;
      std::cout << "   Warning: Missing date at index " << i << std::endl;
    }
  }

  // Check for extreme price values
  for (size_t i = 0; i < data.size(); ++i) {
    const auto& bar = data[i];

    if (bar.open <= 0 || bar.high <= 0 || bar.low <= 0 || bar.close <= 0) {
      issues_found++;
      std::cout << "   Error: Non-positive price values at index " << i
                << " (O:" << bar.open << " H:" << bar.high
                << " L:" << bar.low << " C:" << bar.close << ")" << std::endl;
    }

    // Check for extremely large values (likely data errors)
    double max_reasonable_price = 1e8;  // 100M
    if (bar.open > max_reasonable_price || bar.high > max_reasonable_price ||
        bar.low > max_reasonable_price || bar.close > max_reasonable_price) {
      issues_found++;
      std::cout << "   Warning: Extremely large price values at index " << i << std::endl;
    }
  }

  // Check for gaps (consecutive date issues)
  int gap_count = 0;
  for (size_t i = 1; i < data.size(); ++i) {
    // Assuming daily data for gap detection
    int expected_next_date = data[i-1].date + 1;

    // Handle month transitions (simplified - doesn't handle all edge cases)
    int prev_day = data[i-1].date % 100;
    int prev_month = (data[i-1].date / 100) % 100;
    int prev_year = data[i-1].date / 10000;

    // Very basic gap detection
    if (data[i].date - data[i-1].date > 5) {  // More than 5 days gap
      gap_count++;
      if (gap_count <= 3) {  // Only show first few gaps
        std::cout << "   Warning: Large date gap at index " << i
                  << " (" << data[i-1].date << " -> " << data[i].date << ")" << std::endl;
      }
    }
  }

  if (issues_found == 0 && gap_count == 0) {
    std::cout << "✅ Data Integrity: All " << data.size() << " bars passed integrity checks" << std::endl;
  } else {
    if (issues_found > 0) {
      std::cout << "⚠️ Data Integrity: " << issues_found << " data issues found" << std::endl;
    }
    if (gap_count > 0) {
      std::cout << "⚠️ Data Integrity: " << gap_count << " date gaps detected" << std::endl;
    }
  }
}

void StrategyTester::validate_ohlc_relationships(const std::vector<Bar>& data) {
  std::cout << "🔍 Validating OHLC relationships in " << data.size() << " bars..." << std::endl;

  int violations = 0;

  for (size_t i = 0; i < data.size(); ++i) {
    const auto& bar = data[i];

    // High should be >= Open, High, Low, Close
    if (bar.high < bar.open || bar.high < bar.low || bar.high < bar.close) {
      violations++;
      std::cout << "   Error: High price violations at index " << i << std::endl;
    }

    // Low should be <= Open, High, Low, Close
    if (bar.low > bar.open || bar.low > bar.high || bar.low > bar.close) {
      violations++;
      std::cout << "   Error: Low price violations at index " << i << std::endl;
    }

    // Check for extreme intraday volatility (price changes > 50%)
    double max_change = std::max({
      std::abs(bar.open - bar.close) / bar.open,
      (bar.high - bar.low) / bar.low
    });

    if (max_change > 0.8) {  // 80% intraday change
      violations++;
      std::cout << "   Warning: Extreme intraday volatility at index " << i
                << " (" << (max_change * 100) << "% change)" << std::endl;
    }
  }

  if (violations == 0) {
    std::cout << "✅ OHLC Relationships: All " << data.size() << " bars have valid OHLC relationships" << std::endl;
  } else {
    std::cout << "❌ OHLC Relationships: " << violations << " relationship violations found!" << std::endl;
  }
}

// StrategyGeneration namespace implementations
namespace StrategyGeneration {

std::vector<StrategyTestConfig> generate_sma_configs(
    int num_configs,
    int short_min, int short_max,
    int long_min, int long_max) {

  std::vector<StrategyTestConfig> configs;

  for (int i = 0; i < num_configs; ++i) {
    StrategyTestConfig config;
    config.strategy_name = "SMA";

    // Generate random parameters
    int short_win = short_min + (rand() % (short_max - short_min + 1));
    int long_win = long_min + (rand() % (long_max - long_min + 1));
    double fee = 0.0001 + (rand() % 100) * 0.00001;  // 0.01% to 0.1% fees

    // Ensure short < long
    if (short_win >= long_win) {
      std::swap(short_win, long_win);
    }

    config.parameters = {static_cast<double>(short_win), static_cast<double>(long_win), fee};
    configs.push_back(config);
  }

  return configs;
}

std::vector<StrategyTestConfig> generate_rsi_configs(
    int num_configs,
    int period_min, int period_max,
    double overbought_min, double overbought_max,
    double oversold_min, double oversold_max,
    int confirm_min, int confirm_max) {

  std::vector<StrategyTestConfig> configs;

  for (int i = 0; i < num_configs; ++i) {
    StrategyTestConfig config;
    config.strategy_name = "RSI";

    int period = period_min + (rand() % std::max(1, period_max - period_min + 1));
    double overbought = overbought_min + (static_cast<double>(rand()) / RAND_MAX) * (overbought_max - overbought_min);
    double oversold = oversold_min + (static_cast<double>(rand()) / RAND_MAX) * (oversold_max - oversold_min);
    if (overbought <= oversold) {
      overbought = oversold + 5.0;
    }
    int confirm = confirm_min + (rand() % std::max(1, confirm_max - confirm_min + 1));
    double fee = 0.0001 + (rand() % 100) * 0.00001;

    config.parameters = {
      static_cast<double>(period),
      overbought,
      oversold,
      static_cast<double>(confirm),
      fee
    };

    configs.push_back(config);
  }

  return configs;
}

std::vector<StrategyTestConfig> generate_macd_configs(
    int num_configs,
    int fast_min, int fast_max,
    int slow_min, int slow_max,
    int signal_min, int signal_max,
    double overbought_min, double overbought_max,
    double oversold_min, double oversold_max) {

  std::vector<StrategyTestConfig> configs;

  for (int i = 0; i < num_configs; ++i) {
    StrategyTestConfig config;
    config.strategy_name = "MACD";

    int fast = fast_min + (rand() % std::max(1, fast_max - fast_min + 1));
    int slow = slow_min + (rand() % std::max(1, slow_max - slow_min + 1));
    if (slow <= fast) {
      slow = fast + 4;
    }
    int signal = signal_min + (rand() % std::max(1, signal_max - signal_min + 1));
    double overbought = overbought_min + (static_cast<double>(rand()) / RAND_MAX) * (overbought_max - overbought_min);
    double oversold = oversold_min + (static_cast<double>(rand()) / RAND_MAX) * (oversold_max - oversold_min);
    double fee = 0.0001 + (rand() % 100) * 0.00001;

    config.parameters = {
      static_cast<double>(fast),
      static_cast<double>(slow),
      static_cast<double>(signal),
      overbought,
      oversold,
      fee
    };

    configs.push_back(config);
  }

  return configs;
}

std::vector<StrategyTestConfig> generate_comprehensive_test_suite() {
  std::vector<StrategyTestConfig> configs;

  // SMA strategies with various parameters
  auto sma_configs = generate_sma_configs(50, 5, 50, 20, 200);
  configs.insert(configs.end(), sma_configs.begin(), sma_configs.end());

  auto rsi_configs = generate_rsi_configs(30, 7, 25, 65.0, 85.0, 15.0, 35.0, 1, 4);
  configs.insert(configs.end(), rsi_configs.begin(), rsi_configs.end());

  auto macd_configs = generate_macd_configs(30, 8, 15, 20, 35, 5, 12, 0.5, 1.5, -1.5, -0.5);
  configs.insert(configs.end(), macd_configs.begin(), macd_configs.end());

  return configs;
}

StrategyMetrics quick_test_strategy(const std::string& strategy_type,
                                  const std::vector<double>& params,
                                  const std::vector<Bar>& data) {

  StrategyTestConfig config;
  config.strategy_name = strategy_type;
  config.parameters = params;

  StrategyTester tester;
  return tester.test_strategy(config, data);
}

}
