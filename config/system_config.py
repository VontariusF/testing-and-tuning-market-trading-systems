# Claude Code Trading System Configuration

# Database Configuration
DATABASE_CONFIG = {
    "default_type": "postgresql",  # Use PostgreSQL by default
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "freqtrade",
        "user": "freqtrade",
        "password": "freqtrade"
    },
    "sqlite": {
        "path": "freqtrade.db"
    }
}

# Data Source Configuration
DATA_CONFIG = {
    "default_source": "database",  # Use real database data by default
    "sources": {
        "database": {
            "type": "postgresql",
            "min_candles": 10000,  # Use substantial data samples
            "prefer_real_data": True
        },
        "file": {
            "path": "binance_BTC_USDT_1h.txt",
            "min_candles": 50000
        }
    }
}

# Algorithm Timeout Configuration
TIMEOUT_CONFIG = {
    "standard": {
        "cd_ma": 480,
        "drawdown": 480,
        "mcpt_bars": 480,
        "mcpt_trn": 480,
        "selbias": 480
    },
    "thorough": {
        "cd_ma": 300,
        "drawdown": 300,
        "mcpt_bars": 300,
        "mcpt_trn": 300,
        "selbias": 300
    },
    "custom": {
        "default_timeout": 600  # Default for unspecified algorithms
    }
}

# Market Data Configuration
MARKET_DATA_CONFIG = {
    "default_pairs": ["BTC/USDT"],
    "default_timeframes": ["1h"],
    "default_date_range": {
        "start_date": "2020-01-01",
        "end_date": "2023-12-31"
    },
    "data_requirements": {
        "min_candles_per_analysis": 10000,  # Minimum candles for reliable analysis
        "prefer_long_history": True
    }
}

# Claude Agent Configuration
AGENT_CONFIG = {
    "workflow_settings": {
        "default_experiments": 10,
        "max_concurrent_runs": 3,
        "auto_retry_failed": True,
        "retry_attempts": 3
    },
    "reporting": {
        "default_format": "html",
        "include_all_sections": True,
        "auto_generate_summary": True
    }
}

# System Performance Configuration
PERFORMANCE_CONFIG = {
    "resource_limits": {
        "max_memory_mb": 4096,
        "max_cpu_percent": 80,
        "io_timeout": 300
    },
    "optimization": {
        "use_parallel_processing": True,
        "batch_size": 100,
        "cache_results": True
    }
}
