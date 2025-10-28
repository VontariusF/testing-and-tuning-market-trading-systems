#include "strategy_registry.h"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <fstream>
#include <random>

// StrategyRegistry Implementation
StrategyRegistry::StrategyRegistry(const std::string& db_path) : db_path_(db_path), db_(nullptr) {}

StrategyRegistry::~StrategyRegistry() {
    if (db_) {
        sqlite3_close(db_);
    }
}

bool StrategyRegistry::initialize() {
    // Open database
    if (sqlite3_open(db_path_.c_str(), &db_) != SQLITE_OK) {
        std::cout << "Error opening database: " << sqlite3_errmsg(db_) << std::endl;
        return false;
    }

    // Create tables
    const char* create_strategies_table =
        "CREATE TABLE IF NOT EXISTS strategies ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "strategy_name TEXT NOT NULL,"
        "parameters_hash TEXT UNIQUE NOT NULL,"
        "parameters_json TEXT NOT NULL,"
        "total_return REAL,"
        "sharpe_ratio REAL,"
        "max_drawdown REAL,"
        "win_rate REAL,"
        "profit_factor REAL,"
        "total_trades INTEGER,"
        "composite_score REAL,"
        "tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ");";

    const char* create_regions_table =
        "CREATE TABLE IF NOT EXISTS parameter_regions ("
        "region_id TEXT PRIMARY KEY,"
        "exploration_count INTEGER DEFAULT 0,"
        "best_score REAL DEFAULT 0.0,"
        "last_tested TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ");";

    const char* create_generation_log =
        "CREATE TABLE IF NOT EXISTS generation_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "session_id TEXT,"
        "strategies_tested INTEGER,"
        "best_score REAL,"
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ");";

    if (!execute_sql(create_strategies_table) ||
        !execute_sql(create_regions_table) ||
        !execute_sql(create_generation_log)) {
        return false;
    }

    // Create indexes for performance
    execute_sql("CREATE INDEX IF NOT EXISTS idx_strategies_hash ON strategies(parameters_hash);");
    execute_sql("CREATE INDEX IF NOT EXISTS idx_strategies_score ON strategies(composite_score DESC);");
    execute_sql("CREATE INDEX IF NOT EXISTS idx_strategies_tested ON strategies(tested_at DESC);");

    return true;
}

bool StrategyRegistry::is_strategy_tested(const std::string& strategy_signature) {
    if (!db_) return false;

    sqlite3_stmt* stmt;
    const char* query = "SELECT COUNT(*) FROM strategies WHERE parameters_hash = ?;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_text(stmt, 1, strategy_signature.c_str(), -1, SQLITE_STATIC);

    bool exists = false;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        exists = (sqlite3_column_int(stmt, 0) > 0);
    }

    sqlite3_finalize(stmt);
    return exists;
}

