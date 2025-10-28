#include "strategy_factory.h"

#include "strategy.h"
#include <memory>
#include <string>
#include <vector>

// Factory functions implemented in individual strategy translation units
std::unique_ptr<Strategy> make_sma_strategy(int short_window, int long_window, double fee, const std::string& symbol);
std::unique_ptr<Strategy> make_macd_strategy(int fast_period, int slow_period, int signal_period,
                                             double overbought, double oversold, double fee, const std::string& symbol);
std::unique_ptr<Strategy> make_rsi_strategy(int rsi_period, double overbought, double oversold,
                                           int confirmation, double fee, const std::string& symbol);

std::unique_ptr<Strategy> StrategyFactory::create_sma_strategy(
    int short_window, int long_window, double fee, const std::string& symbol) {
  return make_sma_strategy(short_window, long_window, fee, symbol);
}

std::unique_ptr<Strategy> StrategyFactory::create_strategy(
    const std::string& strategy_name,
    const std::vector<double>& parameters,
    const std::string& symbol) {

  if (strategy_name == "SMA" && parameters.size() >= 3) {
    int short_win = static_cast<int>(parameters[0]);
    int long_win = static_cast<int>(parameters[1]);
    double fee = parameters[2];
    return create_sma_strategy(short_win, long_win, fee, symbol);
  }

  if (strategy_name == "RSI" && parameters.size() >= 5) {
    int rsi_period = static_cast<int>(parameters[0]);
    double overbought = parameters[1];
    double oversold = parameters[2];
    int confirmation = static_cast<int>(parameters[3]);
    double fee = parameters[4];
    return make_rsi_strategy(rsi_period, overbought, oversold, confirmation, fee, symbol);
  }

  if (strategy_name == "MACD" && parameters.size() >= 6) {
    int fast_period = static_cast<int>(parameters[0]);
    int slow_period = static_cast<int>(parameters[1]);
    int signal_period = static_cast<int>(parameters[2]);
    double overbought = parameters[3];
    double oversold = parameters[4];
    double fee = parameters[5];
    return make_macd_strategy(fast_period, slow_period, signal_period, overbought, oversold, fee, symbol);
  }

  return nullptr;
}

std::vector<std::string> StrategyFactory::get_available_strategies() {
  return {"SMA", "RSI", "MACD"};
}

std::vector<std::string> StrategyFactory::get_parameter_names(const std::string& strategy_name) {
  if (strategy_name == "SMA") {
    return {"short_window", "long_window", "fee"};
  }
  if (strategy_name == "RSI") {
    return {"rsi_period", "overbought_level", "oversold_level", "confirmation_period", "fee"};
  }
  if (strategy_name == "MACD") {
    return {"fast_period", "slow_period", "signal_period", "overbought_level", "oversold_level", "fee"};
  }
  return {};
}
