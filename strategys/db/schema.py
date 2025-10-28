"""SQLite schema and initialization helpers for the automated remediation pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

DDL_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS strategies (
        strategy_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        family             TEXT        NOT NULL,
        name               TEXT        NOT NULL UNIQUE,
        template_source    TEXT,
        created_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        notes              TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategy_variants (
        variant_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id        INTEGER     NOT NULL REFERENCES strategies(strategy_id),
        parent_variant_id  INTEGER     REFERENCES strategy_variants(variant_id),
        version_tag        TEXT,
        config_json        TEXT        NOT NULL,
        code_path          TEXT,
        provenance         TEXT,
        created_at         DATETIME    DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategy_runs (
        run_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id         INTEGER     NOT NULL REFERENCES strategy_variants(variant_id),
        data_source        TEXT        NOT NULL,
        iteration          INTEGER     NOT NULL,
        remediation_plan   TEXT,
        start_time         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        end_time           DATETIME,
        status             TEXT        DEFAULT 'pending',
        error_message      TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS run_metrics (
        run_metric_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id             INTEGER     NOT NULL REFERENCES strategy_runs(run_id),
        sharpe_ratio       REAL,
        total_return       REAL,
        max_drawdown       REAL,
        win_rate           REAL,
        total_trades       INTEGER,
        bias_selection     REAL,
        bias_other         TEXT,
        score              REAL,
        recorded_at        DATETIME    DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS remediation_actions (
        action_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id             INTEGER     NOT NULL REFERENCES strategy_runs(run_id),
        action_type        TEXT        NOT NULL,
        description        TEXT,
        metadata_json      TEXT,
        created_at         DATETIME    DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id             INTEGER     REFERENCES strategy_runs(run_id),
        variant_id         INTEGER     REFERENCES strategy_variants(variant_id),
        artifact_type      TEXT        NOT NULL,
        path               TEXT        NOT NULL,
        created_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        checksum           TEXT,
        notes              TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategy_leaderboard (
        leaderboard_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id         INTEGER     NOT NULL REFERENCES strategy_variants(variant_id),
        best_run_id        INTEGER     NOT NULL REFERENCES strategy_runs(run_id),
        rank               INTEGER     NOT NULL,
        score              REAL        NOT NULL,
        promoted_at        DATETIME    DEFAULT CURRENT_TIMESTAMP,
        status             TEXT        DEFAULT 'candidate'
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS generation_experiments (
        experiment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id        INTEGER     NOT NULL REFERENCES strategies(strategy_id),
        policy             TEXT        NOT NULL,
        parameters_json    TEXT,
        started_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        completed_at       DATETIME,
        status             TEXT        DEFAULT 'active',
        notes              TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_jobs (
        job_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type           TEXT        NOT NULL,
        specification      TEXT        NOT NULL,
        status             TEXT        DEFAULT 'pending',
        priority           INTEGER     DEFAULT 0,
        created_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        started_at         DATETIME,
        completed_at       DATETIME,
        last_error         TEXT,
        retry_count        INTEGER     DEFAULT 0,
        max_retries        INTEGER     DEFAULT 3
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_job_runs (
        job_run_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id             INTEGER     NOT NULL REFERENCES automation_jobs(job_id) ON DELETE CASCADE,
        variant_id         INTEGER     REFERENCES strategy_variants(variant_id),
        run_id             INTEGER     REFERENCES strategy_runs(run_id),
        status             TEXT        NOT NULL,
        started_at         DATETIME    DEFAULT CURRENT_TIMESTAMP,
        completed_at       DATETIME,
        details            TEXT
    );
    """,
)


def initialize_database(db_path: Path) -> None:
    """Ensure the SQLite database exists and all schema migrations are applied."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for statement in DDL_STATEMENTS:
            cursor.execute(statement)
        conn.commit()
