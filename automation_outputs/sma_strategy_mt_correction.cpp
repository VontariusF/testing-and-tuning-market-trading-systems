// Multiple-testing correction guideline applied
// Out-of-sample dataset: /Users/vontariusfalls/testing-and-tuning-market-trading-systems/automation_outputs/oos_sample_ohlc.txt
// Automated walk-forward adjustments applied
// Parameter bounds tightened for robustness
// Multiple-testing correction guideline applied
// Out-of-sample dataset: /Users/vontariusfalls/testing-and-tuning-market-trading-systems/automation_outputs/oos_sample_ohlc.txt
// Automated walk-forward adjustments applied
#include "strategy.h"
#include <vector>
#include <cstdio>
#include <cmath>
#include <string>
#include <algorithm>
#include <numeric>
#include <iostream>

// Enhanced SMA Crossover Strategy with Risk Management
class SmaCrossStrategy : public Strategy {
public:
  SmaCrossStrategy(int short_win, int long_win, double fee, std::string symbol)
      : sw_(short_win), lw_(long_win), fee_(fee), symbol_(std::move(symbol)) {
    if (sw_ < 1) sw_ = 1;
    if (lw_ < sw_) lw_ = sw_;

    // Configure advanced risk management
    risk_config_.max_portfolio_risk = 0.02;      // 2% max risk per trade
    risk_config_.stop_loss_pct = 0.02;           // 2% stop loss
    risk_config_.take_profit_pct = 0.06;         // 6% take profit (3:1 reward/risk)
    risk_config_.max_drawdown = 0.10;            // 10% max drawdown
    risk_config_.enable_volatility_sizing = true; // Enable volatility sizing
    risk_config_.enable_atr_stops = true;        // Enable ATR-based stops
    risk_config_.atr_period = 14;                // ATR calculation period
    risk_config_.atr_multiplier = 2.0;           // ATR multiplier for stops
    risk_config_.enable_drawdown_breaker = true; // Enable circuit breaker
    risk_config_.drawdown_breaker_pct = 0.05;    // 5% circuit breaker
    risk_config_.recovery_mode_risk = 0.005;     // 0.5% risk in recovery
  }

  std::string get_name() const override {
    return "SMA Crossover Strategy";
  }

  std::string get_description() const override {
    return "Simple Moving Average Crossover with Risk Management";
  }

  std::vector<std::string> get_required_symbols() const override {
    return {symbol_};
  }

  RiskConfig get_risk_config() const override {
    return risk_config_;
  }

  void on_start() override {
    closes_.clear();
    current_position_ = {};
    current_position_.symbol = symbol_;

    portfolio_value_ = 100000.0;  // Start with $100k
    cash_ = portfolio_value_;
    fees_paid_ = 0.0;
    peak_portfolio_value_ = portfolio_value_;
    max_drawdown_ = 0.0;
    previous_value_ = portfolio_value_;
    last_price_ = 0.0;
    last_date_ = 0;

    trades_.clear();
    daily_returns_.clear();

    short_sma_ = 0.0;
    long_sma_ = 0.0;
    position_ = 0;  // -1, 0, +1

    stop_loss_price_ = 0.0;
    take_profit_price_ = 0.0;
    trailing_stop_price_ = 0.0;
  }

  void on_bar(const Bar& b) override {
    double current_price = b.close;
    closes_.push_back(current_price);

    // Need enough data for both SMAs
    if (closes_.size() < static_cast<size_t>(lw_)) {
      update_position_value(current_price);
      return;
    }

    // Calculate SMAs efficiently
    calculate_smas();

    // Generate trading signal
    int signal = generate_signal();

    // Execute trading logic with risk management
    execute_trading_logic(b, signal);

    last_price_ = current_price;
    last_date_ = b.date;

    // Update performance metrics
    update_performance_metrics();
  }