bool StrategyRegistry::save_strategy_result(const StrategyMetrics& metrics) {
    if (!db_) return false;

    // Convert parameters to JSON
    std::ostringstream json_stream;
    json_stream << "[";
    for (size_t i = 0; i < metrics.parameters.size(); ++i) {
        json_stream << metrics.parameters[i];
        if (i < metrics.parameters.size() - 1) json_stream << ",";
    }
    json_stream << "]";

    std::string signature = generate_strategy_signature(metrics.parameters);

    sqlite3_stmt* stmt;
    const char* insert_query =
        "INSERT OR REPLACE INTO strategies "
        "(strategy_name, parameters_hash, parameters_json, total_return, sharpe_ratio, "
        "max_drawdown, win_rate, profit_factor, total_trades, composite_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);";

    if (sqlite3_prepare_v2(db_, insert_query, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_text(stmt, 1, metrics.strategy_name.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, signature.c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, json_stream.str().c_str(), -1, SQLITE_STATIC);
    sqlite3_bind_double(stmt, 4, metrics.total_return);
    sqlite3_bind_double(stmt, 5, metrics.sharpe_ratio);
    sqlite3_bind_double(stmt, 6, metrics.max_drawdown);
    sqlite3_bind_double(stmt, 7, metrics.win_rate);
    sqlite3_bind_double(stmt, 8, metrics.profit_factor);
    sqlite3_bind_int(stmt, 9, metrics.total_trades);
    sqlite3_bind_double(stmt, 10, metrics.composite_score);

    bool success = (sqlite3_step(stmt) == SQLITE_DONE);
    sqlite3_finalize(stmt);

    if (success) {
        // Update exploration region
        std::string region_id = generate_parameter_region_id(metrics.parameters);
        update_exploration_region(region_id, metrics.composite_score);
    }

    return success;
}

std::vector<StrategyMetrics> StrategyRegistry::get_top_strategies(int limit) {
    std::vector<StrategyMetrics> strategies;
    if (!db_) return strategies;

    sqlite3_stmt* stmt;
    std::string query = "SELECT * FROM strategies ORDER BY composite_score DESC LIMIT " + std::to_string(limit) + ";";

    if (sqlite3_prepare_v2(db_, query.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return strategies;
    }

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        strategies.push_back(load_strategy_from_db(stmt));
    }

    sqlite3_finalize(stmt);
    return strategies;
}

std::vector<StrategyMetrics> StrategyRegistry::get_recent_strategies(int limit) {
    std::vector<StrategyMetrics> strategies;
    if (!db_) return strategies;

    sqlite3_stmt* stmt;
    std::string query = "SELECT * FROM strategies ORDER BY tested_at DESC LIMIT " + std::to_string(limit) + ";";

    if (sqlite3_prepare_v2(db_, query.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        return strategies;
    }

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        strategies.push_back(load_strategy_from_db(stmt));
    }

    sqlite3_finalize(stmt);
    return strategies;
}

bool StrategyRegistry::update_exploration_region(const std::string& region_id, double score) {
    if (!db_) return false;

    sqlite3_stmt* stmt;

    // Try to update existing region
    const char* update_query = "UPDATE parameter_regions SET exploration_count = exploration_count + 1, "
                              "best_score = MAX(best_score, ?), last_tested = CURRENT_TIMESTAMP "
                              "WHERE region_id = ?;";

    if (sqlite3_prepare_v2(db_, update_query, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_double(stmt, 1, score);
    sqlite3_bind_text(stmt, 2, region_id.c_str(), -1, SQLITE_STATIC);

    bool updated = (sqlite3_step(stmt) == SQLITE_DONE);
    sqlite3_finalize(stmt);

    if (!updated) {
        // Insert new region
        const char* insert_query = "INSERT INTO parameter_regions (region_id, exploration_count, best_score) VALUES (?, 1, ?);";

        if (sqlite3_prepare_v2(db_, insert_query, -1, &stmt, nullptr) != SQLITE_OK) {
            return false;
        }

        sqlite3_bind_text(stmt, 1, region_id.c_str(), -1, SQLITE_STATIC);
        sqlite3_bind_double(stmt, 2, score);

        updated = (sqlite3_step(stmt) == SQLITE_DONE);
        sqlite3_finalize(stmt);
    }

    return updated;
}

std::vector<std::string> StrategyRegistry::get_underexplored_regions() {
    std::vector<std::string> regions;
    if (!db_) return regions;

    sqlite3_stmt* stmt;
    const char* query = "SELECT region_id FROM parameter_regions WHERE exploration_count < 5 ORDER BY exploration_count ASC;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return regions;
    }

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        regions.push_back(reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0)));
    }

    sqlite3_finalize(stmt);
    return regions;
}

int StrategyRegistry::get_exploration_count(const std::string& region_id) {
    if (!db_) return 0;

    sqlite3_stmt* stmt;
    const char* query = "SELECT exploration_count FROM parameter_regions WHERE region_id = ?;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return 0;
    }

    sqlite3_bind_text(stmt, 1, region_id.c_str(), -1, SQLITE_STATIC);

    int count = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return count;
}

bool StrategyRegistry::cleanup_old_strategies(int keep_count) {
    if (!db_) return false;

    // Delete old strategies, keeping only the top performers and most recent
    const char* delete_query =
        "DELETE FROM strategies WHERE id NOT IN ("
        "SELECT id FROM strategies ORDER BY composite_score DESC, tested_at DESC LIMIT ?"
        ");";

    sqlite3_stmt* stmt;
    if (sqlite3_prepare_v2(db_, delete_query, -1, &stmt, nullptr) != SQLITE_OK) {
        return false;
    }

    sqlite3_bind_int(stmt, 1, keep_count);

    bool success = (sqlite3_step(stmt) == SQLITE_DONE);
    sqlite3_finalize(stmt);

    return success;
}

bool StrategyRegistry::vacuum_database() {
    return execute_sql("VACUUM;");
}

