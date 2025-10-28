# Setting Up Database Credentials

This guide explains how to configure database credentials for the Claude Code Trading System.

## Quick Start

### Option 1: Using Environment Variables (Recommended)

1. Copy the example environment file:
   ```bash
   cp env.example.txt .env
   ```

2. Edit `.env` with your actual credentials:
   ```bash
   # Your real PostgreSQL credentials
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=your_database_name
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   ```

3. Install python-dotenv (optional, for automatic .env loading):
   ```bash
   pip install python-dotenv
   ```

### Option 2: Direct Configuration Edit

Edit `config/system_config.py` and update the `DATABASE_CONFIG` dictionary with your credentials:

```python
DATABASE_CONFIG = {
    "default_type": "postgresql",
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "your_database_name",
        "user": "your_username",
        "password": "your_password"
    },
    "sqlite": {
        "path": "freqtrade.db"
    }
}
```

### Option 3: Using SQLite (No Setup Required)

If you don't have PostgreSQL, you can use SQLite:

1. Set environment variable: `export DB_TYPE=sqlite`
2. Or edit `config/system_config.py` and change `default_type` to `"sqlite"`

## Environment Variables Reference

The following environment variables can be set:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_TYPE` | Database type: `postgresql` or `sqlite` | `postgresql` |
| `POSTGRES_HOST` | PostgreSQL hostname | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `freqtrade` |
| `POSTGRES_USER` | Database username | `freqtrade` |
| `POSTGRES_PASSWORD` | Database password | `freqtrade` |
| `SQLITE_PATH` | Path to SQLite database file | `freqtrade.db` |

## Testing Your Configuration

Run the database diagnostic to verify your configuration:

```bash
python database_diagnostic.py
```

This will test the connection and display available data.

## Security Notes

- Never commit `.env` files to version control (already in .gitignore)
- Use environment variables for sensitive credentials in production
- Consider using a secrets management service for production deployments
- The current implementation uses plain-text credentials in config files by default

## Troubleshooting

### PostgreSQL Connection Failed

1. Verify PostgreSQL is running: `pg_isready`
2. Check credentials are correct
3. Verify database exists: `psql -U your_user -d your_database`
4. Check firewall/network settings

### SQLite Not Working

1. Check file permissions on the database directory
2. Verify `sqlite3` is installed: `python -c "import sqlite3"`

### Environment Variables Not Loading

1. Ensure python-dotenv is installed: `pip install python-dotenv`
2. Or manually export variables: `export POSTGRES_PASSWORD=your_password`
3. Verify `.env` file is in project root directory

