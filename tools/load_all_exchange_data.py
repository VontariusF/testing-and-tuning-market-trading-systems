#!/usr/bin/env python3
"""
Comprehensive loader for all exchange data (JSON and Feather formats).
Supports: Binance, BinanceUS, Bybit, Coinbase, Hyperliquid
"""

import json
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
import re
import sys

# Try importing pyarrow and pandas for feather support
try:
    import pyarrow.feather as feather
    import pandas as pd
    FEATHER_SUPPORT = True
except ImportError:
    print("⚠ Warning: pyarrow or pandas not installed. Feather files will be skipped.")
    print("  Install with: pip install pyarrow pandas")
    FEATHER_SUPPORT = False

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'freqtrade_db',
    'user': 'freqtrade_user',
    'password': 'Vontarius97$'
}

# Root directories to search recursively
# First check current directory and common data locations
SEARCH_ROOTS = [
    '.',  # Current directory (repository root)
    './data',  # Local data directory
    '../data',  # Parent data directory
    '/Users/vontariusfalls/strategy_template',
    '/Users/vontariusfalls/london-breakout-strategy',
    '/Users/vontariusfalls/freqtrade-ai-project',
    '/Users/vontariusfalls/FreqAI-Training',
]


def create_table(conn):
    """Create the exchange_ohlcv table if it doesn't exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS exchange_ohlcv (
        id BIGSERIAL PRIMARY KEY,
        exchange VARCHAR(50) NOT NULL,
        symbol VARCHAR(50) NOT NULL,
        timeframe VARCHAR(10) NOT NULL,
        data_type VARCHAR(20) DEFAULT 'spot',
        timestamp BIGINT NOT NULL,
        datetime TIMESTAMP NOT NULL,
        open NUMERIC(20, 8) NOT NULL,
        high NUMERIC(20, 8) NOT NULL,
        low NUMERIC(20, 8) NOT NULL,
        close NUMERIC(20, 8) NOT NULL,
        volume NUMERIC(30, 8) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (exchange, symbol, timeframe, data_type, timestamp)
    );
    
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_exchange_symbol_timeframe 
        ON exchange_ohlcv(symbol, timeframe);
    CREATE INDEX IF NOT EXISTS idx_exchange_timestamp 
        ON exchange_ohlcv(timestamp);
    CREATE INDEX IF NOT EXISTS idx_exchange_datetime 
        ON exchange_ohlcv(datetime);
    CREATE INDEX IF NOT EXISTS idx_exchange_symbol_timeframe_timestamp 
        ON exchange_ohlcv(exchange, symbol, timeframe, timestamp);
    CREATE INDEX IF NOT EXISTS idx_exchange_data_type
        ON exchange_ohlcv(data_type);
    """
    
    with conn.cursor() as cur:
        cur.execute(create_table_sql)
        conn.commit()
        print("✓ Table 'exchange_ohlcv' created/verified")


def parse_filename(filename, parent_dir):
    """
    Extract symbol, timeframe, and data_type from filename and path.
    Examples:
      'ADA_USDT-5m.json' -> ('ADA_USDT', '5m', 'spot')
      'BTC_USDT_USDT-5m-futures.feather' -> ('BTC_USDT', '5m', 'futures')
      'BTC_USD-1h.feather' -> ('BTC_USD', '1h', 'spot')
    """
    # Check if futures directory or filename contains 'futures'
    is_futures = 'futures' in parent_dir or 'futures' in filename.lower()
    is_mark = 'mark' in filename.lower()
    is_funding = 'funding' in filename.lower()
    
    # Determine data type
    if is_funding:
        data_type = 'funding_rate'
    elif is_mark:
        data_type = 'mark'
    elif is_futures:
        data_type = 'futures'
    else:
        data_type = 'spot'
    
    # Remove extension
    name = filename.replace('.json', '').replace('.feather', '')
    
    # Remove data type suffixes
    name = re.sub(r'-(futures|mark|funding_rate)$', '', name)
    
    # Parse: SYMBOL-TIMEFRAME or SYMBOL_TIMEFRAME format
    # Handle patterns like: BTC_USDT_USDT-5m or BTC_USDT-5m or BTC_USD-1h
    match = re.match(r'([A-Z0-9_]+?)[-_](\d+[a-z]+)$', name, re.IGNORECASE)
    if match:
        symbol = match.group(1)
        timeframe = match.group(2).lower()
        
        # Normalize symbol (some have double USDT like BTC_USDT_USDT)
        if symbol.endswith('_USDT_USDT'):
            symbol = symbol.replace('_USDT_USDT', '_USDT')
        elif symbol.endswith('_USDC_USDC'):
            symbol = symbol.replace('_USDC_USDC', '_USDC')
            
        return symbol, timeframe, data_type
    
    return None, None, None