  void on_finish() override {
    // Close any open positions at the most recent price
    if (current_position_.quantity != 0.0) {
      double exit_price = (last_price_ > 0.0) ? last_price_ : current_position_.avg_entry_price;
      int exit_date = (last_date_ != 0) ? last_date_ : 0;
      close_position(exit_date, exit_price);
    }

    portfolio_value_ = cash_;

    // Calculate final metrics
    calculate_final_metrics();

    // Print comprehensive results
    print_results();
  }

  double calculate_position_size(const Bar& bar, double portfolio_value) override {
    // Enhanced position sizing with volatility adjustment
    double base_position_size = calculate_base_position_size(portfolio_value);

    if (!risk_config_.enable_volatility_sizing) {
      return base_position_size;
    }

    // Calculate volatility adjustment
    double volatility_adjustment = calculate_volatility_adjustment();

    // Apply volatility scaling (lower volatility = larger position, higher volatility = smaller position)
    double adjusted_size = base_position_size * volatility_adjustment;

    // Ensure minimum and maximum bounds
    double min_size = portfolio_value * 0.001;  // 0.1% minimum
    double max_size = portfolio_value * risk_config_.max_portfolio_risk;  // Max risk limit

    return std::max(min_size, std::min(max_size, adjusted_size));
  }

  double calculate_base_position_size(double portfolio_value) {
    // Use Kelly Criterion for base position sizing
    double win_rate = calculate_win_rate();
    double avg_win = calculate_avg_win();
    double avg_loss = calculate_avg_loss();

    if (win_rate <= 0.0 || avg_win <= 0.0 || avg_loss >= 0.0) {
      return portfolio_value * risk_config_.max_portfolio_risk;
    }

    // Kelly percentage
    double kelly_pct = win_rate - ((1.0 - win_rate) * avg_loss / avg_win);

    // Cap at max portfolio risk
    kelly_pct = std::min(kelly_pct, risk_config_.max_portfolio_risk);
    kelly_pct = std::max(kelly_pct, 0.001);  // Minimum 0.1% position

    return portfolio_value * kelly_pct;
  }

  double calculate_volatility_adjustment() {
    if (closes_.size() < 20) return 1.0;  // Not enough data

    // Calculate historical volatility (standard deviation of returns)
    std::vector<double> returns;
    for (size_t i = 1; i < closes_.size(); ++i) {
      double ret = (closes_[i] - closes_[i-1]) / closes_[i-1];
      returns.push_back(ret);
    }

    if (returns.size() < 2) return 1.0;

    // Calculate mean return
    double mean_return = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();

    // Calculate variance
    double variance = 0.0;
    for (double ret : returns) {
      variance += (ret - mean_return) * (ret - mean_return);
    }
    variance /= (returns.size() - 1);

    double volatility = std::sqrt(variance);

    // Target volatility of 2% (adjust based on your risk tolerance)
    double target_volatility = 0.02;
    double current_volatility = std::max(volatility, 0.001);  // Avoid division by zero

    // Volatility adjustment: lower volatility allows larger positions
    double adjustment = target_volatility / current_volatility;

    // Cap adjustment between 0.5x and 2x
    return std::max(0.5, std::min(2.0, adjustment));
  }

  double calculate_atr_stop_loss(const Bar& bar, double entry_price) {
    if (!risk_config_.enable_atr_stops || closes_.size() < static_cast<size_t>(risk_config_.atr_period)) {
      return entry_price * (1.0 - risk_config_.stop_loss_pct);
    }

    double atr = calculate_atr(risk_config_.atr_period);
    return entry_price - (atr * risk_config_.atr_multiplier);
  }

  double calculate_atr_take_profit(const Bar& bar, double entry_price) {
    if (!risk_config_.enable_atr_stops || closes_.size() < static_cast<size_t>(risk_config_.atr_period)) {
      return entry_price * (1.0 + risk_config_.take_profit_pct);
    }

    double atr = calculate_atr(risk_config_.atr_period);
    // Use 3:1 reward/risk ratio with ATR
    double risk_amount = atr * risk_config_.atr_multiplier;
    double reward_amount = risk_amount * 3.0;
    return entry_price + reward_amount;
  }

