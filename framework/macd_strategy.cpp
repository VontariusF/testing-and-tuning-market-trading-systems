#include "strategy.h"
#include <vector>
#include <iostream>
#include <string>
#include <algorithm>
#include <numeric>
#include <cmath>

// MACD Momentum Strategy Implementation
class MacdMomentumStrategy : public Strategy {
public:
  MacdMomentumStrategy(int fast_period, int slow_period, int signal_period,
                       double overbought_level, double oversold_level, double fee, std::string symbol)
      : fast_period_(fast_period), slow_period_(slow_period), signal_period_(signal_period),
        overbought_level_(overbought_level), oversold_level_(oversold_level),
        fee_(fee), symbol_(std::move(symbol)) {

    // Configure risk management for momentum strategy
    risk_config_.max_portfolio_risk = 0.025;  // 2.5% max risk per trade (momentum can be more volatile)
    risk_config_.stop_loss_pct = 0.04;        // 4% stop loss
    risk_config_.take_profit_pct = 0.12;      // 12% take profit (3:1 reward/risk)
    risk_config_.max_drawdown = 0.15;         // 15% max drawdown
    risk_config_.enable_volatility_sizing = true;
    risk_config_.enable_atr_stops = true;
    risk_config_.atr_period = 14;
    risk_config_.atr_multiplier = 2.5;        // Wider stops for momentum
    risk_config_.enable_drawdown_breaker = true;
    risk_config_.drawdown_breaker_pct = 0.08; // 8% circuit breaker
    risk_config_.recovery_mode_risk = 0.01;    // 1% risk in recovery
  }

  std::string get_name() const override {
    return "MACD Momentum Strategy";
  }

  std::string get_description() const override {
    return "MACD-based momentum strategy with signal line crossovers";
  }

  std::vector<std::string> get_required_symbols() const override {
    return {symbol_};
  }

  RiskConfig get_risk_config() const override {
    return risk_config_;
  }

  void on_start() override {
    closes_.clear();
    ema_fast_.clear();
    ema_slow_.clear();
    macd_line_.clear();
    signal_line_.clear();
    histogram_.clear();

    current_position_ = {};
    current_position_.symbol = symbol_;

    portfolio_value_ = 100000.0;
    cash_ = portfolio_value_;
    fees_paid_ = 0.0;
    peak_portfolio_value_ = portfolio_value_;
    max_drawdown_ = 0.0;
    previous_value_ = portfolio_value_;
    last_price_ = 0.0;
    last_date_ = 0;

    trades_.clear();
    daily_returns_.clear();

    position_ = 0;
    stop_loss_price_ = 0.0;
    take_profit_price_ = 0.0;
    trailing_stop_price_ = 0.0;

    // Initialize MACD calculation
    macd_ = 0.0;
    signal_ = 0.0;
  }

  void on_bar(const Bar& b) override {
    double current_price = b.close;
    closes_.push_back(current_price);

    // Need minimum data for MACD calculation
    if (closes_.size() < static_cast<size_t>(slow_period_ + signal_period_)) {
      update_position_value(current_price);
      return;
    }

    // Calculate MACD
    calculate_macd();

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
    if (current_position_.quantity != 0.0) {
      double exit_price = (last_price_ > 0.0) ? last_price_ : current_position_.avg_entry_price;
      int exit_date = (last_date_ != 0) ? last_date_ : 0;
      close_position(exit_date, exit_price);
    }

    portfolio_value_ = cash_;

    calculate_final_metrics();
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

    // Apply volatility scaling (lower volatility = larger position for momentum)
    double adjusted_size = base_position_size * volatility_adjustment;

    // Ensure minimum and maximum bounds
    double min_size = portfolio_value * 0.001;  // 0.1% minimum
    double max_size = portfolio_value * risk_config_.max_portfolio_risk;

    return std::max(min_size, std::min(max_size, adjusted_size));
  }