int StrategyRegistry::get_total_strategy_count() {
    if (!db_) return 0;

    sqlite3_stmt* stmt;
    const char* query = "SELECT COUNT(*) FROM strategies;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return 0;
    }

    int count = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return count;
}

double StrategyRegistry::get_average_score() {
    if (!db_) return 0.0;

    sqlite3_stmt* stmt;
    const char* query = "SELECT AVG(composite_score) FROM strategies WHERE composite_score > 0;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return 0.0;
    }

    double avg = 0.0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        avg = sqlite3_column_double(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return avg;
}

std::vector<std::string> StrategyRegistry::get_most_successful_parameter_regions() {
    std::vector<std::string> regions;
    if (!db_) return regions;

    sqlite3_stmt* stmt;
    const char* query =
        "SELECT pr.region_id FROM parameter_regions pr "
        "JOIN strategies s ON s.parameters_hash IN ("
        "    SELECT parameters_hash FROM strategies WHERE composite_score > 0.5"
        ") GROUP BY pr.region_id ORDER BY AVG(s.composite_score) DESC LIMIT 10;";

    if (sqlite3_prepare_v2(db_, query, -1, &stmt, nullptr) != SQLITE_OK) {
        return regions;
    }

    while (sqlite3_step(stmt) == SQLITE_ROW) {
        regions.push_back(reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0)));
    }

    sqlite3_finalize(stmt);
    return regions;
}

// Private helper methods
bool StrategyRegistry::execute_sql(const std::string& sql) {
    if (!db_) return false;

    char* error_msg;
    if (sqlite3_exec(db_, sql.c_str(), nullptr, nullptr, &error_msg) != SQLITE_OK) {
        std::cout << "SQL Error: " << error_msg << std::endl;
        sqlite3_free(error_msg);
        return false;
    }

    return true;
}

std::string StrategyRegistry::generate_strategy_signature(const std::vector<double>& parameters) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(8);

    for (double param : parameters) {
        oss << param << "|";
    }

    return oss.str();
}

std::string StrategyRegistry::generate_parameter_region_id(const std::vector<double>& parameters) {
    std::ostringstream oss;

    for (double param : parameters) {
        // Create region buckets (e.g., round to nearest 0.1)
        double bucket = std::round(param * 10.0) / 10.0;
        oss << bucket << "|";
    }

    return oss.str();
}

StrategyMetrics StrategyRegistry::load_strategy_from_db(sqlite3_stmt* stmt) {
    StrategyMetrics metrics;

    metrics.strategy_name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));

    // Parse parameters JSON
    std::string params_json = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
    std::istringstream iss(params_json.substr(1, params_json.length() - 2));  // Remove [ ]
    std::string param;
    while (std::getline(iss, param, ',')) {
        if (!param.empty()) {
            metrics.parameters.push_back(std::stod(param));
        }
    }

    metrics.total_return = sqlite3_column_double(stmt, 4);
    metrics.sharpe_ratio = sqlite3_column_double(stmt, 5);
    metrics.max_drawdown = sqlite3_column_double(stmt, 6);
    metrics.win_rate = sqlite3_column_double(stmt, 7);
    metrics.profit_factor = sqlite3_column_double(stmt, 8);
    metrics.total_trades = sqlite3_column_int(stmt, 9);
    metrics.composite_score = sqlite3_column_double(stmt, 10);

    return metrics;
}

bool StrategyRegistry::save_strategy_to_db(const StrategyMetrics& metrics) {
    return save_strategy_result(metrics);
}

// ExplorationManager Implementation
ExplorationManager::ExplorationManager(StrategyRegistry& registry) : registry_(registry) {
    // Seed with current time for reproducible results
    seed_ = static_cast<unsigned int>(time(nullptr));
    srand(seed_);
}

std::vector<double> ExplorationManager::generate_exploration_parameters(
    const std::vector<std::pair<double, double>>& ranges) {

    // Get underexplored regions first
    auto underexplored = registry_.get_underexplored_regions();

    if (!underexplored.empty()) {
        // Generate parameters in underexplored region
        std::string target_region = underexplored[0];

        // For now, generate random parameters (in a full implementation,
        // we'd decode the region and generate within that specific area)
        std::vector<double> params;
        for (const auto& range : ranges) {
            double random_value = range.first + (range.second - range.first) * (static_cast<double>(rand()) / RAND_MAX);
            params.push_back(random_value);
        }

        return params;
    }

    // Fall back to random generation
    std::vector<double> params;
    for (const auto& range : ranges) {
        double random_value = range.first + (range.second - range.first) * (static_cast<double>(rand()) / RAND_MAX);
        params.push_back(random_value);
    }

    return params;
}