  double calculate_atr(int period) {
    if (closes_.size() < static_cast<size_t>(period + 1)) return 0.0;

    std::vector<double> true_ranges;
    for (size_t i = 1; i < closes_.size(); ++i) {
      double high = 0.0, low = 0.0;  // Simplified - using close prices for now
      double tr = std::abs(closes_[i] - closes_[i-1]);
      true_ranges.push_back(tr);
    }

    if (true_ranges.size() < static_cast<size_t>(period)) return 0.0;

    // Calculate ATR as SMA of true ranges
    double atr_sum = 0.0;
    int start_idx = true_ranges.size() - period;
    for (int i = start_idx; i < static_cast<int>(true_ranges.size()); ++i) {
      atr_sum += true_ranges[i];
    }

    return atr_sum / period;
  }

  bool check_drawdown_breaker() {
    if (!risk_config_.enable_drawdown_breaker) return false;

    double current_drawdown = (peak_portfolio_value_ - portfolio_value_) / peak_portfolio_value_;
    return current_drawdown >= risk_config_.drawdown_breaker_pct;
  }

  bool is_in_recovery_mode() {
    double current_drawdown = (peak_portfolio_value_ - portfolio_value_) / peak_portfolio_value_;
    return current_drawdown >= (risk_config_.max_drawdown * 0.8);  // 80% of max drawdown
  }

  double get_adjusted_risk_per_trade() {
    if (is_in_recovery_mode()) {
      return risk_config_.recovery_mode_risk;  // Reduced risk in recovery
    }
    return risk_config_.max_portfolio_risk;
  }

  bool should_enter_position(const Bar& bar) override {
    if (closes_.size() < static_cast<size_t>(lw_)) return false;

    calculate_smas();
    return generate_signal() != 0;
  }

  bool should_exit_position(const Bar& bar, const Position& position) override {
    double current_price = bar.close;

    if (position.quantity > 0) {
      if (stop_loss_price_ > 0.0 && current_price <= stop_loss_price_) {
        return true;
      }
      if (take_profit_price_ > 0.0 && current_price >= take_profit_price_) {
        return true;
      }
      if (risk_config_.enable_trailing_stop && trailing_stop_price_ > 0.0) {
        if (current_price <= trailing_stop_price_) {
          return true;
        }
        update_trailing_stop(current_price);
      }
    } else if (position.quantity < 0) {
      if (stop_loss_price_ > 0.0 && current_price >= stop_loss_price_) {
        return true;
      }
      if (take_profit_price_ > 0.0 && current_price <= take_profit_price_) {
        return true;
      }
      if (risk_config_.enable_trailing_stop && trailing_stop_price_ > 0.0) {
        if (current_price >= trailing_stop_price_) {
          return true;
        }
        update_trailing_stop(current_price);
      }
    }

    return false;
  }

  double calculate_stop_loss(const Bar& bar, double entry_price) override {
    return entry_price * (1.0 - risk_config_.stop_loss_pct);
  }

  double calculate_take_profit(const Bar& bar, double entry_price) override {
    return entry_price * (1.0 + risk_config_.take_profit_pct);
  }

  double get_sharpe_ratio() const override {
    if (daily_returns_.size() < 2) return 0.0;

    double mean_return = std::accumulate(daily_returns_.begin(), daily_returns_.end(), 0.0) / daily_returns_.size();

    double variance = 0.0;
    for (double ret : daily_returns_) {
      variance += (ret - mean_return) * (ret - mean_return);
    }
    variance /= (daily_returns_.size() - 1);

    double std_dev = std::sqrt(variance);
    if (std_dev == 0.0) return 0.0;

    // Assume risk-free rate of 2%
    double risk_free_rate = 0.02;
    double annualized_return = mean_return * 252;  // Assuming daily returns

    return (annualized_return - risk_free_rate) / (std_dev * std::sqrt(252));
  }

