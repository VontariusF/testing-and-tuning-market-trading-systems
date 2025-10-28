# Binance Database Query Examples

## Connection String
```
postgresql://freqtrade_user:Vontarius97$@localhost:5432/freqtrade_db
```

## Quick Stats

### Summary by symbol and timeframe
```sql
SELECT 
    exchange,
    symbol,
    timeframe,
    COUNT(*) as candles,
    MIN(datetime) as first_candle,
    MAX(datetime) as last_candle
FROM binance_ohlcv
GROUP BY exchange, symbol, timeframe
ORDER BY symbol, timeframe;
```

### Total candles in database
```sql
SELECT COUNT(*) FROM binance_ohlcv;
```

## Data Queries

### Get recent candles for a symbol
```sql
SELECT * FROM binance_ohlcv
WHERE symbol = 'ADA_USDT' 
  AND timeframe = '5m'
ORDER BY timestamp DESC
LIMIT 100;
```

### Get candles for specific date range
```sql
SELECT * FROM binance_ohlcv
WHERE symbol = 'SOL_USDT'
  AND datetime >= '2025-01-01'
  AND datetime < '2025-02-01'
ORDER BY timestamp;
```

### Get daily OHLCV from 5m data (aggregation)
```sql
SELECT 
    DATE(datetime) as date,
    symbol,
    MIN(open) as open,
    MAX(high) as high,
    MIN(low) as low,
    MAX(close) as close,
    SUM(volume) as volume
FROM binance_ohlcv
WHERE symbol = 'ADA_USDT'
  AND datetime >= '2025-01-01'
GROUP BY DATE(datetime), symbol
ORDER BY date;
```

### Calculate daily returns
```sql
WITH daily_close AS (
    SELECT 
        DATE(datetime) as date,
        symbol,
        FIRST_VALUE(close) OVER (PARTITION BY DATE(datetime), symbol ORDER BY timestamp) as open_price,
        LAST_VALUE(close) OVER (PARTITION BY DATE(datetime), symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_price
    FROM binance_ohlcv
    WHERE symbol = 'ADA_USDT'
)
SELECT DISTINCT
    date,
    symbol,
    open_price,
    close_price,
    ((close_price - open_price) / open_price * 100) as daily_return_pct
FROM daily_close
ORDER BY date DESC;
```

### Find highest volume candles
```sql
SELECT 
    datetime,
    symbol,
    timeframe,
    open,
    high,
    low,
    close,
    volume
FROM binance_ohlcv
WHERE symbol = 'SOL_USDT'
ORDER BY volume DESC
LIMIT 20;
```

### Calculate moving averages
```sql
SELECT 
    datetime,
    symbol,
    close,
    AVG(close) OVER (
        PARTITION BY symbol 
        ORDER BY timestamp 
        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
    ) as ma_20,
    AVG(close) OVER (
        PARTITION BY symbol 
        ORDER BY timestamp 
        ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
    ) as ma_50
FROM binance_ohlcv
WHERE symbol = 'ADA_USDT'
ORDER BY timestamp DESC
LIMIT 100;
```

### Get candlestick patterns (simplified)
```sql
SELECT 
    datetime,
    symbol,
    open,
    high,
    low,
    close,
    CASE 
        WHEN close > open THEN 'GREEN'
        WHEN close < open THEN 'RED'
        ELSE 'DOJI'
    END as candle_type,
    high - low as candle_range,
    ABS(close - open) as body_size,
    ((close - open) / open * 100) as pct_change
FROM binance_ohlcv
WHERE symbol = 'SOL_USDT'
ORDER BY timestamp DESC
LIMIT 50;
```

## Python Usage Example

```python
import psycopg2
import pandas as pd

# Connect to database
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='freqtrade_db',
    user='freqtrade_user',
    password='Vontarius97$'
)

# Query data
query = """
SELECT datetime, open, high, low, close, volume
FROM binance_ohlcv
WHERE symbol = 'ADA_USDT' AND timeframe = '5m'
ORDER BY timestamp
"""

df = pd.read_sql(query, conn)
print(df.head())

conn.close()
```

## Maintenance

### Check table size
```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('binance_ohlcv')) as total_size,
    pg_size_pretty(pg_relation_size('binance_ohlcv')) as table_size,
    pg_size_pretty(pg_indexes_size('binance_ohlcv')) as indexes_size;
```

### Vacuum and analyze (optimize)
```sql
VACUUM ANALYZE binance_ohlcv;
```

## Adding More Data

To add more Binance data files, simply place them in one of these directories:
- `/Users/vontariusfalls/strategy_template/user_data/data/binance/`
- `/Users/vontariusfalls/strategy_template/user_data/data/binanceus/`
- `/Users/vontariusfalls/london-breakout-strategy/user_data/data/binance/`

Then run:
```bash
python3 /Users/vontariusfalls/testing-and-tuning-market-trading-systems/tools/load_binance_to_db.py
```

The script automatically handles duplicates and will update existing records.