std::vector<double> ExplorationManager::generate_success_based_parameters(
    const std::vector<std::pair<double, double>>& ranges) {

    // Get top performing strategies
    auto top_strategies = registry_.get_top_strategies(10);

    if (top_strategies.empty()) {
        // No successful strategies yet, use random
        return generate_exploration_parameters(ranges);
    }

    // Pick a random successful strategy and mutate it
    int random_index = rand() % top_strategies.size();
    const auto& base_strategy = top_strategies[random_index];

    return mutate_around_successful(base_strategy.parameters, ranges);
}

void ExplorationManager::update_exploration_stats(const std::vector<double>& parameters, double score) {
    std::string region_id = get_parameter_region(parameters);
    registry_.update_exploration_region(region_id, score);
}

std::vector<std::string> ExplorationManager::get_exploration_recommendations() {
    std::vector<std::string> recommendations;

    auto underexplored = registry_.get_underexplored_regions();
    if (!underexplored.empty()) {
        recommendations.push_back("Focus on underexplored parameter regions");
    }

    auto successful_regions = registry_.get_most_successful_parameter_regions();
    if (!successful_regions.empty()) {
        recommendations.push_back("Generate variations around successful parameter regions");
    }

    return recommendations;
}

std::string ExplorationManager::get_parameter_region(const std::vector<double>& parameters) {
    std::ostringstream oss;
    for (double param : parameters) {
        double bucket = std::round(param * 10.0) / 10.0;
        oss << bucket << "|";
    }
    return oss.str();
}

double ExplorationManager::calculate_region_score(const std::string& region_id) {
    return registry_.get_exploration_count(region_id) > 0 ? 1.0 / registry_.get_exploration_count(region_id) : 1.0;
}

std::vector<double> ExplorationManager::mutate_around_successful(
    const std::vector<double>& base_params,
    const std::vector<std::pair<double, double>>& ranges) {

    std::vector<double> mutated_params = base_params;

    // Mutate each parameter with 30% probability
    for (size_t i = 0; i < mutated_params.size(); ++i) {
        double rand_val = static_cast<double>(rand()) / RAND_MAX;
        if (rand_val < 0.3) {  // 30% mutation rate
            double mutation = -0.1 + 0.2 * (static_cast<double>(rand()) / RAND_MAX);  // -0.1 to 0.1
            mutated_params[i] = base_params[i] + (ranges[i].second - ranges[i].first) * mutation;

            // Clamp to valid range
            mutated_params[i] = std::max(ranges[i].first,
                               std::min(ranges[i].second, mutated_params[i]));
        }
    }

    return mutated_params;
}

// SmartStrategyTester Implementation
SmartStrategyTester::SmartStrategyTester(const std::string& db_path) {
    registry_ = std::make_unique<StrategyRegistry>(db_path);
    exploration_manager_ = std::make_unique<ExplorationManager>(*registry_);

    if (!registry_->initialize()) {
        std::cout << "Warning: Could not initialize strategy registry" << std::endl;
    }
}

std::vector<StrategyMetrics> SmartStrategyTester::test_strategies_with_deduplication(
    const std::vector<StrategyTestConfig>& configs,
    const std::vector<Bar>& data,
    int max_attempts) {

    std::vector<StrategyMetrics> results;
    int attempts = 0;

    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "SMART STRATEGY TESTING WITH DEDUPLICATION" << std::endl;
    std::cout << "Target: " << configs.size() << " unique strategies" << std::endl;
    std::cout << std::string(80, '=') << std::endl;

    for (const auto& config : configs) {
        if (attempts >= max_attempts) {
            std::cout << "Reached maximum attempts limit (" << max_attempts << ")" << std::endl;
            break;
        }

        std::string signature = registry_->generate_strategy_signature(config.parameters);

        if (registry_->is_strategy_tested(signature)) {
            std::cout << "Skipping duplicate strategy: " << config.strategy_name
                      << " (" << attempts + 1 << "/" << max_attempts << ")" << std::endl;
            attempts++;
            continue;
        }

        std::cout << "Testing unique strategy: " << config.strategy_name
                  << " (" << (attempts + 1) << "/" << max_attempts << ")" << std::endl;

        StrategyMetrics metrics = test_strategy(config, data);
        results.push_back(metrics);

        // Save result to registry
        registry_->save_strategy_result(metrics);

        attempts++;
    }

    std::cout << "Successfully tested " << results.size() << " unique strategies" << std::endl;
    return results;
}