  double get_max_drawdown() const override {
    return max_drawdown_;
  }

  double get_total_return() const override {
    if (portfolio_value_ <= 0.0) return -1.0;
    return (portfolio_value_ - 100000.0) / 100000.0;
  }

  int get_trade_count() const override {
    int exit_trades = 0;
    for (const auto& trade : trades_) {
      if (trade.type == Trade::Type::EXIT) {
        ++exit_trades;
      }
    }
    return exit_trades;
  }

  std::vector<Trade> get_trades() const override {
    return trades_;
  }

  std::vector<Position> get_positions() const override {
    std::vector<Position> positions;
    if (current_position_.quantity != 0.0) {
      positions.push_back(current_position_);
    }
    return positions;
  }

private:
  void calculate_smas() {
    size_t size = closes_.size();

    // Calculate short SMA
    if (size >= static_cast<size_t>(sw_)) {
      double sum = 0.0;
      for (int i = 0; i < sw_; ++i) {
        sum += closes_[size - 1 - i];
      }
      short_sma_ = sum / sw_;
    }

    // Calculate long SMA
    if (size >= static_cast<size_t>(lw_)) {
      double sum = 0.0;
      for (int i = 0; i < lw_; ++i) {
        sum += closes_[size - 1 - i];
      }
      long_sma_ = sum / lw_;
    }
  }

  int generate_signal() {
    if (short_sma_ == 0.0 || long_sma_ == 0.0) return 0;

    if (short_sma_ > long_sma_) return 1;   // Long signal
    if (short_sma_ < long_sma_) return -1;  // Short signal
    return 0;  // No signal
  }

  void execute_trading_logic(const Bar& bar, int signal) {
    double current_price = bar.close;

    // Check if we should exit current position
    if (current_position_.quantity != 0.0 && should_exit_position(bar, current_position_)) {
      close_position(bar.date, current_price);
      return;
    }

    // Check if signal changed
    if (signal != position_) {
      // Close existing position if any
      if (current_position_.quantity != 0.0) {
        close_position(bar.date, current_price);
      }

      // Open new position if signal is not neutral
      if (signal != 0) {
        open_position(bar.date, current_price, signal);
      }

      position_ = signal;
    }

    // Update position value
    update_position_value(current_price);
  }

  void open_position(int date, double price, int direction) {
    if (price <= 0.0) return;

    double position_size = calculate_position_size({}, portfolio_value_);
    if (position_size <= 0.0) return;

    double quantity = position_size / price;
    double notional = quantity * price;

    // Create trade record
    Trade entry_trade;
    entry_trade.date = date;
    entry_trade.side = (direction > 0) ? Trade::Side::BUY : Trade::Side::SELL;
    entry_trade.type = Trade::Type::ENTRY;
    entry_trade.price = price;
    entry_trade.quantity = quantity;
    entry_trade.symbol = symbol_;

    trades_.push_back(entry_trade);

    // Update position bookkeeping
    current_position_.symbol = symbol_;
    current_position_.avg_entry_price = price;
    current_position_.current_price = price;
    current_position_.unrealized_pnl = 0.0;
    current_position_.quantity = (direction > 0) ? quantity : -quantity;

    double fee_amount = fee_ * notional;
    if (direction > 0) {
      cash_ -= notional + fee_amount;
      stop_loss_price_ = calculate_stop_loss({}, price);
      take_profit_price_ = calculate_take_profit({}, price);
      trailing_stop_price_ = price * (1.0 - risk_config_.trailing_stop_pct);
    } else {
      cash_ += notional - fee_amount;
      stop_loss_price_ = price * (1.0 + risk_config_.stop_loss_pct);
      take_profit_price_ = price * (1.0 - risk_config_.take_profit_pct);
      trailing_stop_price_ = price * (1.0 + risk_config_.trailing_stop_pct);
    }

    fees_paid_ += fee_amount;
    update_position_value(price);
  }