def get_exchange_from_path(filepath):
    """Extract exchange name from file path."""
    path_lower = filepath.lower()
    
    if 'binanceus' in path_lower:
        return 'binanceus'
    elif 'binance' in path_lower:
        return 'binance'
    elif 'bybit' in path_lower:
        return 'bybit'
    elif 'coinbaseexchange' in path_lower:
        return 'coinbaseexchange'
    elif 'coinbase' in path_lower:
        return 'coinbase'
    elif 'hyperliquid' in path_lower:
        return 'hyperliquid'
    
    return 'unknown'


def load_json_file(filepath):
    """Load and parse a JSON file containing OHLCV data."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        else:
            return None
    except Exception as e:
        print(f"      ✗ Error loading JSON: {e}")
        return None


def load_feather_file(filepath):
    """Load and parse a Feather file containing OHLCV data."""
    if not FEATHER_SUPPORT:
        return None
    
    try:
        df = feather.read_feather(filepath)
        
        # Check if index looks like timestamps
        index_is_timestamp = False
        if df.index.name in ['date', 'timestamp', 'time'] or str(df.index.dtype).startswith('datetime'):
            index_is_timestamp = True
        
        # Convert to list of lists format: [timestamp, open, high, low, close, volume]
        # Determine column names (may vary)
        col_map = {}
        
        # Check index for timestamp
        if index_is_timestamp:
            col_map['timestamp'] = '__index__'
        
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ['date', 'timestamp', 'time'] and 'timestamp' not in col_map:
                col_map['timestamp'] = col
            elif col_lower == 'open':
                col_map['open'] = col
            elif col_lower == 'high':
                col_map['high'] = col
            elif col_lower == 'low':
                col_map['low'] = col
            elif col_lower == 'close':
                col_map['close'] = col
            elif col_lower in ['volume', 'vol']:
                col_map['volume'] = col
        
        # Verify we have required columns
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(k in col_map for k in required):
            # Try alternative: if we don't have volume, set it to 0
            if 'volume' not in col_map:
                col_map['volume'] = None
            
            # Check again
            if not all(k in col_map or col_map.get(k) is None for k in required if k != 'volume'):
                return None
        
        # Convert to list format
        data = []
        for idx, row in df.iterrows():
            try:
                # Get timestamp from index or column
                if col_map['timestamp'] == '__index__':
                    timestamp = idx
                else:
                    timestamp = row[col_map['timestamp']]
                
                # Convert timestamp to milliseconds if needed
                if hasattr(timestamp, 'timestamp'):
                    # It's a pandas Timestamp or datetime
                    timestamp = int(timestamp.timestamp() * 1000)
                elif isinstance(timestamp, (int, float)):
                    # If timestamp is in seconds, convert to milliseconds
                    if timestamp < 1e12:
                        timestamp = int(timestamp * 1000)
                    else:
                        timestamp = int(timestamp)
                else:
                    # Try to parse as datetime string
                    dt = pd.to_datetime(timestamp)
                    timestamp = int(dt.timestamp() * 1000)
                
                # Get volume (may be None)
                if col_map['volume'] is None:
                    volume = 0.0
                else:
                    vol_val = row[col_map['volume']]
                    volume = float(vol_val) if vol_val is not None and not pd.isna(vol_val) else 0.0
                
                data.append([
                    timestamp,
                    float(row[col_map['open']]),
                    float(row[col_map['high']]),
                    float(row[col_map['low']]),
                    float(row[col_map['close']]),
                    volume
                ])
            except Exception as e:
                # Skip bad rows
                continue
        
        return data if data else None
    except Exception as e:
        print(f"      ✗ Error loading Feather: {e}")
        return None


def insert_ohlcv_data(conn, exchange, symbol, timeframe, data_type, ohlcv_data):
    """
    Insert OHLCV data into the database.
    Uses ON CONFLICT to handle duplicates.
    """
    if not ohlcv_data:
        return 0

    # Prepare data for insertion and deduplicate
    rows = []
    seen_timestamps = set()

    for candle in ohlcv_data:
        try:
            timestamp_ms = int(candle[0])

            # Skip duplicate timestamps within the same file
            if timestamp_ms in seen_timestamps:
                continue
            seen_timestamps.add(timestamp_ms)

            dt = datetime.fromtimestamp(timestamp_ms / 1000.0)

            rows.append((
                exchange,
                symbol,
                timeframe,
                data_type,
                timestamp_ms,
                dt,
                float(candle[1]),  # open
                float(candle[2]),  # high
                float(candle[3]),  # low
                float(candle[4]),  # close
                float(candle[5]) if len(candle) > 5 else 0.0,  # volume
            ))
        except (ValueError, IndexError, TypeError) as e:
            continue  # Skip bad rows

    if not rows:
        return 0

    # Use INSERT ... ON CONFLICT ... DO NOTHING for better performance
    # and avoid the "cannot affect row a second time" error
    insert_sql = """
        INSERT INTO exchange_ohlcv
            (exchange, symbol, timeframe, data_type, timestamp, datetime, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (exchange, symbol, timeframe, data_type, timestamp)
        DO NOTHING
    """

    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows, page_size=1000)
            conn.commit()
        return len(rows)
    except Exception as e:
        print(f"      ✗ Error inserting data: {e}")
        conn.rollback()
        return 0


def find_all_data_files():
    """Recursively find all trading data files."""
    files = []

    for root_dir in SEARCH_ROOTS:
        root_path = Path(root_dir)
        if not root_path.exists():
            continue

        # Find all JSON and feather files
        for filepath in root_path.rglob('*'):
            if not filepath.is_file():
                continue

            # Check file extension
            if filepath.suffix not in ['.json', '.feather']:
                continue

            # Skip known non-data files
            skip_patterns = [
                'leverage_tier', 'moonward', 'config', 'settings', 'params',
                'validation', 'results', 'report', 'metadata', 'state',
                'hypotheses', 'escalation', 'investigation', 'review',
                'optimization', 'architect', 'analyst', 'coder', 'reviewer',
                'guardian', 'investigator', 'patcher', 'optimizer', 'current',
                'specification', 'learnings', 'failure', 'metrics', 'summary',
                'backtest-result', 'pair_dictionary', 'run_params'
            ]

            if any(skip in filepath.name.lower() for skip in skip_patterns):
                continue

            # Only include files that look like OHLCV data
            # Should contain exchange names and trading pairs
            filename_lower = filepath.name.lower()
            has_exchange = any(exc in filename_lower for exc in ['binance', 'bybit', 'coinbase', 'hyperliquid'])
            has_pair = any(pair in filename_lower for pair in ['usdt', 'usd', 'btc', 'eth', 'ada', 'sol', 'bnb', 'avax', 'dot', 'doge', 'xrp'])

            if has_exchange or has_pair or 'data' in str(filepath).lower():
                files.append(filepath)

    return files


def main():
    """Main function to orchestrate the data loading."""
    print("=" * 100)
    print("Comprehensive Exchange Data Loader")
    print("=" * 100)
    print(f"\nSupported formats: JSON{', Feather' if FEATHER_SUPPORT else ''}")
    print(f"Supported exchanges: Binance, BinanceUS, Bybit, Coinbase, Hyperliquid")
    
    # Find all files
    print("\n🔍 Scanning for trading data files...")
    all_files = find_all_data_files()
    print(f"   Found {len(all_files)} files")
    
    if not all_files:
        print("\n✗ No data files found!")
        return
    
    # Connect to database
    print("\n🔌 Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✓ Connected successfully")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    try:
        # Create table
        create_table(conn)
        
        # Process all files
        print(f"\n📊 Processing {len(all_files)} files...")
        print("-" * 100)
        
        total_rows = 0
        successful_files = 0
        failed_files = 0
        
        for i, filepath in enumerate(all_files, 1):
            # Parse file info
            exchange = get_exchange_from_path(str(filepath))
            parent_dir = str(filepath.parent)
            symbol, timeframe, data_type = parse_filename(filepath.name, parent_dir)
            
            if not symbol or not timeframe:
                print(f"{i:4d}/{len(all_files)} ⚠ Skipping {filepath.name} (could not parse)")
                failed_files += 1
                continue
            
            # Load data
            if filepath.suffix == '.json':
                data = load_json_file(filepath)
            elif filepath.suffix == '.feather':
                data = load_feather_file(filepath)
            else:
                data = None
            
            if data is None:
                print(f"{i:4d}/{len(all_files)} ✗ Failed: {exchange}/{symbol}-{timeframe} ({data_type})")
                failed_files += 1
                continue
            
            # Insert into database
            rows_inserted = insert_ohlcv_data(conn, exchange, symbol, timeframe, data_type, data)
            
            if rows_inserted > 0:
                total_rows += rows_inserted
                successful_files += 1
                print(f"{i:4d}/{len(all_files)} ✓ {exchange:15s} {symbol:15s} {timeframe:5s} {data_type:12s} {rows_inserted:8,} candles")
            else:
                print(f"{i:4d}/{len(all_files)} ✗ Failed: {exchange}/{symbol}-{timeframe} ({data_type})")
                failed_files += 1
        
        print("-" * 100)
        print(f"\n📈 Summary:")
        print(f"   Successful: {successful_files}/{len(all_files)} files")
        print(f"   Failed:     {failed_files}/{len(all_files)} files")
        print(f"   Total rows: {total_rows:,} candles inserted/updated")
        
        # Display database statistics
        print("\n" + "=" * 100)
        print("📊 Database Statistics by Exchange")
        print("=" * 100)
        
        stats_sql = """
        SELECT 
            exchange,
            COUNT(DISTINCT symbol) as symbols,
            COUNT(DISTINCT timeframe) as timeframes,
            COUNT(DISTINCT data_type) as data_types,
            COUNT(*) as total_candles,
            MIN(datetime) as first_candle,
            MAX(datetime) as last_candle
        FROM exchange_ohlcv
        GROUP BY exchange
        ORDER BY exchange;
        """
        
        with conn.cursor() as cur:
            cur.execute(stats_sql)
            results = cur.fetchall()
        
        if results:
            print(f"\n{'Exchange':<20} {'Symbols':<10} {'Timeframes':<12} {'Types':<8} {'Candles':<15} {'First':<20} {'Last':<20}")
            print("-" * 120)
            for row in results:
                exchange, symbols, timeframes, types, candles, first, last = row
                print(f"{exchange:<20} {symbols:<10} {timeframes:<12} {types:<8} {candles:<15,} {str(first):<20} {str(last):<20}")
            
            total_candles = sum(row[4] for row in results)
            print("-" * 120)
            print(f"{'TOTAL':<20} {'':<10} {'':<12} {'':<8} {total_candles:<15,}")
        
    finally:
        conn.close()
        print("\n✓ Database connection closed")
    
    print("\n" + "=" * 100)
    print("✅ Data loading complete!")
    print("=" * 100)


if __name__ == '__main__':
    main()
