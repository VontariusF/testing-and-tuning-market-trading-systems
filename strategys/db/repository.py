"""Persistence helpers for automated strategy remediation workflows."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from .schema import initialize_database


class StrategyRepository:
    """Lightweight repository over SQLite for storing strategy artifacts."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        initialize_database(self.db_path)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_strategy(
        self,
        *,
        family: str,
        name: str,
        template_source: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT strategy_id FROM strategies WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row:
                strategy_id = int(row[0])
                cursor.execute(
                    "UPDATE strategies SET family = ?, template_source = COALESCE(?, template_source), notes = COALESCE(?, notes) WHERE strategy_id = ?",
                    (family, template_source, notes, strategy_id),
                )
                return strategy_id

            cursor.execute(
                "INSERT INTO strategies (family, name, template_source, notes) VALUES (?, ?, ?, ?)",
                (family, name, template_source, notes),
            )
            return int(cursor.lastrowid)

    def add_variant(
        self,
        *,
        strategy_id: int,
        config: Dict[str, Any],
        parent_variant_id: Optional[int] = None,
        version_tag: Optional[str] = None,
        code_path: Optional[str] = None,
        provenance: Optional[str] = None,
    ) -> int:
        config_json = json.dumps(config, sort_keys=True)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO strategy_variants (strategy_id, parent_variant_id, version_tag, config_json, code_path, provenance)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    parent_variant_id,
                    version_tag,
                    config_json,
                    code_path,
                    provenance,
                ),
            )
            return int(cursor.lastrowid)

    def start_run(
        self,
        *,
        variant_id: int,
        data_source: str,
        iteration: int,
        remediation_plan: Optional[Dict[str, Any]] = None,
    ) -> int:
        plan_json = json.dumps(remediation_plan) if remediation_plan is not None else None
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO strategy_runs (variant_id, data_source, iteration, remediation_plan)
                VALUES (?, ?, ?, ?)
                """,
                (variant_id, data_source, iteration, plan_json),
            )
            return int(cursor.lastrowid)

    def complete_run(
        self,
        run_id: int,
        *,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE strategy_runs SET status = ?, end_time = CURRENT_TIMESTAMP, error_message = ? WHERE run_id = ?",
                (status, error_message, run_id),
            )

    def record_metrics(
        self,
        run_id: int,
        *,
        metrics: Dict[str, Any],
        bias_selection: Optional[float],
        bias_other: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
    ) -> int:
        bias_other_json = json.dumps(bias_other, sort_keys=True) if bias_other else None
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO run_metrics (run_id, sharpe_ratio, total_return, max_drawdown, win_rate, total_trades, bias_selection, bias_other, score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    metrics.get("sharpe_ratio"),
                    metrics.get("total_return"),
                    metrics.get("max_drawdown"),
                    metrics.get("win_rate"),
                    metrics.get("total_trades"),
                    bias_selection,
                    bias_other_json,
                    score,
                ),
            )
            return int(cursor.lastrowid)

    def add_remediation_action(
        self,
        run_id: int,
        *,
        action_type: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        metadata_json = json.dumps(metadata, sort_keys=True) if metadata else None
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO remediation_actions (run_id, action_type, description, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, action_type, description, metadata_json),
            )
            return int(cursor.lastrowid)

    def add_artifact(
        self,
        *,
        run_id: Optional[int],
        variant_id: Optional[int],
        artifact_type: str,
        path: str,
        notes: Optional[str] = None,
    ) -> int:
        checksum = self._checksum(path)
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO artifacts (run_id, variant_id, artifact_type, path, checksum, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, variant_id, artifact_type, path, checksum, notes),
            )
            return int(cursor.lastrowid)

    def upsert_leaderboard_entry(
        self,
        *,
        variant_id: int,
        best_run_id: int,
        score: float,
        rank: int,
        status: str = "candidate",
    ) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT leaderboard_id FROM strategy_leaderboard WHERE variant_id = ?",
                (variant_id,),
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE strategy_leaderboard
                       SET best_run_id = ?, score = ?, rank = ?, status = ?, promoted_at = CURRENT_TIMESTAMP
                     WHERE leaderboard_id = ?
                    """,
                    (best_run_id, score, rank, status, int(row[0])),
                )
                return int(row[0])

            cursor.execute(
                """
                INSERT INTO strategy_leaderboard (variant_id, best_run_id, rank, score, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (variant_id, best_run_id, rank, score, status),
            )
            return int(cursor.lastrowid)

    def start_generation_experiment(
        self,
        *,
        strategy_id: int,
        policy: str,
        parameters: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> int:
        parameters_json = json.dumps(parameters, sort_keys=True) if parameters else None
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO generation_experiments (strategy_id, policy, parameters_json, notes)
                VALUES (?, ?, ?, ?)
                """,
                (strategy_id, policy, parameters_json, notes),
            )
            return int(cursor.lastrowid)

    def complete_generation_experiment(
        self,
        experiment_id: int,
        *,
        status: str = "completed",
        notes: Optional[str] = None,
    ) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE generation_experiments
                   SET status = ?,
                       completed_at = CURRENT_TIMESTAMP,
                       notes = COALESCE(?, notes)
                 WHERE experiment_id = ?
                """,
                (status, notes, experiment_id),
            )

    def get_leaderboard(
        self,
        *,
        top_n: Optional[int] = None,
        status_filter: Optional[str] = None,
        strategy_family: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """Retrieve leaderboard entries with strategy information."""
        query = """
            SELECT
                lb.leaderboard_id,
                lb.variant_id,
                lb.best_run_id,
                lb.rank,
                lb.score,
                lb.status,
                lb.promoted_at,
                s.family,
                s.name as strategy_name,
                sv.version_tag,
                sv.config_json,
                rm.sharpe_ratio,
                rm.total_return,
                rm.max_drawdown,
                rm.win_rate,
                rm.total_trades,
                rm.bias_selection
            FROM strategy_leaderboard lb
            JOIN strategy_variants sv ON lb.variant_id = sv.variant_id
            JOIN strategies s ON sv.strategy_id = s.strategy_id
            JOIN run_metrics rm ON lb.best_run_id = rm.run_id
        """

        conditions = []
        params = []

        if status_filter:
            conditions.append("lb.status = ?")
            params.append(status_filter)

        if strategy_family:
            conditions.append("s.family = ?")
            params.append(strategy_family)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY lb.score DESC"

        if top_n:
            query += " LIMIT ?"
            params.append(top_n)

        with self._connection() as conn:
            cursor = conn.cursor()
            results = cursor.execute(query, params).fetchall()

        leaderboard_entries = []
        for row in results:
            entry = dict(zip([
                'leaderboard_id', 'variant_id', 'best_run_id', 'rank', 'score',
                'status', 'promoted_at', 'family', 'strategy_name', 'version_tag',
                'config_json', 'sharpe_ratio', 'total_return', 'max_drawdown',
                'win_rate', 'total_trades', 'bias_selection'
            ], row))

            # Parse config JSON
            if entry['config_json']:
                entry['config'] = json.loads(entry['config_json'])
                del entry['config_json']

            leaderboard_entries.append(entry)

        return leaderboard_entries

    def get_leaderboard_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the leaderboard."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Total strategies tracked
            total_strategies = cursor.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]

            # Active leaderboard entries
            active_entries = cursor.execute(
                "SELECT COUNT(*) FROM strategy_leaderboard WHERE status = 'active'"
            ).fetchone()[0]

            # Average performance metrics
            avg_metrics = cursor.execute("""
                SELECT
                    AVG(rm.sharpe_ratio) as avg_sharpe,
                    AVG(rm.total_return) as avg_return,
                    AVG(rm.max_drawdown) as avg_drawdown,
                    AVG(rm.win_rate) as avg_win_rate,
                    AVG(lb.score) as avg_score,
                    MAX(lb.score) as best_score
                FROM strategy_leaderboard lb
                JOIN run_metrics rm ON lb.best_run_id = rm.run_id
                WHERE lb.status = 'active'
            """).fetchone()

            # Top performer
            top_performer = cursor.execute("""
                SELECT s.name, lb.score
                FROM strategy_leaderboard lb
                JOIN strategy_variants sv ON lb.variant_id = sv.variant_id
                JOIN strategies s ON sv.strategy_id = s.strategy_id
                ORDER BY lb.score DESC
                LIMIT 1
            """).fetchone()

            return {
                'total_strategies': total_strategies,
                'active_leaderboard_entries': active_entries,
                'average_sharpe_ratio': avg_metrics[0] if avg_metrics[0] else 0,
                'average_total_return': avg_metrics[1] if avg_metrics[1] else 0,
                'average_max_drawdown': avg_metrics[2] if avg_metrics[2] else 0,
                'average_win_rate': avg_metrics[3] if avg_metrics[3] else 0,
                'average_score': avg_metrics[4] if avg_metrics[4] else 0,
                'best_score': avg_metrics[5] if avg_metrics[5] else 0,
                'top_performer': {
                    'name': top_performer[0] if top_performer else None,
                    'score': top_performer[1] if top_performer else None
                }
            }

    # ------------------------------------------------------------------
    # Automation job helpers
    # ------------------------------------------------------------------

    def enqueue_job(
        self,
        *,
        job_type: str,
        specification: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
    ) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO automation_jobs (job_type, specification, priority, max_retries)
                VALUES (?, ?, ?, ?)
                """,
                (job_type, json.dumps(specification, sort_keys=True), priority, max_retries),
            )
            return int(cursor.lastrowid)

    def fetch_next_job(self) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, job_type, specification, priority, status, retry_count, max_retries
                  FROM automation_jobs
                 WHERE status IN ('pending', 'retry')
                 ORDER BY priority DESC, job_id ASC
                 LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None

            job_id, job_type, spec_json, priority, status, retry_count, max_retries = row
            cursor.execute(
                """
                UPDATE automation_jobs
                   SET status = 'running',
                       started_at = CURRENT_TIMESTAMP
                 WHERE job_id = ?
                """,
                (job_id,),
            )
            conn.commit()
            return {
                "job_id": job_id,
                "job_type": job_type,
                "specification": json.loads(spec_json),
                "priority": priority,
                "status": status,
                "retry_count": retry_count,
                "max_retries": max_retries,
            }

    def complete_job(
        self,
        job_id: int,
        *,
        status: str,
        error: Optional[str] = None,
        retry: bool = False,
    ) -> None:
        with self._connection() as conn:
            if retry:
                conn.execute(
                    """
                    UPDATE automation_jobs
                       SET status = 'retry',
                           last_error = ?,
                           retry_count = retry_count + 1
                     WHERE job_id = ?
                    """,
                    (error, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE automation_jobs
                       SET status = ?,
                           completed_at = CURRENT_TIMESTAMP,
                           last_error = ?
                     WHERE job_id = ?
                    """,
                    (status, error, job_id),
                )

    def record_job_run(
        self,
        *,
        job_id: int,
        variant_id: Optional[int],
        run_id: Optional[int],
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO automation_job_runs (job_id, variant_id, run_id, status, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    variant_id,
                    run_id,
                    status,
                    json.dumps(details, sort_keys=True) if details else None,
                ),
            )
            return int(cursor.lastrowid)

    def get_run_metrics(self, run_id: int) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT sharpe_ratio, total_return, max_drawdown, win_rate, total_trades, bias_selection, score
                  FROM run_metrics
                 WHERE run_id = ?
                 ORDER BY recorded_at DESC
                 LIMIT 1
                """,
                (run_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            keys = [
                "sharpe_ratio",
                "total_return",
                "max_drawdown",
                "win_rate",
                "total_trades",
                "bias_selection",
                "score",
            ]
            return dict(zip(keys, row))

    def get_next_leaderboard_rank(self) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(rank), 0) + 1 FROM strategy_leaderboard")
            (next_rank,) = cursor.fetchone()
            return int(next_rank)

    def _checksum(self, path: str) -> Optional[str]:
        file_path = Path(path)
        if not file_path.exists():
            return None
        hasher = hashlib.sha256()
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
