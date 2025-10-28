"""Automation controller to orchestrate end-to-end strategy jobs."""

from __future__ import annotations

import logging
import time
import traceback
from typing import Optional

from strategys.db.repository import StrategyRepository

from .worker import AutomationWorker


logger = logging.getLogger(__name__)


class AutomationController:
    """Polls the job queue and dispatches work to automation workers."""

    def __init__(
        self,
        repository: StrategyRepository,
        *,
        workspace: str = ".",
        poll_interval: float = 5.0,
    ) -> None:
        self.repository = repository
        self.worker = AutomationWorker(repository, workspace=workspace)
        self.poll_interval = poll_interval
        self._running = False

    def run_forever(self) -> None:
        """Continuously poll for jobs and execute them."""
        self._running = True
        logger.info("Automation controller started")
        while self._running:
            job = self.repository.fetch_next_job()
            if not job:
                time.sleep(self.poll_interval)
                continue
            self._process_job(job)

    def stop(self) -> None:
        self._running = False

    def run_once(self) -> Optional[dict]:
        """Process a single job if available."""
        job = self.repository.fetch_next_job()
        if not job:
            return None
        return self._process_job(job)

    def _process_job(self, job: dict) -> dict:
        job_id = job["job_id"]
        logger.info("Processing job %s (%s)", job_id, job["job_type"])
        try:
            result = self.worker.execute(job)
            self.repository.complete_job(job_id, status="completed")
            logger.info("Job %s completed", job_id)
            return result
        except Exception as exc:  # pylint: disable=broad-except
            error_message = f"{exc}\n{traceback.format_exc()}"
            retry_count = job.get("retry_count", 0) + 1
            max_retries = job.get("max_retries", 0)
            should_retry = retry_count <= max_retries
            if should_retry:
                logger.warning(
                    "Job %s failed (attempt %s/%s): %s",
                    job_id,
                    retry_count,
                    max_retries,
                    exc,
                )
                self.repository.complete_job(
                    job_id,
                    status="retry",
                    error=error_message,
                    retry=True,
                )
            else:
                logger.error("Job %s failed permanently: %s", job_id, exc)
                self.repository.complete_job(
                    job_id,
                    status="failed",
                    error=error_message,
                )
            return {"error": error_message, "retry": should_retry}
