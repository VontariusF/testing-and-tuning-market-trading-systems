#!/usr/bin/env python3
"""
Configuration Manager for Claude Code Trading System
Centralized configuration loading and management
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """Manages system configuration from file and environment variables"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        if config_path is None:
            # Default to config/system_config.py in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "system_config.py"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from Python file"""
        try:
            # Execute config file to get configuration variables
            config_globals = {}
            with open(self.config_path, 'r') as f:
                exec(f.read(), config_globals)
            
            return {
                'database': config_globals.get('DATABASE_CONFIG', {}),
                'data': config_globals.get('DATA_CONFIG', {}),
                'timeouts': config_globals.get('TIMEOUT_CONFIG', {}),
                'market': config_globals.get('MARKET_DATA_CONFIG', {}),
                'agents': config_globals.get('AGENT_CONFIG', {}),
                'performance': config_globals.get('PERFORMANCE_CONFIG', {})
            }
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if file not found"""
        return {
            'database': {
                'default_type': 'sqlite',
                'sqlite': {'path': 'freqtrade.db'}
            },
            'data': {
                'default_source': 'file',
                'sources': {
                    'file': {'path': 'binance_BTC_USDT_1h.txt'}
                }
            },
            'timeouts': {
                'standard': {
                    'cd_ma': 480,
                    'drawdown': 480,
                    'mcpt_bars': 480,
                    'mcpt_trn': 480,
                    'selbias': 480
                }
            }
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config['database']
    
    def get_data_config(self) -> Dict[str, Any]:
        """Get data source configuration"""
        return self.config['data']
    
    def get_timeout_config(self, mode: str = 'standard') -> Dict[str, Any]:
        """Get timeout configuration for specific mode"""
        timeouts = self.config['timeouts']
        return timeouts.get(mode, timeouts.get('custom', {'default_timeout': 600}))
    
    def get_market_config(self) -> Dict[str, Any]:
        """Get market data configuration"""
        return self.config['market']
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration"""
        return self.config['agents']
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.config['performance']
    
    def is_database_available(self, db_type: str) -> bool:
        """Check if specific database type is available"""
        if db_type == 'postgresql':
            try:
                import psycopg2
                return True
            except ImportError:
                return False
        elif db_type == 'sqlite':
            try:
                import sqlite3
                return True
            except ImportError:
                return False
        return False
    
    def get_best_data_source(self) -> Dict[str, Any]:
        """Get best available data source"""
        data_config = self.get_data_config()
        default_source = data_config.get('default_source', 'file')
        
        if default_source == 'database':
            # Check if database is available
            db_config = self.get_database_config()
            db_type = db_config.get('default_type', 'sqlite')
            
            if self.is_database_available(db_type):
                return data_config['sources']['database']
            else:
                # Fallback to file
                return data_config['sources']['file']
        
        return data_config['sources'].get(default_source, data_config['sources']['file'])


# Global configuration instance
_config_manager = None

def get_config() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return get_config().get_database_config()


def get_data_config() -> Dict[str, Any]:
    """Get data source configuration"""
    return get_config().get_data_config()


def get_timeout_config(mode: str = 'standard') -> Dict[str, Any]:
    """Get timeout configuration"""
    return get_config().get_timeout_config(mode)


def get_market_config() -> Dict[str, Any]:
    """Get market data configuration"""
    return get_config().get_market_config()


def get_agent_config() -> Dict[str, Any]:
    """Get agent configuration"""
    return get_config().get_agent_config()