  void close_position(int date, double price) {
    if (current_position_.quantity == 0.0 || price <= 0.0) {
      portfolio_value_ = cash_;
      return;
    }

    double quantity = current_position_.quantity;
    double abs_quantity = std::abs(quantity);
    double entry_value = abs_quantity * current_position_.avg_entry_price;
    double exit_value = abs_quantity * price;

    double pnl = quantity * (price - current_position_.avg_entry_price);
    double total_fees = fee_ * (entry_value + exit_value);
    double net_pnl = pnl - total_fees;

    double exit_fee = fee_ * exit_value;
    if (quantity > 0) {
      cash_ += exit_value - exit_fee;
    } else {
      cash_ -= exit_value + exit_fee;
    }

    fees_paid_ += exit_fee;

    // Create exit trade record
    Trade exit_trade;
    exit_trade.date = date;
    exit_trade.side = (quantity > 0) ? Trade::Side::SELL : Trade::Side::BUY;
    exit_trade.type = Trade::Type::EXIT;
    exit_trade.price = price;
    exit_trade.quantity = abs_quantity;
    exit_trade.pnl = net_pnl;
    exit_trade.symbol = symbol_;

    trades_.push_back(exit_trade);

    current_position_.quantity = 0.0;
    current_position_.avg_entry_price = 0.0;
    current_position_.current_price = 0.0;
    current_position_.unrealized_pnl = 0.0;

    stop_loss_price_ = 0.0;
    take_profit_price_ = 0.0;
    trailing_stop_price_ = 0.0;

    portfolio_value_ = cash_;
  }

  double calculate_pnl(double current_price) const {
    if (current_position_.quantity == 0.0) return 0.0;
    return current_position_.quantity * (current_price - current_position_.avg_entry_price);
  }

  void update_position_value(double current_price) {
    if (current_position_.quantity == 0.0) {
      portfolio_value_ = cash_;
      return;
    }

    current_position_.current_price = current_price;
    current_position_.unrealized_pnl = calculate_pnl(current_price);

    portfolio_value_ = cash_ + current_position_.quantity * current_price;
  }

  void update_trailing_stop(double current_price) {
    if (current_position_.quantity > 0) {
      double new_trailing_stop = current_price * (1.0 - risk_config_.trailing_stop_pct);
      if (new_trailing_stop > trailing_stop_price_) {
        trailing_stop_price_ = new_trailing_stop;
      }
    } else if (current_position_.quantity < 0) {
      double new_trailing_stop = current_price * (1.0 + risk_config_.trailing_stop_pct);
      if (trailing_stop_price_ == 0.0 || new_trailing_stop < trailing_stop_price_) {
        trailing_stop_price_ = new_trailing_stop;
      }
    }
  }

  void update_performance_metrics() override {
    if (portfolio_value_ > peak_portfolio_value_) {
      peak_portfolio_value_ = portfolio_value_;
    }

    if (peak_portfolio_value_ > 0.0) {
      double current_drawdown = (peak_portfolio_value_ - portfolio_value_) / peak_portfolio_value_;
      if (current_drawdown > max_drawdown_) {
        max_drawdown_ = current_drawdown;
      }
    }

    if (previous_value_ > 0.0) {
      double daily_return = (portfolio_value_ - previous_value_) / previous_value_;
      daily_returns_.push_back(daily_return);
    }
    previous_value_ = portfolio_value_;
  }

  void calculate_final_metrics() {
    // Calculate final performance metrics
    final_sharpe_ratio_ = get_sharpe_ratio();
    final_max_drawdown_ = get_max_drawdown();
    final_total_return_ = get_total_return();
  }

  double calculate_win_rate() const {
    int completed_trades = 0;
    int winning_trades = 0;

    for (const auto& trade : trades_) {
      if (trade.type != Trade::Type::EXIT) continue;
      ++completed_trades;
      if (trade.pnl > 0.0) {
        ++winning_trades;
      }
    }

    if (completed_trades == 0) return 0.0;
    return static_cast<double>(winning_trades) / completed_trades;
  }

