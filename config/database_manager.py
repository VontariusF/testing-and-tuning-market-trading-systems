
#!/usr/bin/env python3
"""
Database Manager for Claude Code Trading System - Fixed Version
Handles real market data access from PostgreSQL and SQLite databases
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import time
import json


class DatabaseManager:
    """Manages database connections and market data queries"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize database manager with configuration"""
        self.config = self._load_config(config_path)
        self.db_connection = None
        self._connect_best_database()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load database configuration"""
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "system_config.py"
        
        try:
            config_globals = {}
            with open(config_path, 'r') as f:
                exec(f.read(), config_globals)
            return config_globals.get('DATABASE_CONFIG', {})
        except Exception as e:
            print(f"Warning: Could not load database config: {e}")
            return {"default_type": "sqlite"}
    
    def _connect_best_database(self) -> bool:
        """Connect to best available database source"""
        db_config = self.config
        default_type = db_config.get('default_type', 'sqlite')
        
        if default_type == 'postgresql':
            if self._connect_postgresql(db_config.get('postgresql', {})):
                return True
        
        if default_type == 'sqlite' or not self.db_connection:
            return self._connect_sqlite(db_config.get('sqlite', {}))
        
        return self.db_connection is not None
    
    def _connect_postgresql(self, pg_config: Dict[str, Any]) -> bool:
        """Connect to PostgreSQL database"""
        try:
            import psycopg2
            print("🔗 Connecting to PostgreSQL database...")
            
            self.db_connection = psycopg2.connect(
                host=pg_config.get('host', 'localhost'),
                port=pg_config.get('port', 5432),
                database=pg_config.get('database', 'freqtrade'),
                user=pg_config.get('user', 'freqtrade'),
                password=pg_config.get('password', 'freqtrade')
            )
            
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
            print("✅ PostgreSQL connection established")
            return True
            
        except Exception as e:
            print(f"⚠️  PostgreSQL connection failed: {e}")
            self.db_connection = None
            return False
    
    def _connect_sqlite(self, sqlite_config: Dict[str, Any]) -> bool:
        """Connect to SQLite database"""
        try:
            import sqlite3
            print("🔗 Connecting to SQLite database...")
            
            db_path = sqlite_config.get('path', 'freqtrade.db')
            self.db_connection = sqlite3.connect(db_path)
            
            print(f"✅ SQLite connection established: {db_path}")
            return True
            
        except Exception as e:
            print(f"⚠️  SQLite connection failed: {e}")
            self.db_connection = None
            return False
    
    def get_candle_count(self, pair: str, timeframe: str) -> int:
        """Get total number of candles available for a pair/timeframe"""
        if not self.db_connection:
            return 0
        
        try:
            cursor = self.db_connection.cursor()
            if 'postgresql' in str(type(self.db_connection)):
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM trades 
                    WHERE pair = %s AND timeframe = %s
                """, (pair, timeframe))
            else:  # SQLite
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM ft_trades 
                    WHERE pair = ? AND timeframe = ?
                """, (pair, timeframe))
            
            count = cursor.fetchone()[0]
            cursor.close()
            print(f"📊 Found {count} candles for {pair} {timeframe}")
            return count
                
        except Exception as e:
            print(f"⚠️  Failed to count candles: {e}")
            return 0


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    return DatabaseManager()