std::vector<StrategyMetrics> SmartStrategyTester::discover_strategies(
    const std::vector<Bar>& data,
    int target_count,
    int max_total_attempts) {

    std::vector<StrategyMetrics> results;
    int attempts = 0;

    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "STRATEGY DISCOVERY MODE" << std::endl;
    std::cout << "Target: " << target_count << " unique strategies" << std::endl;
    std::cout << std::string(80, '=') << std::endl;

    // Define parameter ranges for SMA strategies
    std::vector<std::pair<double, double>> param_ranges = {
        {5.0, 50.0},    // short_window
        {20.0, 200.0},  // long_window
        {0.0001, 0.001} // fee
    };

    while (results.size() < static_cast<size_t>(target_count) && attempts < max_total_attempts) {
        // Generate strategy configuration
        StrategyTestConfig config;
        config.strategy_name = "SMA";

        // Use intelligent parameter generation
        config.parameters = exploration_manager_->generate_exploration_parameters(param_ranges);

        // Ensure short < long
        if (config.parameters.size() >= 2) {
            int short_win = std::max(2, static_cast<int>(config.parameters[0]));
            int long_win = std::max(short_win + 5, static_cast<int>(config.parameters[1]));
            config.parameters[0] = short_win;
            config.parameters[1] = long_win;
        }

        std::string signature = registry_->generate_strategy_signature(config.parameters);

        if (registry_->is_strategy_tested(signature)) {
            attempts++;
            continue;
        }

        std::cout << "Testing strategy " << (results.size() + 1) << "/" << target_count
                  << " (attempt " << (attempts + 1) << ")" << std::endl;

        StrategyMetrics metrics = test_strategy(config, data);
        results.push_back(metrics);

        // Save result and update exploration stats
        registry_->save_strategy_result(metrics);
        exploration_manager_->update_exploration_stats(config.parameters, metrics.composite_score);

        attempts++;
    }

    std::cout << "\nDiscovered " << results.size() << " unique strategies in " << attempts << " attempts" << std::endl;
    return results;
}

void SmartStrategyTester::print_registry_stats() {
    std::cout << "\n" << std::string(60, '=') << std::endl;
    std::cout << "STRATEGY REGISTRY STATISTICS" << std::endl;
    std::cout << std::string(60, '=') << std::endl;

    std::cout << "Total strategies tested: " << registry_->get_total_strategy_count() << std::endl;
    std::cout << "Average composite score: " << registry_->get_average_score() << std::endl;

    auto underexplored = registry_->get_underexplored_regions();
    std::cout << "Underexplored regions: " << underexplored.size() << std::endl;

    auto successful_regions = registry_->get_most_successful_parameter_regions();
    std::cout << "Most successful regions: " << successful_regions.size() << std::endl;

    std::cout << std::string(60, '=') << std::endl;
}

bool SmartStrategyTester::is_config_duplicate(const StrategyTestConfig& config) {
    std::string signature = registry_->generate_strategy_signature(config.parameters);
    return registry_->is_strategy_tested(signature);
}

StrategyTestConfig SmartStrategyTester::generate_unique_config(const ParameterGenConfig& gen_config) {
    StrategyTestConfig config;
    config.strategy_name = gen_config.strategy_type;

    int attempts = 0;
    const int max_attempts = 100;

    do {
        config.parameters = StrategyTester::generate_random_parameters_static(gen_config.parameter_ranges);
        attempts++;

        if (attempts >= max_attempts) {
            std::cout << "Warning: Could not generate unique parameters after " << max_attempts << " attempts" << std::endl;
            break;
        }
    } while (is_config_duplicate(config));

    return config;
}