  double calculate_avg_win() const {
    double total_wins = 0.0;
    int win_count = 0;

    for (const auto& trade : trades_) {
      if (trade.type != Trade::Type::EXIT) continue;
      if (trade.pnl > 0.0) {
        total_wins += trade.pnl;
        ++win_count;
      }
    }

    return win_count > 0 ? total_wins / win_count : 0.0;
  }

  double calculate_avg_loss() const {
    double total_losses = 0.0;
    int loss_count = 0;

    for (const auto& trade : trades_) {
      if (trade.type != Trade::Type::EXIT) continue;
      if (trade.pnl < 0.0) {
        total_losses += trade.pnl;
        ++loss_count;
      }
    }

    return loss_count > 0 ? total_losses / loss_count : 0.0;
  }

  void print_results() {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "SMA CROSSOVER STRATEGY RESULTS" << std::endl;
    std::cout << std::string(60, '=') << std::endl;
    std::cout << "Symbol: " << symbol_ << std::endl;
    std::cout << "Parameters: Short=" << sw_ << ", Long=" << lw_ << ", Fee=" << fee_ << std::endl;
    std::cout << "\nPERFORMANCE METRICS:" << std::endl;
    std::cout << "  Total Return: " << (final_total_return_ * 100.0) << "%" << std::endl;
    std::cout << "  Sharpe Ratio: " << final_sharpe_ratio_ << std::endl;
    std::cout << "  Max Drawdown: " << (final_max_drawdown_ * 100.0) << "%" << std::endl;
    std::cout << "  Total Trades: " << get_trade_count() << std::endl;

    if (get_trade_count() > 0) {
      std::cout << "  Win Rate: " << (calculate_win_rate() * 100.0) << "%" << std::endl;
      std::cout << "  Avg Win: $" << calculate_avg_win() << std::endl;
      std::cout << "  Avg Loss: $" << calculate_avg_loss() << std::endl;

      std::cout << "  Total Fees: $" << fees_paid_ << std::endl;
    }

    std::cout << "\nRISK METRICS:" << std::endl;
    std::cout << "  Portfolio Value: $" << portfolio_value_ << std::endl;
    std::cout << "  Risk per Trade: " << (risk_config_.max_portfolio_risk * 100.0) << "%" << std::endl;
    std::cout << "  Stop Loss: " << (risk_config_.stop_loss_pct * 100.0) << "%" << std::endl;
    std::cout << "  Take Profit: " << (risk_config_.take_profit_pct * 100.0) << "%" << std::endl;

    std::cout << std::string(60, '=') << std::endl;
  }

  // Strategy parameters
  int sw_, lw_;
  double fee_;
  std::string symbol_;

  // Price data
  std::vector<double> closes_;
  double short_sma_ = 0.0;
  double long_sma_ = 0.0;

  // Position management
  int position_ = 0;  // -1, 0, +1
  Position current_position_;
  double cash_ = 0.0;
  double fees_paid_ = 0.0;
  double last_price_ = 0.0;
  int last_date_ = 0;
  double previous_value_ = 0.0;

  // Risk management
  double stop_loss_price_ = 0.0;
  double take_profit_price_ = 0.0;
  double trailing_stop_price_ = 0.0;

  // Performance tracking
  double peak_portfolio_value_ = 0.0;
  double max_drawdown_ = 0.0;
  std::vector<double> daily_returns_;

  // Final metrics
  double final_sharpe_ratio_ = 0.0;
  double final_max_drawdown_ = 0.0;
  double final_total_return_ = 0.0;
};

// Factory function
std::unique_ptr<Strategy> make_sma_strategy(int sw, int lw, double fee, const std::string& symbol) {
  return std::make_unique<SmaCrossStrategy>(sw, lw, fee, symbol);
}