  bool should_enter_position(const Bar& bar) override {
    if (closes_.size() < static_cast<size_t>(slow_period_ + signal_period_)) {
      return false;
    }

    calculate_macd();
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

    double risk_free_rate = 0.02;
    double annualized_return = mean_return * 252;

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
  void calculate_macd() {
    size_t size = closes_.size();

    // Calculate EMAs
    calculate_emas();

    // Calculate MACD line (fast EMA - slow EMA)
    if (ema_fast_.size() >= static_cast<size_t>(slow_period_)) {
      macd_ = ema_fast_.back() - ema_slow_.back();
      macd_line_.push_back(macd_);
    }

    // Calculate signal line (EMA of MACD line)
    if (macd_line_.size() >= static_cast<size_t>(signal_period_)) {
      size_t start_idx = macd_line_.size() - signal_period_;
      double sum = 0.0;
      for (size_t i = start_idx; i < macd_line_.size(); ++i) {
        sum += macd_line_[i];
      }
      signal_ = sum / signal_period_;
      signal_line_.push_back(signal_);
    }

    // Calculate histogram (MACD - Signal)
    if (!macd_line_.empty() && !signal_line_.empty()) {
      double hist = macd_line_.back() - signal_line_.back();
      histogram_.push_back(hist);
    }
  }

  void calculate_emas() {
    size_t size = closes_.size();

    // Calculate fast EMA
    if (ema_fast_.empty()) {
      // First EMA is just the price
      if (size >= static_cast<size_t>(fast_period_)) {
        double sum = 0.0;
        for (size_t i = size - fast_period_; i < size; ++i) {
          sum += closes_[i];
        }
        ema_fast_.push_back(sum / fast_period_);
      }
    } else {
      // Subsequent EMAs use smoothing
      double multiplier = 2.0 / (fast_period_ + 1.0);
      double ema = (closes_.back() * multiplier) + (ema_fast_.back() * (1.0 - multiplier));
      ema_fast_.push_back(ema);
    }

    // Calculate slow EMA
    if (ema_slow_.empty()) {
      // First EMA is just the price
      if (size >= static_cast<size_t>(slow_period_)) {
        double sum = 0.0;
        for (size_t i = size - slow_period_; i < size; ++i) {
          sum += closes_[i];
        }
        ema_slow_.push_back(sum / slow_period_);
      }
    } else {
      // Subsequent EMAs use smoothing
      double multiplier = 2.0 / (slow_period_ + 1.0);
      double ema = (closes_.back() * multiplier) + (ema_slow_.back() * (1.0 - multiplier));
      ema_slow_.push_back(ema);
    }
  }

  int generate_signal() {
    if (histogram_.size() < 2) return 0;

    double current_hist = histogram_.back();
    double previous_hist = histogram_[histogram_.size() - 2];

    // Bullish signal: MACD crosses above signal line
    if (previous_hist <= 0.0 && current_hist > 0.0) {
      return 1;  // Long signal
    }

    // Bearish signal: MACD crosses below signal line
    if (previous_hist >= 0.0 && current_hist < 0.0) {
      return -1;  // Short signal
    }

    // Additional filter: Check for strong momentum
    if (current_hist > overbought_level_) {
      return -1;  // Overbought, short signal
    }

    if (current_hist < oversold_level_) {
      return 1;  // Oversold, long signal
    }

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

    Trade entry_trade;
    entry_trade.date = date;
    entry_trade.side = (direction > 0) ? Trade::Side::BUY : Trade::Side::SELL;
    entry_trade.type = Trade::Type::ENTRY;
    entry_trade.price = price;
    entry_trade.quantity = quantity;
    entry_trade.symbol = symbol_;

    trades_.push_back(entry_trade);

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
    final_sharpe_ratio_ = get_sharpe_ratio();
    final_max_drawdown_ = get_max_drawdown();
    final_total_return_ = get_total_return();
  }

  double calculate_base_position_size(double portfolio_value) {
    // Use Kelly Criterion for base position sizing
    double win_rate = calculate_win_rate();
    double avg_win = calculate_avg_win();
    double avg_loss = calculate_avg_loss();

    if (win_rate <= 0.0 || avg_win <= 0.0 || avg_loss >= 0.0) {
      return portfolio_value * risk_config_.max_portfolio_risk;
    }

    double kelly_pct = win_rate - ((1.0 - win_rate) * avg_loss / avg_win);
    kelly_pct = std::min(kelly_pct, risk_config_.max_portfolio_risk);
    kelly_pct = std::max(kelly_pct, 0.001);

    return portfolio_value * kelly_pct;
  }

  double calculate_volatility_adjustment() {
    if (closes_.size() < 20) return 1.0;

    std::vector<double> returns;
    for (size_t i = 1; i < closes_.size(); ++i) {
      double ret = (closes_[i] - closes_[i-1]) / closes_[i-1];
      returns.push_back(ret);
    }

    if (returns.size() < 2) return 1.0;

    double mean_return = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();
    double variance = 0.0;
    for (double ret : returns) {
      variance += (ret - mean_return) * (ret - mean_return);
    }
    variance /= (returns.size() - 1);

    double volatility = std::sqrt(variance);
    double target_volatility = 0.02;
    double current_volatility = std::max(volatility, 0.001);

    // For momentum, higher volatility might indicate stronger trends
    double adjustment = current_volatility / target_volatility;
    return std::max(0.5, std::min(2.0, adjustment));
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
        win_count++;
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
        loss_count++;
      }
    }