// StrategyManagement namespace functions
namespace StrategyManagement {

bool initialize_strategy_database(const std::string& db_path) {
    StrategyRegistry registry(db_path);
    return registry.initialize();
}

bool export_strategies_to_csv(const std::vector<StrategyMetrics>& strategies, const std::string& filename) {
    std::ofstream file(filename);
    if (!file.is_open()) {
        return false;
    }

    // Write header
    file << "Strategy,Total_Return,Sharpe_Ratio,Max_Drawdown,Win_Rate,Profit_Factor,Total_Trades,Composite_Score,Parameters\n";

    // Write data
    for (const auto& strategy : strategies) {
        file << strategy.strategy_name << ","
             << strategy.total_return << ","
             << strategy.sharpe_ratio << ","
             << strategy.max_drawdown << ","
             << strategy.win_rate << ","
             << strategy.profit_factor << ","
             << strategy.total_trades << ","
             << strategy.composite_score << ",";

        // Write parameters
        for (size_t i = 0; i < strategy.parameters.size(); ++i) {
            file << strategy.parameters[i];
            if (i < strategy.parameters.size() - 1) file << ";";
        }
        file << "\n";
    }

    file.close();
    return true;
}

std::vector<StrategyMetrics> import_strategies_from_csv(const std::string& filename) {
    std::vector<StrategyMetrics> strategies;
    std::ifstream file(filename);

    if (!file.is_open()) {
        return strategies;
    }

    std::string line;
    bool is_header = true;

    while (std::getline(file, line)) {
        if (is_header) {
            is_header = false;
            continue;  // Skip header
        }

        std::istringstream iss(line);
        std::string token;
        StrategyMetrics metrics;

        // Parse strategy name
        if (std::getline(iss, token, ',')) {
            metrics.strategy_name = token;
        }

        // Parse metrics
        if (std::getline(iss, token, ',')) metrics.total_return = std::stod(token);
        if (std::getline(iss, token, ',')) metrics.sharpe_ratio = std::stod(token);
        if (std::getline(iss, token, ',')) metrics.max_drawdown = std::stod(token);
        if (std::getline(iss, token, ',')) metrics.win_rate = std::stod(token);
        if (std::getline(iss, token, ',')) metrics.profit_factor = std::stod(token);
        if (std::getline(iss, token, ',')) metrics.total_trades = std::stoi(token);
        if (std::getline(iss, token, ',')) metrics.composite_score = std::stod(token);

        // Parse parameters
        if (std::getline(iss, token, ',')) {
            std::istringstream param_iss(token);
            std::string param;
            while (std::getline(param_iss, param, ';')) {
                metrics.parameters.push_back(std::stod(param));
            }
        }

        strategies.push_back(metrics);
    }

    file.close();
    return strategies;
}

std::string generate_performance_report(const std::vector<StrategyMetrics>& strategies) {
    std::ostringstream report;

    report << "STRATEGY PERFORMANCE REPORT\n";
    report << "==========================\n\n";

    report << "Summary Statistics:\n";
    report << "- Total Strategies: " << strategies.size() << "\n";

    if (!strategies.empty()) {
        double avg_return = 0.0, avg_sharpe = 0.0, avg_score = 0.0;
        int total_trades = 0;

        for (const auto& s : strategies) {
            avg_return += s.total_return;
            avg_sharpe += s.sharpe_ratio;
            avg_score += s.composite_score;
            total_trades += s.total_trades;
        }

        avg_return /= strategies.size();
        avg_sharpe /= strategies.size();
        avg_score /= strategies.size();

        report << "- Average Return: " << (avg_return * 100.0) << "%\n";
        report << "- Average Sharpe: " << avg_sharpe << "\n";
        report << "- Average Score: " << avg_score << "\n";
        report << "- Total Trades: " << total_trades << "\n";
    }

    report << "\nTop 5 Strategies:\n";
    for (size_t i = 0; i < std::min(size_t(5), strategies.size()); ++i) {
        const auto& s = strategies[i];
        report << (i + 1) << ". " << s.strategy_name
               << " (Return: " << (s.total_return * 100.0) << "%, "
               << "Sharpe: " << s.sharpe_ratio << ", "
               << "Score: " << s.composite_score << ")\n";
    }

    return report.str();
}

bool optimize_strategy_database(const std::string& db_path) {
    StrategyRegistry registry(db_path);

    std::cout << "Optimizing strategy database..." << std::endl;

    // Clean up old strategies
    if (!registry.cleanup_old_strategies(10000)) {
        return false;
    }

    // Vacuum database for better performance
    if (!registry.vacuum_database()) {
        return false;
    }

    std::cout << "Database optimization complete" << std::endl;
    return true;
}

}
