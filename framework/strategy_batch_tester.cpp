#include "strategy_tester.h"
#include "strategy.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>

// Data loading function
std::vector<Bar> load_market_data(const std::string& filename) {
  std::vector<Bar> bars;
  std::ifstream file(filename);

  if (!file.is_open()) {
    std::cout << "Error: Cannot open data file: " << filename << std::endl;
    return bars;
  }

  std::string line;
  int line_count = 0;

  while (std::getline(file, line)) {
    ++line_count;
    if (line.length() < 2) continue;

    // Simple parser for OHLC data
    std::istringstream iss(line);
    Bar bar;

    // Parse date (first 8 characters)
    std::string date_str;
    if (!(iss >> date_str)) continue;

    try {
      bar.date = std::stoi(date_str.substr(0, 8));
    } catch (const std::exception&) {
      continue;  // Skip invalid lines
    }

    // Parse OHLC prices
    if (!(iss >> bar.open >> bar.high >> bar.low >> bar.close)) {
      continue;  // Skip if we can't parse all required fields
    }

    // Optional volume
    if (iss >> bar.volume) {
      // Volume provided
    } else {
      bar.volume = 0.0;  // Default volume
    }

    bars.push_back(bar);
  }

  file.close();

  std::cout << "Loaded " << bars.size() << " bars from " << filename << std::endl;
  return bars;
}

// Main batch testing function
void run_strategy_batch_test(const std::string& data_file,
                             int num_strategies = 50,
                             const std::string& strategy_type_input = "SMA") {
  std::cout << "\n" << std::string(100, '*') << std::endl;
  std::cout << "SYSTEMATIC STRATEGY GENERATION & TESTING" << std::endl;
  std::cout << std::string(100, '*') << std::endl;

  // Load market data
  std::cout << "Loading market data..." << std::endl;
  std::vector<Bar> data = load_market_data(data_file);

  if (data.empty()) {
    std::cout << "Error: No data loaded. Exiting." << std::endl;
    return;
  }

  std::cout << "Data loaded: " << data.size() << " bars" << std::endl;

  std::string strategy_type = strategy_type_input;
  std::transform(strategy_type.begin(), strategy_type.end(), strategy_type.begin(), [](unsigned char c) {
    return static_cast<char>(std::toupper(c));
  });

  // Initialize strategy tester
  StrategyTester tester;

  std::cout << "\nGenerating " << num_strategies << " " << strategy_type << " strategy configurations..." << std::endl;

  std::vector<StrategyTestConfig> configs;
  if (strategy_type == "SMA") {
    configs = StrategyGeneration::generate_sma_configs(num_strategies, 5, 50, 20, 200);
  } else if (strategy_type == "RSI") {
    configs = StrategyGeneration::generate_rsi_configs(num_strategies);
  } else if (strategy_type == "MACD") {
    configs = StrategyGeneration::generate_macd_configs(num_strategies);
  } else {
    std::cout << "Unknown strategy type: " << strategy_type_input << std::endl;
    return;
  }

  std::cout << "Generated " << configs.size() << " " << strategy_type << " strategy configurations" << std::endl;

  // Test all strategies
  std::cout << "\nStarting batch testing..." << std::endl;
  auto results = tester.test_multiple_strategies(configs, data);

  if (results.empty()) {
    std::cout << "Error: No results generated." << std::endl;
    return;
  }

  // Select and display top strategies
  std::cout << "\nSelecting top performing strategies..." << std::endl;
  auto top_strategies = tester.select_top_strategies(results, 10);

  // Save results to file
  std::ofstream results_file("strategy_test_results.txt");
  if (results_file.is_open()) {
    results_file << "STRATEGY TESTING RESULTS\n";
    results_file << "========================\n\n";

    results_file << "TOP 10 STRATEGIES:\n";
    results_file << "Rank\tStrategy\tReturn%\tSharpe\tMaxDD%\tWin%\tTrades\tScore\n";

    for (size_t i = 0; i < top_strategies.size(); ++i) {
      const auto& m = top_strategies[i];
      results_file << (i + 1) << "\t"
                   << m.strategy_name << "\t"
                   << (m.total_return * 100.0) << "\t"
                   << m.sharpe_ratio << "\t"
                   << (m.max_drawdown * 100.0) << "\t"
                   << (m.win_rate * 100.0) << "\t"
                   << m.total_trades << "\t"
                   << m.composite_score << "\n";
    }

    results_file << "\nDETAILED RESULTS:\n";
    for (size_t i = 0; i < results.size(); ++i) {
      const auto& m = results[i];
      results_file << "\n--- Strategy " << (i + 1) << " ---\n";
      results_file << "Parameters: ";
      for (size_t j = 0; j < m.parameters.size(); ++j) {
        results_file << m.parameters[j];
        if (j < m.parameters.size() - 1) results_file << ", ";
      }
      results_file << "\n";
      results_file << "Return: " << (m.total_return * 100.0) << "%\n";
      results_file << "Sharpe: " << m.sharpe_ratio << "\n";
      results_file << "Max DD: " << (m.max_drawdown * 100.0) << "%\n";
      results_file << "Score: " << m.composite_score << "\n";
    }

    results_file.close();
    std::cout << "Results saved to strategy_test_results.txt" << std::endl;
  }

  // Display summary
  std::cout << "\n" << std::string(100, '=') << std::endl;
  std::cout << "BATCH TESTING SUMMARY" << std::endl;
  std::cout << std::string(100, '=') << std::endl;

  double best_return = top_strategies[0].total_return;
  double avg_return = 0.0;
  double best_sharpe = 0.0;
  int total_trades = 0;

  for (const auto& m : results) {
    avg_return += m.total_return;
    if (m.sharpe_ratio > best_sharpe) best_sharpe = m.sharpe_ratio;
    total_trades += m.total_trades;
  }
  avg_return /= results.size();

  std::cout << "Best Strategy Return: " << (best_return * 100.0) << "%" << std::endl;
  std::cout << "Average Strategy Return: " << (avg_return * 100.0) << "%" << std::endl;
  std::cout << "Best Sharpe Ratio: " << best_sharpe << std::endl;
  std::cout << "Total Trades Across All Strategies: " << total_trades << std::endl;
  std::cout << "Strategies Tested: " << results.size() << std::endl;

  std::cout << "\n✅ STRATEGY GENERATION & TESTING COMPLETE!" << std::endl;
  std::cout << "📊 Check 'strategy_test_results.txt' for detailed results" << std::endl;
  std::cout << "🏆 Top strategies are ready for production use!" << std::endl;
}

