"""
Database utilities for FreqTrade integration
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FreqTradeDB:
    """FreqTrade PostgreSQL database interface"""

    def __init__(self, connection_string: str):
        """
        Initialize FreqTrade DB connection
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.connection = None

    def connect(self) -> bool:
        """Connect to FreqTrade database"""
        try:
            self.connection = psycopg2.connect(self.connection_string)
            # Set connection to autocommit mode to avoid transaction issues
            self.connection.autocommit = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_connection(self):
        """Get active database connection"""
        if not self.connection or self.connection.closed:
            self.connect()
        return self.connection

    def fetch_ohlcv(self, pair: str = "BTC/USDT", timeframe: str = "1h", limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data from FreqTrade database

        Args:
            pair: Trading pair (e.g., "BTC/USDT")
            timeframe: Timeframe (e.g., "1h", "4h", "1d")
            limit: Number of candles to fetch (default: 1000)

        Returns:
            List of OHLCV dictionaries
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Convert pair to symbol format
                symbol = pair.replace('/', '_')  # Convert BTC/USDT to BTC_USDT format

                # Determine optimal limit based on timeframe for drawdown analysis
                # For drawdown, we need at least 1 year of data
                if timeframe == "1h":
                    # 1 year of hourly data = ~8760 candles
                    optimal_limit = min(limit, 8760)
                elif timeframe == "4h":
                    # 1 year of 4h data = ~2190 candles
                    optimal_limit = min(limit, 2190)
                elif timeframe == "1d":
                    # 1 year of daily data = ~365 candles
                    optimal_limit = min(limit, 365)
                else:
                    optimal_limit = min(limit, 2000)  # Default for other timeframes

                # Query the exchange_ohlcv table with real data
                query = """
                SELECT timestamp, open, high, low, close, volume
                FROM exchange_ohlcv
                WHERE exchange = 'binance' AND symbol = %s AND timeframe = %s
                ORDER BY timestamp ASC
                LIMIT %s
                """

                try:
                    cursor.execute(query, (symbol, timeframe, optimal_limit))
                    rows = cursor.fetchall()
                    if not rows:
                        logger.error(f"No data found for {pair} {timeframe} in exchange_ohlcv table")
                        return []
                except Exception as e:
                    logger.error(f"Query failed for {pair} {timeframe}: {e}")
                    return []

                # Convert to standard format (reverse to chronological order)
                ohlcv = []
                for row in reversed(rows):
                    try:
                        # Handle timestamp conversion safely
                        timestamp_ms = row['timestamp']
                        if isinstance(timestamp_ms, str):
                            timestamp_ms = int(timestamp_ms)
                        timestamp_sec = timestamp_ms // 1000

                        ohlcv.append({
                            'timestamp': timestamp_sec,
                            'open': float(row['open']) if row['open'] else 0.0,
                            'high': float(row['high']) if row['high'] else 0.0,
                            'low': float(row['low']) if row['low'] else 0.0,
                            'close': float(row['close']) if row['close'] else 0.0,
                            'volume': float(row['volume']) if row['volume'] else 0.0
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error converting row data: {e}")
                        continue

                logger.info(f"Successfully fetched and converted {len(ohlcv)} candles for {pair} {timeframe}")
                return ohlcv

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            return []

    def fetch_trades(self, pair: str = "BTC/USDT", limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch trade data from FreqTrade database
        
        Args:
            pair: Trading pair
            limit: Number of trades to fetch
        
        Returns:
            List of trade dictionaries
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return []

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                query = """
                SELECT timestamp, pair, amount, open_rate, close_rate, side, fee, fee_currency
                FROM trades 
                WHERE pair = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """
                
                cursor.execute(query, (pair, limit))
                trades = cursor.fetchall()
                
                formatted_trades = []
                for trade in reversed(trades):
                    formatted_trades.append({
                        'timestamp': trade['timestamp'],
                        'pair': trade['pair'],
                        'amount': float(trade['amount']),
                        'price': float(trade['close_rate']),
                        'side': trade['side'],
                        'fee': float(trade['fee']),
                        'fee_currency': trade['fee_currency']
                    })
                
                logger.info(f"Fetched {len(formatted_trades)} trades for {pair}")
                return formatted_trades
                
        except Exception as e:
            logger.error(f"Failed to fetch trade data: {e}")
            return []

    def get_available_pairs(self) -> List[str]:
        """
        Get list of available trading pairs in the database

        Returns:
            List of available pair symbols
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return []

        try:
            with self.connection.cursor() as cursor:
                # Try multiple table formats and combine results
                all_pairs = set()
                table_attempts = [
                    "SELECT DISTINCT symbol FROM binance_ohlcv ORDER BY symbol",
                    "SELECT DISTINCT symbol FROM exchange_ohlcv ORDER BY symbol",
                    "SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol"
                ]

                for query in table_attempts:
                    try:
                        cursor.execute(query)
                        pairs = [row[0] for row in cursor.fetchall()]
                        all_pairs.update(pairs)
                    except Exception as e:
                        logger.warning(f"Query failed: {e}")
                        continue

                pairs_list = sorted(list(all_pairs))
                logger.info(f"Found {len(pairs_list)} total pairs across all tables")
                return pairs_list

        except Exception as e:
            logger.error(f"Failed to fetch available pairs: {e}")
            return []

    def get_available_timeframes(self, pair: str = "BTC/USDT") -> List[str]:
        """
        Get list of available timeframes for a pair

        Args:
            pair: Trading pair

        Returns:
            List of available timeframes
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return []

        try:
            with self.connection.cursor() as cursor:
                symbol = pair.replace('/', '_')  # Convert BTC/USDT to BTC_USDT format
                query = "SELECT DISTINCT timeframe FROM ohlcv WHERE symbol = %s ORDER BY timeframe"
                cursor.execute(query, (symbol,))
                timeframes = [row[0] for row in cursor.fetchall()]
                return timeframes

        except Exception as e:
            logger.error(f"Failed to fetch available timeframes: {e}")
            return []

    def discover_table_structure(self) -> Dict[str, Any]:
        """
        Discover available tables and their structures in the database

        Returns:
            Dictionary with table information
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return {}

        try:
            with self.connection.cursor() as cursor:
                # Get all table names
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]

                structure = {}
                for table in tables:
                    if 'ohlc' in table.lower() or 'trade' in table.lower():
                        # Get column information for relevant tables
                        cursor.execute("""
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        columns = cursor.fetchall()
                        structure[table] = {
                            'columns': [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns]
                        }

                return structure

        except Exception as e:
            logger.error(f"Failed to discover table structure: {e}")
            return {}

    def test_table_query(self, table_name: str, pair: str = "BTC/USDT", timeframe: str = "1h") -> bool:
        """
        Test if a specific table has the expected data

        Args:
            table_name: Name of table to test
            pair: Trading pair to look for
            timeframe: Timeframe to look for

        Returns:
            True if table contains expected data
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            return False

        try:
            with self.connection.cursor() as cursor:
                symbol = pair.replace('/', '_')

                # Try different query patterns
                queries = [
                    f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s AND timeframe = %s LIMIT 1",
                    f"SELECT COUNT(*) FROM {table_name} WHERE pair = %s AND timeframe = %s LIMIT 1",
                    f"SELECT COUNT(*) FROM {table_name} WHERE symbol = %s LIMIT 1",
                ]

                for query in queries:
                    try:
                        cursor.execute(query, (symbol, timeframe))
                        count = cursor.fetchone()[0]
                        if count > 0:
                            logger.info(f"Table {table_name} has {count} matching records")
                            return True
                    except Exception:
                        continue

                return False

        except Exception as e:
            logger.error(f"Failed to test table {table_name}: {e}")
            return False

    def discover_all_data(self) -> Dict[str, Any]:
        """
        Discover all available data in the database

        Returns:
            Comprehensive data availability report
        """
        if not self.connection:
            self.connect()

        if not self.connection:
            logger.error("Database connection failed")
            return {}

        try:
            with self.connection.cursor() as cursor:
                # Get all pairs and their available timeframes
                all_pairs = self.get_available_pairs()
                data_summary = {}

                for pair in all_pairs:
                    pair_info = {'timeframes': {}}

                    # Check each timeframe
                    timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
                    for tf in timeframes:
                        try:
                            # Test if data exists for this pair/timeframe
                            test_query = """
                            SELECT COUNT(*) FROM binance_ohlcv
                            WHERE symbol = %s AND timeframe = %s
                            LIMIT 1
                            """
                            cursor.execute(test_query, (pair, tf))
                            count = cursor.fetchone()[0]

                            if count > 0:
                                # Get actual data count and date range
                                range_query = """
                                SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
                                FROM binance_ohlcv
                                WHERE symbol = %s AND timeframe = %s
                                """
                                cursor.execute(range_query, (pair, tf))
                                min_ts, max_ts, total_count = cursor.fetchone()

                                pair_info['timeframes'][tf] = {
                                    'count': total_count,
                                    'date_range': {
                                        'start': min_ts // 1000 if min_ts else None,
                                        'end': max_ts // 1000 if max_ts else None
                                    }
                                }
                        except Exception as e:
                            logger.warning(f"Error checking {pair} {tf}: {e}")
                            continue

                    if pair_info['timeframes']:
                        data_summary[pair] = pair_info

                return data_summary

        except Exception as e:
            logger.error(f"Failed to discover all data: {e}")
            return {}

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
