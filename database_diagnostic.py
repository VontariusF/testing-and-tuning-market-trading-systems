#!/usr/bin/env python3
"""
Database diagnostic tool for FreqTrade integration
"""

import sys
import json
from pathlib import Path

# Add stratval package to path
sys.path.insert(0, str(Path(__file__).parent / 'stratval'))

def diagnose_database():
    """Diagnose FreqTrade database structure and connectivity"""
    print("🔍 FreqTrade Database Diagnostic Tool")
    print("=" * 50)

    try:
        from stratval.utils.database import FreqTradeDB

        # Your actual database connection string
        db_connection_string = "postgresql://freqtrade_user:Vontarius97$@localhost:5432/freqtrade_db"

        print(f"🔌 Testing connection to: {db_connection_string.replace('Vontarius97$', '***')}")

        # Create database instance
        db = FreqTradeDB(db_connection_string)

        # Test 1: Basic Connection
        print("\n1. Testing database connection...")
        if db.connect():
            print("   ✅ Database connection successful")
        else:
            print("   ❌ Database connection failed")
            return False

        # Test 2: Discover Table Structure
        print("\n2. Discovering table structure...")
        structure = db.discover_table_structure()

        if structure:
            print("   ✅ Found relevant tables:")
            for table_name, info in structure.items():
                print(f"     📊 {table_name}:")
                for col in info['columns']:
                    print(f"        - {col['name']} ({col['type']}) {'NULL' if col['nullable'] == 'YES' else 'NOT NULL'}")
        else:
            print("   ⚠️  No relevant tables found")

        # Test 3: Test Table Queries
        print("\n3. Testing table queries...")
        test_pairs = ["BTC/USDT", "ETH/USDT", "BTC_USDT"]
        test_timeframes = ["1h", "4h", "1d"]

        for pair in test_pairs:
            for timeframe in test_timeframes:
                print(f"   🔍 Testing {pair} {timeframe}...")
                if db.test_table_query("ohlcv", pair, timeframe):
                    print(f"      ✅ Found data for {pair} {timeframe}")
                else:
                    print(f"      ❌ No data found for {pair} {timeframe}")

        # Test 4: Available Pairs
        print("\n4. Finding available pairs...")
        pairs = db.get_available_pairs()
        if pairs:
            print(f"   ✅ Found {len(pairs)} trading pairs:")
            for pair in pairs[:10]:  # Show first 10
                print(f"      📈 {pair}")
            if len(pairs) > 10:
                print(f"      ... and {len(pairs) - 10} more")
        else:
            print("   ❌ No trading pairs found")

        # Test 4b: Comprehensive Data Discovery
        print("\n5. Discovering all available data...")
        all_data = db.discover_all_data()
        if all_data:
            print("   ✅ Comprehensive data discovery:")
            for pair, info in all_data.items():
                print(f"     📊 {pair}:")
                for tf, details in info['timeframes'].items():
                    count = details['count']
                    start_date = details['date_range']['start']
                    end_date = details['date_range']['end']
                    print(f"        ⏱️  {tf}: {count} candles ({start_date} to {end_date})")
        else:
            print("   ⚠️  No comprehensive data found")

        # Test 5: Sample Data Fetch
        print("\n5. Testing data fetch...")
        try:
            sample_data = db.fetch_ohlcv("BTC/USDT", "1h", limit=10)
            if sample_data:
                print(f"   ✅ Successfully fetched {len(sample_data)} sample candles")
                print("      Sample data:")
                print(f"      First candle: {sample_data[0]}")
                print(f"      Last candle: {sample_data[-1]}")
            else:
                print("   ❌ No sample data fetched")
        except Exception as e:
            print(f"   ❌ Error fetching sample data: {e}")

        # Cleanup
        db.disconnect()
        print("\n✅ Database diagnostic completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Database diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = diagnose_database()
    print(f"\n{'🎉 DATABASE DIAGNOSTIC COMPLETED!' if success else '❌ DATABASE DIAGNOSTIC FAILED!'}")
    sys.exit(0 if success else 1)
