"""Worker responsible for executing automation jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from strategys.automated_bias_remediation import AutomatedBiasRemediator
from strategys.db.repository import StrategyRepository

from .jobs import StrategyBatchJob, parse_job_spec


class AutomationWorker:
    """Execute jobs fetched by the automation controller."""

    def __init__(self, repository: StrategyRepository, workspace: str = ".") -> None:
        self.repository = repository
        self.workspace = Path(workspace).resolve()

    def execute(self, job: Dict[str, Any]) -> Dict[str, Any]:
        job_type = job["job_type"]
        specification = job["specification"]
        parsed_spec = parse_job_spec(job_type, specification)

        if isinstance(parsed_spec, StrategyBatchJob):
            return self._execute_strategy_batch(job, parsed_spec)

        raise ValueError(f"Unsupported job type: {job_type}")

    def _execute_strategy_batch(
        self,
        job: Dict[str, Any],
        batch_job: StrategyBatchJob,
    ) -> Dict[str, Any]:
        remediator = AutomatedBiasRemediator(
            str(self.workspace),
            repository=self.repository,
        )

        results = remediator.generate_strategy_batch(
            batch_job.specs,
            batch_job.data_path,
            policy=batch_job.policy,
            max_iterations=batch_job.max_iterations,
        )

        recorded_runs: List[Dict[str, Any]] = []
        for result in results:
            iterations = result.get("iterations", [])
            final_iteration = iterations[-1] if iterations else {}
            run_id = final_iteration.get("run_id")
            variant_id = result.get("variant_id")
            success = bool(result.get("success"))

            status = "completed" if success else "needs_review"
            details = {
                "summary": result.get("summary"),
                "success": success,
            }

            job_run_id = self.repository.record_job_run(
                job_id=job["job_id"],
                variant_id=variant_id,
                run_id=run_id,
                status=status,
                details=details,
            )

            if success and run_id and variant_id:
                metrics = self.repository.get_run_metrics(run_id) or {}
                score = metrics.get("score")
                if score is None and metrics:
                    # Fall back to simple score if not stored
                    sharpe = metrics.get("sharpe_ratio") or 0.0
                    drawdown = abs(metrics.get("max_drawdown") or 0.0)
                    penalty = metrics.get("bias_selection") or 0.0
                    score = float(sharpe) - float(drawdown) - float(penalty)
                rank = self.repository.get_next_leaderboard_rank()
                self.repository.upsert_leaderboard_entry(
                    variant_id=variant_id,
                    best_run_id=run_id,
                    score=float(score) if score is not None else 0.0,
                    rank=rank,
                    status="candidate",
                )

            recorded_runs.append(
                {
                    "job_run_id": job_run_id,
                    "variant_id": variant_id,
                    "run_id": run_id,
                    "success": success,
                }
            )

        return {"runs": recorded_runs}
