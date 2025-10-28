# Claude Code Memory - Trading System

## Repository Overview
This is a comprehensive trading strategy testing and validation system with both legacy C++ algorithms and modern Python frameworks.

## System Architecture

### Core Components
- **C++ Trading Algorithms**: 36+ compiled executables in `build/` directory
- **StratVal Framework**: Python validation system with 9 algorithm adapters
- **Strategy Framework**: Modern C++ strategy implementations (SMA, RSI, MACD)
- **Automation System**: Bias remediation and strategy generation pipelines
- **Database Integration**: PostgreSQL with 420K+ market data candles

### Key Executables
- `build/strategy_runner`: Main strategy execution engine
- `build/strategy_batch_tester`: Parameter sweep and comparison tool
- `build/MCPT_BARS`, `build/DRAWDOWN`, `build/CD_MA`: Validation algorithms

### Data Assets
- **PostgreSQL Database**: 420,956 candles of real market data
- **binance_BTC_USDT_1h.txt**: 50,000 BTC hourly candles
- **data/larger_sample_data.txt**: 1,645 candles for testing
- **Multiple symbol support**: Database contains various trading pairs

## Known Issues (From SYSTEM_ANALYSIS_REPORT.md)

### Critical Issues
1. **Data Underutilization**: System defaults to 50-bar samples despite having 420K+ candles available
2. **Timeout Configuration Problems**: Inconsistent timeouts causing algorithm failures
   - Standard mode: 480s vs Thorough mode: 300s (inconsistent)
   - DRAWDOWN and MCPT_TRN frequently timeout
3. **Database Configuration Split**: PostgreSQL (production data) vs SQLite (local schema)

### Solutions Needed
- Update `stratval/utils/config.py` timeout settings
- Configure default data sources to use real market data
- Fix PostgreSQL vs SQLite data source routing

## Strategy Generation System

### Working Components
- ✅ 50+ strategies generated in `end_to_end_results/generated_strategies/`
- ✅ Template-based strategy creation functional
- ✅ Automated bias remediation pipeline operational
- ✅ Database schema supports strategy versioning

### Generated Strategy Types
- Moving Average Crossover strategies with parameter variations
- RSI Mean Reversion strategies
- MACD momentum strategies
- Custom parameter combinations through factory system

## Validation Pipeline

### Available Algorithms
1. **CD_MA**: Coincident/Directional Moving Average analysis
2. **BND_RET**: Bond return analysis
3. **BOOT_RATIO**: Bootstrap ratio testing
4. **BOUND_MEAN**: Bounded mean analysis
5. **DEV_MA**: Deviation moving average
6. **SELBIAS**: Selection bias detection
7. **MCPT_TRN**: Monte Carlo permutation test (training)
8. **DRAWDOWN**: Maximum drawdown analysis
9. **MCPT_BARS**: Monte Carlo permutation test (bars)

### Validation Modes
- **Quick**: 30s timeout, basic algorithms
- **Standard**: 480s timeout, comprehensive validation
- **Thorough**: 300s timeout (needs fixing), all algorithms

## Command Reference

### Strategy Execution
```bash
# Run individual strategy
./build/strategy_runner sma data/sample_ohlc.txt --short 5 --long 20 --fee 0.0005 --symbol DEMO

# Batch parameter testing
./build/strategy_batch_tester data/sample_ohlc.txt 50 SMA

# Automated bias remediation
python3 strategys/automated_bias_remediation.py --strategy framework/sma_strategy.cpp --data data/sample_ohlc.txt --iterations 3
```

### Validation Commands
```bash
# StratVal CLI validation
python3 -m stratval.cli.stratval validate framework/sma_strategy.cpp --data data/sample_ohlc.txt --mode standard

# Complete system test
python3 complete_test.py

# Real data validation
python3 test_real_data_validation.py --quick
```

### Build System
```bash
# Full build
cmake -S . -B build && cmake --build build -j

# Test suite
ctest --test-dir build --output-on-failure
```

## Database Connections

### PostgreSQL (Production)
- **Host**: localhost:5432
- **Database**: freqtrade_db
- **User**: freqtrade_user
- **Data**: 420,956 candles across multiple symbols
- **Status**: ✅ Connected and operational

### SQLite (Local)
- **File**: `./freqtrade_db` (60KB)
- **Purpose**: Strategy tracking and automation
- **Tables**: strategies, variants, runs, metrics, artifacts
- **Status**: ✅ Schema created, used for automation pipeline

## File Structure Highlights

### Critical Directories
- `build/`: Compiled executables and test results
- `stratval/`: Python validation framework package
- `framework/`: C++ strategy templates and implementations
- `tools/`: Data processing and automation scripts
- `automation_outputs/`: Generated strategies and remediation results
- `end_to_end_results/`: Comprehensive test outputs with 50+ generated strategies

### Configuration Files
- `stratval/utils/config.py`: Validation timeout and algorithm settings
- `CMakeLists.txt`: Build system configuration
- `setup.py`: Python package configuration

## Recent Findings

### System Strengths
- ✅ Complete build system with 36+ executables
- ✅ Comprehensive validation framework operational
- ✅ Strategy generation system producing diverse strategies
- ✅ Real market data available (420K+ candles)
- ✅ Automated bias remediation working
- ✅ Multiple reporting formats (HTML, JSON, terminal)

### Immediate Priorities
1. **Fix timeout configurations** in validation system
2. **Configure real data usage** as default instead of samples
3. **Resolve PostgreSQL/SQLite data routing** 
4. **Test full end-to-end pipeline** with larger datasets

## Working Examples

Last successful runs:
- Strategy runner: SMA strategy with 0.118% return on 50-bar sample
- Batch tester: 10 SMA configurations tested successfully
- Bias remediation: 2 iterations completed with OOS validation
- Database: Successfully connected to PostgreSQL with 420K+ candles

The system is **fundamentally sound** with **configuration optimization** needed for full utilization of available data assets.