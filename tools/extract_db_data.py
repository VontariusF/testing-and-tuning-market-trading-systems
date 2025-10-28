#!/usr/bin/env python3
"""
Extract market data from PostgreSQL database for strategy testing
"""

import psycopg2
import sys
from datetime import datetime
import os

# Database connection parameters
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'freqtrade_db',
    'user': 'freqtrade_user',
    'password': 'Vontarius97$'
}

def extract_market_data(exchange: str, symbol: str, timeframe: str, limit: int = 100000) -> str:
    """Extract market data from database and format for strategy tester"""

    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query data
        query = """
        SELECT timestamp, open, high, low, close
        FROM exchange_ohlcv
        WHERE exchange = %s AND symbol = %s AND timeframe = %s
        ORDER BY timestamp ASC
        LIMIT %s
        """

        cursor.execute(query, (exchange, symbol, timeframe, limit))
        rows = cursor.fetchall()

        if not rows:
            print(f"No data found for {exchange}/{symbol}/{timeframe}")
            return ""

        # Convert to strategy tester format: YYYYMMDD Open High Low Close
        lines = []
        for timestamp, open_price, high_price, low_price, close_price in rows:
            # Convert timestamp to YYYYMMDD
            dt = datetime.fromtimestamp(timestamp / 1000)
            date_int = dt.year * 10000 + dt.month * 100 + dt.day

            line = "{:08d} {:.6f} {:.6f} {:.6f} {:.6f}".format(
                date_int, open_price, high_price, low_price, close_price
            )
            lines.append(line)

        print(f"Extracted {len(lines)} bars for {exchange}/{symbol}/{timeframe}")
        return "\n".join(lines) + "\n"

    except Exception as e:
        print(f"Error extracting data: {e}")
        return ""

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    """Main function"""
    if len(sys.argv) < 4:
        print("Usage: python3 extract_db_data.py <exchange> <symbol> <timeframe> [limit]")
        print("Example: python3 extract_db_data.py binance BTC_USDT 1h 50000")
        print("\nAvailable exchanges/symbols:")
        print("  binance: BTC_USDT, ETH_USDT, ADA_USDT, SOL_USDT, BNB_USDT, AVAX_USDT, DOT_USDT, DOGE_USDT, XRP_USDT, LINK_USDT")
        print("  bybit: BTC_USDT, ETH_USDT, ADA_USDT, SOL_USDT, BNB_USDT, AVAX_USDT, DOT_USDT, DOGE_USDT, XRP_USDT")
        return 1

    exchange = sys.argv[1]
    symbol = sys.argv[2]
    timeframe = sys.argv[3]
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 100000

    output_file = f"{exchange}_{symbol}_{timeframe}.txt"

    data = extract_market_data(exchange, symbol, timeframe, limit)

    if data:
        with open(output_file, 'w') as f:
            f.write(data)
        print(f"Data saved to {output_file}")

        # Also copy to market_data.txt for easy testing
        with open('market_data.txt', 'w') as f:
            f.write(data)
        print("Also saved as market_data.txt for strategy testing")

        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())
