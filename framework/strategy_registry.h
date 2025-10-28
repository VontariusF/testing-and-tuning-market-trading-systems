#pragma once

#include "strategy_tester.h"
#include <string>
#include <vector>
#include <memory>
#include <sqlite3.h>

// Strategy registry for tracking tested strategies and preventing duplicates
class StrategyRegistry {
public:
    StrategyRegistry(const std::string& db_path = "strategy_registry.db");
    ~StrategyRegistry();

    // Initialize database tables
    bool initialize();

    // Strategy management
    bool is_strategy_tested(const std::string& strategy_signature);
    bool save_strategy_result(const StrategyMetrics& metrics);
    std::vector<StrategyMetrics> get_top_strategies(int limit = 100);
    std::vector<StrategyMetrics> get_recent_strategies(int limit = 10000);

    // Exploration tracking
    bool update_exploration_region(const std::string& region_id, double score);
    std::vector<std::string> get_underexplored_regions();
    int get_exploration_count(const std::string& region_id);

    // Database maintenance
    bool cleanup_old_strategies(int keep_count = 10000);
    bool vacuum_database();

    // Statistics
    int get_total_strategy_count();
    double get_average_score();
    std::vector<std::string> get_most_successful_parameter_regions();

private:
    sqlite3* db_;
    std::string db_path_;

    // Helper methods
    bool execute_sql(const std::string& sql);
public:
    std::string generate_strategy_signature(const std::vector<double>& parameters);
    std::string generate_parameter_region_id(const std::vector<double>& parameters);
    StrategyMetrics load_strategy_from_db(sqlite3_stmt* stmt);
    bool save_strategy_to_db(const StrategyMetrics& metrics);
};

// Strategy exploration manager for intelligent parameter generation
class ExplorationManager {
public:
    ExplorationManager(StrategyRegistry& registry);

    // Generate parameters in underexplored regions first
    std::vector<double> generate_exploration_parameters(
        const std::vector<std::pair<double, double>>& ranges);

    // Generate parameters around successful strategies
    std::vector<double> generate_success_based_parameters(
        const std::vector<std::pair<double, double>>& ranges);

    // Update exploration statistics
    void update_exploration_stats(const std::vector<double>& parameters, double score);

    // Get exploration recommendations
    std::vector<std::string> get_exploration_recommendations();

private:
    StrategyRegistry& registry_;
    unsigned int seed_;  // For reproducible random generation

    std::string get_parameter_region(const std::vector<double>& parameters);
    double calculate_region_score(const std::string& region_id);
    std::vector<double> mutate_around_successful(const std::vector<double>& base_params,
                                               const std::vector<std::pair<double, double>>& ranges);
};

// Enhanced strategy tester with deduplication
class SmartStrategyTester : public StrategyTester {
public:
    SmartStrategyTester(const std::string& db_path = "strategy_registry.db");

    // Enhanced testing with deduplication
    std::vector<StrategyMetrics> test_strategies_with_deduplication(
        const std::vector<StrategyTestConfig>& configs,
        const std::vector<Bar>& data,
        int max_attempts = 1000);

    // Generate and test strategies intelligently
    std::vector<StrategyMetrics> discover_strategies(
        const std::vector<Bar>& data,
        int target_count = 100,
        int max_total_attempts = 1000);

    // Get registry statistics
    void print_registry_stats();

private:
    std::unique_ptr<StrategyRegistry> registry_;
    std::unique_ptr<ExplorationManager> exploration_manager_;

    bool is_config_duplicate(const StrategyTestConfig& config);
    StrategyTestConfig generate_unique_config(const ParameterGenConfig& gen_config);
};

// Utility functions for strategy management
namespace StrategyManagement {

    // Create database and initialize tables
    bool initialize_strategy_database(const std::string& db_path = "strategy_registry.db");

    // Export strategy results to CSV
    bool export_strategies_to_csv(const std::vector<StrategyMetrics>& strategies,
                                 const std::string& filename = "strategy_results.csv");

    // Import strategies from CSV
    std::vector<StrategyMetrics> import_strategies_from_csv(const std::string& filename);

    // Generate strategy performance report
    std::string generate_performance_report(const std::vector<StrategyMetrics>& strategies);

    // Clean and optimize strategy database
    bool optimize_strategy_database(const std::string& db_path = "strategy_registry.db");

}
