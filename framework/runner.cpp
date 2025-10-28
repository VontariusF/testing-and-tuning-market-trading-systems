#include "strategy.h"
#include "strategy_factory.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

static void usage() {
  std::cout << "Usage: strategy_runner <strategy> <ohlc_file> [options]\n";
  std::cout << "  strategies:\n"
            << "    sma  --short N --long M --fee F --symbol TICKER\n"
            << "    rsi  --period N --overbought X --oversold Y --confirm K --fee F --symbol TICKER\n"
            << "    macd --fast N --slow M --signal K --overbought X --oversold Y --fee F --symbol TICKER\n";
  std::cout << "  Format: YYYYMMDD Open High Low Close [Volume]\n";
}

static std::string to_upper(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
    return static_cast<char>(std::toupper(c));
  });
  return value;
}

static bool parse_ohlc_line(const std::string& line, Bar& out) {
  if (line.length() < 8) return false;

  size_t pos = 0;
  std::string date_str = line.substr(0, 8);
  for (char c : date_str) {
    if (c < '0' || c > '9') return false;
  }
  out.date = std::stoi(date_str);

  pos = 8;
  auto skip_delim = [&]() {
    while (pos < line.length() && (line[pos] == ' ' || line[pos] == '\t' || line[pos] == ',')) ++pos;
  };

  skip_delim();
  if (pos >= line.length()) return false;
  size_t end_pos;
  out.open = std::stod(line.substr(pos), &end_pos);
  pos += end_pos;

  skip_delim();
  if (pos >= line.length()) return false;
  out.high = std::stod(line.substr(pos), &end_pos);
  pos += end_pos;

  skip_delim();
  if (pos >= line.length()) return false;
  out.low = std::stod(line.substr(pos), &end_pos);
  pos += end_pos;

  skip_delim();
  if (pos >= line.length()) return false;
  out.close = std::stod(line.substr(pos), &end_pos);
  pos += end_pos;

  skip_delim();
  if (pos < line.length()) {
    out.volume = std::stod(line.substr(pos), &end_pos);
  } else {
    out.volume = 0.0;
  }

  if (!std::isfinite(out.open) || !std::isfinite(out.high) ||
      !std::isfinite(out.low) || !std::isfinite(out.close)) {
    return false;
  }

  return true;
}

