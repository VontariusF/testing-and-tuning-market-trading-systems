#!/usr/bin/env python3
"""Regression coverage for the automated bias remediation pipeline."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from strategys.automated_bias_remediation import (
    AutomatedBiasRemediator,
    StrategyConfig,
    StrategySpec,
    _main as run_cli,
)
from strategys.db import StrategyRepository
from strategys.automation.controller import AutomationController
from strategys.automation.worker import AutomationWorker
from tools import run_automation


class AutomatedBiasRemediationTests(unittest.TestCase):
    """Validate orchestration logic without invoking heavy C++ binaries."""

    def setUp(self) -> None:
        self.remediator = AutomatedBiasRemediator(".", enable_persistence=False)

    def test_pipeline_terminates_after_single_iteration(self) -> None:
        baseline_validation = {
            "performance_metrics": {"sharpe_ratio": 0.1, "total_return": 0.01, "total_trades": 10},
            "algorithm_results": {"SELBIAS": {"bias_metrics": {"detected_bias": "Selection bias=0.1200"}}},
        }
        improved_validation = {
            "performance_metrics": {"sharpe_ratio": 0.2, "total_return": 0.015, "total_trades": 10},
            "algorithm_results": {"SELBIAS": {"bias_metrics": {"detected_bias": "Selection bias=0.0400"}}},
        }

        strategy_cfg = StrategyConfig(
            name="test_sma",
            strategy_type="sma",
            parameters={"short": 10, "long": 40, "fee": 0.0005, "symbol": "DEMO"},
            source=Path("framework/sma_strategy.cpp"),
        )

        with mock.patch.object(
            self.remediator,
            "_load_initial_strategy_config",
            return_value=strategy_cfg,
        ), mock.patch.object(
            self.remediator,
            "_persist_config",
            side_effect=["baseline.json", "iter1.json"],
        ), mock.patch.object(
            self.remediator,
            "_ensure_binary",
        ), mock.patch.object(
            self.remediator,
            "_run_strategy_validation",
            side_effect=[baseline_validation, improved_validation],
        ), mock.patch.object(
            self.remediator,
            "_generate_auto_remediation_plan",
            side_effect=[
                {
                    "full_plan": {"remediation_steps": ["Implement walk-forward", "Apply multiple testing"]},
                    "automated_steps": ["walk-forward", "multiple testing"],
                    "requires_manual": 0,
                },
                {"full_plan": {"remediation_steps": []}, "automated_steps": [], "requires_manual": 0},
            ],
        ), mock.patch.object(
            self.remediator,
            "_apply_automated_fixes",
            return_value=(strategy_cfg, ["Walk-forward", "Multiple testing"]),
        ), mock.patch.object(
            self.remediator,
            "_persist_final_artifacts",
            return_value={"final_config_path": "final.json", "report_path": "report.txt"},
        ):
            results = self.remediator.run_full_pipeline("framework/sma_strategy.cpp", "data/sample_ohlc.txt", 2)

        self.assertTrue(results["iterations"], "Iterations should be recorded")
        self.assertEqual(results["iterations"][-1]["iteration"], 1)
        self.assertIn("summary", results)
        self.assertIn("report.txt", results.get("summary", ""))

    def test_cli_invokes_pipeline_and_writes_results(self) -> None:
        fake_results = {
            "iterations": [],
            "final_config_path": "automation_outputs/final.json",
            "report_path": "automation_outputs/report.txt",
            "summary": "summary text",
        }

        with mock.patch(
            "strategys.automated_bias_remediation.AutomatedBiasRemediator.run_full_pipeline",
            return_value=fake_results,
        ), mock.patch(
            "strategys.automated_bias_remediation.AutomatedBiasRemediator.__init__",
            return_value=None,
        ), mock.patch.object(
            Path, "write_text", autospec=True
        ) as write_mock:
            test_args = [
                "automated_bias_remediation.py",
                "--strategy",
                "framework/sma_strategy.cpp",
                "--data",
                "data/sample_ohlc.txt",
                "--iterations",
                "1",
                "--output",
                "results.json",
            ]
            with mock.patch.object(sys, "argv", test_args):
                run_cli()

        write_mock.assert_called()
        args, kwargs = write_mock.call_args
        self.assertIn("results.json", str(args[0]))

    def test_generate_strategy_batch_uses_factory_specs(self) -> None:
        spec = StrategySpec(
            base_name="factory_sma",
            strategy_type="sma",
            template_path="framework/sma_strategy.cpp",
            base_parameters={"short": 8, "long": 24, "fee": 0.0005, "symbol": "DEMO"},
            parameter_grid={"short": [8], "long": [24]},
            limit=1,
        )

        with mock.patch.object(
            self.remediator,
            "run_full_pipeline",
            return_value={"summary": "ok"},
        ) as run_mock:
            results = self.remediator.generate_strategy_batch([spec], "data/sample_ohlc.txt")

        self.assertEqual(len(results), 1)
        self.assertTrue(run_mock.called)
        _, kwargs = run_mock.call_args
        generated_config = kwargs.get("preconfigured")
        self.assertIsInstance(generated_config, StrategyConfig)
        self.assertEqual(generated_config.parameters["short"], 8)
        self.assertEqual(generated_config.metadata.get("factory", {}).get("base_strategy_name"), "factory_sma")


class StrategyRepositoryTests(unittest.TestCase):
    def test_repository_persists_strategy_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "repo.sqlite"
            repo = StrategyRepository(db_path)

            strategy_id = repo.upsert_strategy(
                family="sma",
                name="unit_test_strategy",
                template_source="framework/sma_strategy.cpp",
            )
            self.assertGreater(strategy_id, 0)

            config_dict = {
                "name": "unit_test_strategy",
                "strategy_type": "sma",
                "parameters": {"short": 5, "long": 20},
                "metadata": {},
                "source": "framework/sma_strategy.cpp",
            }
            variant_id = repo.add_variant(
                strategy_id=strategy_id,
                config=config_dict,
                version_tag="baseline",
                code_path="framework/sma_strategy.cpp",
                provenance="unit-test",
            )
            self.assertGreater(variant_id, 0)

            run_id = repo.start_run(
                variant_id=variant_id,
                data_source="data/sample_ohlc.txt",
                iteration=0,
                remediation_plan=None,
            )
            self.assertGreater(run_id, 0)

            repo.record_metrics(
                run_id,
                metrics={
                    "sharpe_ratio": 0.5,
                    "total_return": 0.1,
                    "max_drawdown": 0.05,
                    "win_rate": 0.6,
                    "total_trades": 12,
                },
                bias_selection=0.02,
                bias_other={"SELBIAS": {"bias_metrics": {"detected_bias": "Selection bias=0.0200"}}},
                score=0.43,
            )
            repo.complete_run(run_id, status="success")

            repo.add_remediation_action(
                run_id,
                action_type="walk_forward",
                description="Walk-forward optimization applied",
            )

            artifact_path = Path(tmpdir) / "artifact.txt"
            artifact_path.write_text("unit test artifact", encoding="utf-8")
            repo.add_artifact(
                run_id=run_id,
                variant_id=variant_id,
                artifact_type="config",
                path=str(artifact_path),
                notes="unit-test",
            )

            leaderboard_id = repo.upsert_leaderboard_entry(
                variant_id=variant_id,
                best_run_id=run_id,
                score=0.43,
                rank=1,
            )
            self.assertGreater(leaderboard_id, 0)

            experiment_id = repo.start_generation_experiment(
                strategy_id=strategy_id,
                policy="grid",
                parameters={"limit": 1},
            )
            self.assertGreater(experiment_id, 0)
            repo.complete_generation_experiment(experiment_id)


class AutomationControllerTests(unittest.TestCase):
    def test_controller_processes_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "automation.sqlite"
            repo = StrategyRepository(db_path)

            job_id = repo.enqueue_job(
                job_type="strategy_batch",
                specification={"specs": [], "data_path": "data/sample_ohlc.txt"},
            )

            controller = AutomationController(repo, workspace=tmpdir, poll_interval=0.01)
            with mock.patch(
                "strategys.automation.controller.AutomationWorker.execute",
                return_value={"ok": True},
            ) as exec_mock:
                result = controller.run_once()

            self.assertEqual(result, {"ok": True})
            exec_mock.assert_called_once()

            with repo._connection() as conn:  # type: ignore[attr-defined]
                status = conn.execute(
                    "SELECT status FROM automation_jobs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()[0]
            self.assertEqual(status, "completed")


class AutomationWorkerTests(unittest.TestCase):
    def test_worker_records_job_runs_and_leaderboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "automation.sqlite"
            repo = StrategyRepository(db_path)

            strategy_id = repo.upsert_strategy(
                family="sma",
                name="worker_strategy",
                template_source="framework/sma_strategy.cpp",
            )
            variant_id = repo.add_variant(
                strategy_id=strategy_id,
                config={
                    "name": "worker_strategy",
                    "strategy_type": "sma",
                    "parameters": {"short": 5, "long": 20},
                    "metadata": {},
                    "source": "framework/sma_strategy.cpp",
                },
                version_tag="baseline",
                code_path="framework/sma_strategy.cpp",
                provenance="unit-test",
            )

            run_id = repo.start_run(
                variant_id=variant_id,
                data_source="data/sample_ohlc.txt",
                iteration=0,
                remediation_plan=None,
            )
            repo.record_metrics(
                run_id,
                metrics={
                    "sharpe_ratio": 0.7,
                    "total_return": 0.12,
                    "max_drawdown": 0.04,
                    "win_rate": 0.6,
                    "total_trades": 15,
                },
                bias_selection=0.03,
                score=0.63,
            )
            repo.complete_run(run_id, status="success")

            job_id = repo.enqueue_job(
                job_type="strategy_batch",
                specification={
                    "data_path": "data/sample_ohlc.txt",
                    "specs": [
                        {
                            "base_name": "worker_strategy",
                            "strategy_type": "sma",
                            "template_path": "framework/sma_strategy.cpp",
                            "base_parameters": {"short": 5, "long": 20},
                        }
                    ],
                },
            )
            job = repo.fetch_next_job()
            assert job is not None

            dummy_results = [
                {
                    "iterations": [
                        {"iteration": 0, "run_id": run_id},
                    ],
                    "success": True,
                    "summary": "Automated run completed",
                    "variant_id": variant_id,
                }
            ]

            def fake_init(self, workspace_dir=".", **kwargs):  # type: ignore[override]
                self.repository = kwargs.get("repository")
                self.outputs_dir = Path(tmpdir)

            with mock.patch(
                "strategys.automation.worker.AutomatedBiasRemediator.__init__",
                autospec=True,
            ) as init_mock, mock.patch(
                "strategys.automation.worker.AutomatedBiasRemediator.generate_strategy_batch",
                return_value=dummy_results,
            ):
                init_mock.side_effect = fake_init
                worker = AutomationWorker(repo, workspace=tmpdir)
                result = worker.execute(job)

            self.assertEqual(len(result["runs"]), 1)
            recorded = result["runs"][0]
            self.assertTrue(recorded["success"])
            self.assertEqual(recorded["variant_id"], variant_id)

            with repo._connection() as conn:  # type: ignore[attr-defined]
                status = conn.execute(
                    "SELECT status FROM automation_job_runs WHERE job_id = ?",
                    (job_id,),
                ).fetchone()[0]
                leaderboard_row = conn.execute(
                    "SELECT variant_id, best_run_id, score FROM strategy_leaderboard WHERE variant_id = ?",
                    (variant_id,),
                ).fetchone()

            self.assertEqual(status, "completed")
            self.assertIsNotNone(leaderboard_row)
            self.assertEqual(leaderboard_row[0], variant_id)
            self.assertEqual(leaderboard_row[1], run_id)
            self.assertAlmostEqual(leaderboard_row[2], 0.63, places=4)


class AutomationCLITests(unittest.TestCase):
    def test_run_automation_main_invokes_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            db_path = (workspace / "freqtrade_db").resolve()

            with mock.patch("tools.run_automation.StrategyRepository") as repo_mock, mock.patch(
                "tools.run_automation.AutomationController"
            ) as controller_mock:
                controller_instance = controller_mock.return_value
                exit_code = run_automation.main(
                    ["--workspace", str(workspace), "--poll-interval", "10"]
                )

            self.assertEqual(exit_code, 0)
            repo_mock.assert_called_once_with(db_path)
            controller_mock.assert_called_once_with(
                repo_mock.return_value,
                workspace=str(workspace.resolve()),
                poll_interval=10.0,
            )
            controller_instance.run_once.assert_called_once()


if __name__ == "__main__":
    unittest.main()
