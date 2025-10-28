#pragma once

#include "strategy.h"
#include <memory>
#include <string>
#include <vector>

// Strategy factory for creating strategies by name
class StrategyFactory {
public:
  // Create SMA strategy with parameters: short_window, long_window, fee
  static std::unique_ptr<Strategy> create_sma_strategy(
      int short_window, int long_window, double fee, const std::string& symbol = "DEMO");

  // Create strategy by name and parameters
  static std::unique_ptr<Strategy> create_strategy(
      const std::string& strategy_name,
      const std::vector<double>& parameters,
      const std::string& symbol = "DEMO");

  // Get available strategy types
  static std::vector<std::string> get_available_strategies();

  // Get parameter requirements for a strategy
  static std::vector<std::string> get_parameter_names(const std::string& strategy_name);
};
