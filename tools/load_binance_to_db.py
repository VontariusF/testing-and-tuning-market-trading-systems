#!/usr/bin/env python3
"""
Load Binance multi-timeframe data from JSON files into PostgreSQL database.
"""

import json
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
import re

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'freqtrade_db',
    'user': 'freqtrade_user',
    'password': 'Vontarius97$'
}

# Paths to search for Binance data
BINANCE_DATA_PATHS = [
    '/Users/vontariusfalls/strategy_template/user_data/data/binance',
    '/Users/vontariusfalls/strategy_template/user_data/data/binanceus',
    '/Users/vontariusfalls/london-breakout-strategy/user_data/data/binance',
]


def create_table(conn):
    """Create the binance_ohlcv table if it doesn't exist."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS binance_ohlcv (
        id BIGSERIAL PRIMARY KEY,
        exchange VARCHAR(50) NOT NULL,
        symbol VARCHAR(50) NOT NULL,
        timeframe VARCHAR(10) NOT NULL,
        timestamp BIGINT NOT NULL,
        datetime TIMESTAMP NOT NULL,
        open NUMERIC(20, 8) NOT NULL,
        high NUMERIC(20, 8) NOT NULL,
        low NUMERIC(20, 8) NOT NULL,
        close NUMERIC(20, 8) NOT NULL,
        volume NUMERIC(30, 8) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (exchange, symbol, timeframe, timestamp)
    );
    
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_binance_symbol_timeframe 
        ON binance_ohlcv(symbol, timeframe);
    CREATE INDEX IF NOT EXISTS idx_binance_timestamp 
        ON binance_ohlcv(timestamp);
    CREATE INDEX IF NOT EXISTS idx_binance_datetime 
        ON binance_ohlcv(datetime);
    CREATE INDEX IF NOT EXISTS idx_binance_symbol_timeframe_timestamp 
        ON binance_ohlcv(symbol, timeframe, timestamp);
    """
    
    with conn.cursor() as cur:
        cur.execute(create_table_sql)
        conn.commit()
        print("✓ Table 'binance_ohlcv' created/verified")


def parse_filename(filename):
    """
    Extract symbol and timeframe from filename.
    Example: 'ADA_USDT-5m.json' -> ('ADA_USDT', '5m')
    """
    match = re.match(r'([A-Z0-9_]+)-(\w+)\.json', filename)
    if match:
        return match.group(1), match.group(2)
    return None, None


def load_json_file(filepath):
    """Load and parse a JSON file containing OHLCV data."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"✗ Error loading {filepath}: {e}")
        return None


def insert_ohlcv_data(conn, exchange, symbol, timeframe, ohlcv_data):
    """
    Insert OHLCV data into the database.
    Uses ON CONFLICT to handle duplicates.
    """
    if not ohlcv_data:
        return 0
    
    # Prepare data for insertion
    rows = []
    for candle in ohlcv_data:
        timestamp_ms = int(candle[0])
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
        
        rows.append((
            exchange,
            symbol,
            timeframe,
            timestamp_ms,
            dt,
            float(candle[1]),  # open
            float(candle[2]),  # high
            float(candle[3]),  # low
            float(candle[4]),  # close
            float(candle[5]),  # volume
        ))
    
    insert_sql = """
        INSERT INTO binance_ohlcv 
            (exchange, symbol, timeframe, timestamp, datetime, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (exchange, symbol, timeframe, timestamp) 
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    
    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, rows, page_size=1000)
            conn.commit()
        return len(rows)
    except Exception as e:
        print(f"✗ Error inserting data for {symbol}-{timeframe}: {e}")
        conn.rollback()
        return 0


def process_directory(conn, directory_path):
    """Process all JSON files in a directory."""
    path = Path(directory_path)
    
    if not path.exists():
        print(f"⚠ Directory not found: {directory_path}")
        return
    
    # Determine exchange name from path
    if 'binanceus' in str(path):
        exchange = 'binanceus'
    else:
        exchange = 'binance'
    
    print(f"\n📂 Processing directory: {directory_path}")
    print(f"   Exchange: {exchange}")
    
    json_files = list(path.glob('*.json'))
    
    if not json_files:
        print(f"   No JSON files found")
        return
    
    print(f"   Found {len(json_files)} JSON file(s)")
    
    total_rows = 0
    successful_files = 0
    
    for json_file in json_files:
        symbol, timeframe = parse_filename(json_file.name)
        
        if not symbol or not timeframe:
            print(f"   ⚠ Skipping {json_file.name} (could not parse filename)")
            continue
        
        print(f"   Loading {json_file.name}...", end=' ')
        
        data = load_json_file(json_file)
        if data is None:
            continue
        
        rows_inserted = insert_ohlcv_data(conn, exchange, symbol, timeframe, data)
        total_rows += rows_inserted
        successful_files += 1
        
        print(f"✓ {rows_inserted:,} candles")
    
    print(f"\n   Summary: {successful_files}/{len(json_files)} files processed, {total_rows:,} total candles")


def get_table_stats(conn):
    """Get statistics about the loaded data."""
    stats_sql = """
    SELECT 
        exchange,
        symbol,
        timeframe,
        COUNT(*) as candle_count,
        MIN(datetime) as first_candle,
        MAX(datetime) as last_candle
    FROM binance_ohlcv
    GROUP BY exchange, symbol, timeframe
    ORDER BY exchange, symbol, timeframe;
    """
    
    with conn.cursor() as cur:
        cur.execute(stats_sql)
        results = cur.fetchall()
    
    return results


def main():
    """Main function to orchestrate the data loading."""
    print("=" * 80)
    print("Binance Data Loader")
    print("=" * 80)
    
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
        
        # Process all directories
        for data_path in BINANCE_DATA_PATHS:
            process_directory(conn, data_path)
        
        # Display statistics
        print("\n" + "=" * 80)
        print("📊 Database Statistics")
        print("=" * 80)
        
        stats = get_table_stats(conn)
        
        if stats:
            print(f"\n{'Exchange':<12} {'Symbol':<15} {'Timeframe':<10} {'Candles':<12} {'First':<20} {'Last':<20}")
            print("-" * 100)
            for row in stats:
                exchange, symbol, timeframe, count, first, last = row
                print(f"{exchange:<12} {symbol:<15} {timeframe:<10} {count:<12,} {str(first):<20} {str(last):<20}")
            
            # Total count
            total_candles = sum(row[3] for row in stats)
            print("-" * 100)
            print(f"Total candles in database: {total_candles:,}")
        else:
            print("\nNo data found in database")
        
    finally:
        conn.close()
        print("\n✓ Database connection closed")
    
    print("\n" + "=" * 80)
    print("✅ Data loading complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()