    return loss_count > 0 ? total_losses / loss_count : 0.0;
  }

  void print_results() {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "MACD MOMENTUM STRATEGY RESULTS" << std::endl;
    std::cout << std::string(60, '=') << std::endl;
    std::cout << "Symbol: " << symbol_ << std::endl;
    std::cout << "Parameters: Fast=" << fast_period_ << ", Slow=" << slow_period_
              << ", Signal=" << signal_period_ << ", Overbought=" << overbought_level_
              << ", Oversold=" << oversold_level_ << ", Fee=" << fee_ << std::endl;

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

    std::cout << "\nMACD STATISTICS:" << std::endl;
    if (!macd_line_.empty()) {
      std::cout << "  Current MACD: " << macd_ << std::endl;
      std::cout << "  Current Signal: " << signal_ << std::endl;
      if (!histogram_.empty()) {
        std::cout << "  Current Histogram: " << histogram_.back() << std::endl;
      } else {
        std::cout << "  Current Histogram: n/a" << std::endl;
      }
    }

    std::cout << "\nRISK METRICS:" << std::endl;
    std::cout << "  Portfolio Value: $" << portfolio_value_ << std::endl;
    std::cout << "  Risk per Trade: " << (risk_config_.max_portfolio_risk * 100.0) << "%" << std::endl;
    std::cout << "  Stop Loss: " << (risk_config_.stop_loss_pct * 100.0) << "%" << std::endl;
    std::cout << "  Take Profit: " << (risk_config_.take_profit_pct * 100.0) << "%" << std::endl;

    std::cout << std::string(60, '=') << std::endl;
  }

  // Strategy parameters
  int fast_period_;
  int slow_period_;
  int signal_period_;
  double overbought_level_;
  double oversold_level_;
  double fee_;
  std::string symbol_;

  // Price data
  std::vector<double> closes_;
  std::vector<double> ema_fast_;
  std::vector<double> ema_slow_;
  std::vector<double> macd_line_;
  std::vector<double> signal_line_;
  std::vector<double> histogram_;
  double macd_ = 0.0;
  double signal_ = 0.0;

  // Position management
  int position_ = 0;
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

// Factory function for MACD strategy
std::unique_ptr<Strategy> make_macd_strategy(int fast_period, int slow_period, int signal_period,
                                             double overbought, double oversold, double fee, const std::string& symbol) {
  return std::make_unique<MacdMomentumStrategy>(fast_period, slow_period, signal_period, overbought, oversold, fee, symbol);
}
