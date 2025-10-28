#pragma once

#include <cstddef>
#include <string>
#include <vector>
#include <memory>

// Enhanced Bar structure with volume support
struct Bar {
  int date = 0;         // YYYYMMDD (optional; 0 if missing)
  double open = 0.0;
  double high = 0.0;
  double low = 0.0;
  double close = 0.0;
  double volume = 0.0;  // Added volume support for C++17 compatibility
};

// Trade structure for better trade tracking
struct Trade {
  enum class Side { BUY, SELL };
  enum class Type { ENTRY, EXIT };

  int date = 0;
  Side side = Side::BUY;
  Type type = Type::ENTRY;
  double price = 0.0;
  double quantity = 0.0;
  double pnl = 0.0;
  std::string symbol;
};

// Position information for risk management
struct Position {
  std::string symbol;
  double quantity = 0.0;
  double avg_entry_price = 0.0;
  double current_price = 0.0;
  double unrealized_pnl = 0.0;
  double realized_pnl = 0.0;
};

// Risk management configuration
struct RiskConfig {
  double max_position_size = 10000.0;    // Maximum position size
  double max_portfolio_risk = 0.02;      // Max 2% portfolio risk per trade
  double max_drawdown = 0.10;            // Max 10% drawdown
  double stop_loss_pct = 0.02;           // 2% stop loss
  double take_profit_pct = 0.06;         // 6% take profit (3:1 reward/risk)
  bool enable_trailing_stop = true;      // Enable trailing stops
  double trailing_stop_pct = 0.01;       // 1% trailing stop

  // Advanced risk management
  bool enable_volatility_sizing = true;  // Use volatility-adjusted sizing
  bool enable_atr_stops = true;          // Use ATR-based stops
  double atr_period = 14;                // ATR calculation period
  double atr_multiplier = 2.0;           // ATR multiplier for stops
  double max_correlation = 0.7;          // Max correlation between positions
  bool enable_drawdown_breaker = true;   // Enable drawdown circuit breaker
  double drawdown_breaker_pct = 0.05;    // 5% drawdown circuit breaker
  double recovery_mode_risk = 0.005;     // 0.5% risk in recovery mode
};

// Enhanced Strategy interface with risk management
class Strategy {
public:
  virtual ~Strategy() = default;

  // Lifecycle methods
  virtual void on_start() {}
  virtual void on_bar(const Bar& b) = 0;
  virtual void on_finish() {}

  // Enhanced methods for better strategy management
  virtual std::string get_name() const { return "Unknown Strategy"; }
  virtual std::string get_description() const { return "No description available"; }
  virtual std::vector<std::string> get_required_symbols() const { return {}; }
  virtual RiskConfig get_risk_config() const { return {}; }

  // Position and risk management
  virtual double calculate_position_size(const Bar& bar, double portfolio_value) { return 0.0; }
  virtual bool should_enter_position(const Bar& bar) { return false; }
  virtual bool should_exit_position(const Bar& bar, const Position& position) { return false; }
  virtual double calculate_stop_loss(const Bar& bar, double entry_price) { return 0.0; }
  virtual double calculate_take_profit(const Bar& bar, double entry_price) { return 0.0; }

  // Performance tracking
  virtual void update_performance_metrics() {}
  virtual double get_portfolio_value() const { return portfolio_value_; }
  virtual double get_sharpe_ratio() const { return 0.0; }
  virtual double get_max_drawdown() const { return 0.0; }
  virtual double get_total_return() const { return 0.0; }
  virtual int get_trade_count() const { return 0; }

  // Trade management
  virtual std::vector<Trade> get_trades() const { return {}; }
  virtual std::vector<Position> get_positions() const { return {}; }

protected:
  std::vector<Trade> trades_;
  std::vector<Position> positions_;
  double portfolio_value_ = 100000.0;  // Default $100k portfolio
  RiskConfig risk_config_;
};