int main(int argc, char** argv) {
  if (argc < 3) {
    usage();
    return 1;
  }

  const std::string strategy_input = argv[1];
  const std::string strategy_name = to_upper(strategy_input);
  const std::string filename = argv[2];

  // Shared defaults
  double fee = 0.0005;
  std::string symbol = "DEMO";

  // SMA defaults
  int sma_short = 10;
  int sma_long = 40;

  // RSI defaults
  int rsi_period = 14;
  double rsi_overbought = 70.0;
  double rsi_oversold = 30.0;
  int rsi_confirm = 2;

  // MACD defaults
  int macd_fast = 12;
  int macd_slow = 26;
  int macd_signal = 9;
  double macd_overbought = 1.0;
  double macd_oversold = -1.0;

  auto require_value = [&](const std::string& option, int index) {
    if (index + 1 >= argc) {
      std::cout << "Missing value for option " << option << std::endl;
      usage();
      std::exit(1);
    }
  };

  for (int i = 3; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--symbol") {
      require_value(arg, i);
      symbol = argv[++i];
    } else if (arg == "--fee") {
      require_value(arg, i);
      fee = std::atof(argv[++i]);
    } else if (strategy_name == "SMA" && arg == "--short") {
      require_value(arg, i);
      sma_short = std::atoi(argv[++i]);
    } else if (strategy_name == "SMA" && arg == "--long") {
      require_value(arg, i);
      sma_long = std::atoi(argv[++i]);
    } else if (strategy_name == "RSI" && arg == "--period") {
      require_value(arg, i);
      rsi_period = std::atoi(argv[++i]);
    } else if (strategy_name == "RSI" && arg == "--overbought") {
      require_value(arg, i);
      rsi_overbought = std::atof(argv[++i]);
    } else if (strategy_name == "RSI" && arg == "--oversold") {
      require_value(arg, i);
      rsi_oversold = std::atof(argv[++i]);
    } else if (strategy_name == "RSI" && arg == "--confirm") {
      require_value(arg, i);
      rsi_confirm = std::atoi(argv[++i]);
    } else if (strategy_name == "MACD" && arg == "--fast") {
      require_value(arg, i);
      macd_fast = std::atoi(argv[++i]);
    } else if (strategy_name == "MACD" && arg == "--slow") {
      require_value(arg, i);
      macd_slow = std::atoi(argv[++i]);
    } else if (strategy_name == "MACD" && arg == "--signal") {
      require_value(arg, i);
      macd_signal = std::atoi(argv[++i]);
    } else if (strategy_name == "MACD" && arg == "--overbought") {
      require_value(arg, i);
      macd_overbought = std::atof(argv[++i]);
    } else if (strategy_name == "MACD" && arg == "--oversold") {
      require_value(arg, i);
      macd_oversold = std::atof(argv[++i]);
    } else {
      std::cout << "Unknown or invalid option: " << arg << std::endl;
      usage();
      return 1;
    }
  }

  std::vector<double> parameters;
  if (strategy_name == "SMA") {
    if (sma_long <= sma_short) {
      std::cout << "For SMA, long window must be greater than short window." << std::endl;
      return 1;
    }
    parameters = {static_cast<double>(sma_short), static_cast<double>(sma_long), fee};
  } else if (strategy_name == "RSI") {
    if (rsi_overbought <= rsi_oversold) {
      std::cout << "RSI overbought level must be greater than oversold level." << std::endl;
      return 1;
    }
    parameters = {
      static_cast<double>(rsi_period),
      rsi_overbought,
      rsi_oversold,
      static_cast<double>(rsi_confirm),
      fee
    };
  } else if (strategy_name == "MACD") {
    if (macd_slow <= macd_fast) {
      std::cout << "MACD slow period must be greater than fast period." << std::endl;
      return 1;
    }
    parameters = {
      static_cast<double>(macd_fast),
      static_cast<double>(macd_slow),
      static_cast<double>(macd_signal),
      macd_overbought,
      macd_oversold,
      fee
    };
  } else {
    std::cout << "Unknown strategy: " << strategy_input << std::endl;
    usage();
    return 1;
  }

  auto strategy = StrategyFactory::create_strategy(strategy_name, parameters, symbol);
  if (!strategy) {
    std::cout << "Failed to create strategy" << std::endl;
    return 1;
  }

  std::ifstream file(filename);
  if (!file.is_open()) {
    std::cout << "Cannot open file: " << filename << std::endl;
    return 1;
  }

  std::cout << "Starting " << strategy->get_name() << " with " << symbol << std::endl;
  std::cout << "File: " << filename << std::endl;

  strategy->on_start();

  std::string line;
  int line_count = 0;
  int valid_bars = 0;

  while (std::getline(file, line)) {
    ++line_count;
    if (line.length() < 2) continue;

    Bar bar;
    if (parse_ohlc_line(line, bar)) {
      ++valid_bars;
      strategy->on_bar(bar);
    } else {
      std::cout << "Warning: Skipping invalid line " << line_count << std::endl;
    }
  }

  file.close();

  std::cout << "Processed " << line_count << " lines, " << valid_bars << " valid bars" << std::endl;

  strategy->on_finish();

  std::cout << "\n=== STRATEGY SUMMARY ===" << std::endl;
  std::cout << "Strategy: " << strategy->get_name() << std::endl;
  std::cout << "Symbol: " << symbol << std::endl;
  std::cout << "Total Return: " << (strategy->get_total_return() * 100.0) << "%" << std::endl;
  std::cout << "Sharpe Ratio: " << strategy->get_sharpe_ratio() << std::endl;
  std::cout << "Max Drawdown: " << (strategy->get_max_drawdown() * 100.0) << "%" << std::endl;
  std::cout << "Total Trades: " << strategy->get_trade_count() << std::endl;

  return 0;
}