// Interactive mode for custom testing
void run_interactive_mode() {
  std::cout << "\nINTERACTIVE STRATEGY TESTER" << std::endl;
  std::cout << "============================" << std::endl;

  std::string data_file;
  std::cout << "Enter data file path: ";
  std::getline(std::cin, data_file);

  // Load data
  auto data = load_market_data(data_file);
  if (data.empty()) {
    std::cout << "No data loaded. Exiting." << std::endl;
    return;
  }

  StrategyTester tester;

  while (true) {
    std::cout << "\nOptions:" << std::endl;
    std::cout << "1. Test single SMA strategy" << std::endl;
    std::cout << "2. Run batch test (50 strategies)" << std::endl;
    std::cout << "3. Run comprehensive test (100 strategies)" << std::endl;
    std::cout << "4. Exit" << std::endl;
    std::cout << "Choose option: ";

    std::string choice;
    std::getline(std::cin, choice);

    if (choice == "1") {
      // Single strategy test
      int short_win, long_win;
      double fee;

      std::cout << "Enter short window (5-50): ";
      std::string input;
      std::getline(std::cin, input);
      short_win = std::stoi(input);

      std::cout << "Enter long window (20-200): ";
      std::getline(std::cin, input);
      long_win = std::stoi(input);

      std::cout << "Enter fee (0.0001-0.001): ";
      std::getline(std::cin, input);
      fee = std::stod(input);

      StrategyTestConfig config;
      config.strategy_name = "SMA";
      config.parameters = {static_cast<double>(short_win), static_cast<double>(long_win), fee};

      auto metrics = tester.test_strategy(config, data);
      tester.print_strategy_metrics(metrics);

    } else if (choice == "2") {
      std::cout << "Enter strategy type (SMA/RSI/MACD) [SMA]: ";
      std::string type_input;
      std::getline(std::cin, type_input);
      if (type_input.empty()) type_input = "SMA";
      run_strategy_batch_test(data_file, 50, type_input);
    } else if (choice == "3") {
      std::cout << "Enter strategy type (SMA/RSI/MACD) [SMA]: ";
      std::string type_input;
      std::getline(std::cin, type_input);
      if (type_input.empty()) type_input = "SMA";
      run_strategy_batch_test(data_file, 100, type_input);
    } else if (choice == "4") {
      break;
    } else {
      std::cout << "Invalid option. Please try again." << std::endl;
    }
  }
}

int main(int argc, char** argv) {
  // Seed random number generator
  srand(static_cast<unsigned int>(time(nullptr)));

  std::cout << "STRATEGY GENERATION & TESTING FRAMEWORK" << std::endl;
  std::cout << "=======================================" << std::endl;

  if (argc >= 2) {
    // Command line mode
    std::string data_file = argv[1];
    int num_strategies = 50;
    std::string strategy_type = "SMA";

    if (argc >= 3) {
      bool numeric = true;
      for (const char* p = argv[2]; *p; ++p) {
        if (!std::isdigit(static_cast<unsigned char>(*p))) {
          numeric = false;
          break;
        }
      }

      if (numeric) {
        num_strategies = std::stoi(argv[2]);
        if (argc >= 4) {
          strategy_type = argv[3];
        }
      } else {
        strategy_type = argv[2];
        if (argc >= 4) {
          num_strategies = std::stoi(argv[3]);
        }
      }
    }

    run_strategy_batch_test(data_file, num_strategies, strategy_type);
  } else {
    // Default mode - use market_data.txt if it exists
    std::string default_file = "market_data.txt";
    std::ifstream test_file(default_file);
    if (test_file.good()) {
      test_file.close();
      std::cout << "Using default data file: " << default_file << std::endl;
      run_strategy_batch_test(default_file, 50);
    } else {
      test_file.close();
      std::cout << "No data file provided and market_data.txt not found." << std::endl;
      std::cout << "Usage: " << argv[0] << " <data_file> [num_strategies]" << std::endl;
      std::cout << "Starting interactive mode..." << std::endl;
      run_interactive_mode();
    }
  }

  return 0;
}
