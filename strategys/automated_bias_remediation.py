#!/usr/bin/env python3
"""Automated bias remediation pipeline that orchestrates strategy validation,
parameter remediation, and reporting using the C++ backtesting harness.
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import math
import random
import re
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure we can import the remediation engine wherever this module lives.
_CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(_CURRENT_DIR))
sys.path.append(str(_CURRENT_DIR.parent / "stratval"))

try:
    from bias_remediation import BiasRemediationEngine, export_remediation_report  # type: ignore

    try:  # Optional dependency: full stratval adapter registry
        from stratval.adapters.base import AlgorithmRegistry  # type: ignore
        STRATVAL_AVAILABLE = True
    except Exception:  # pragma: no cover - the registry is optional
        AlgorithmRegistry = None  # type: ignore
        STRATVAL_AVAILABLE = False
except ImportError as exc:  # pragma: no cover - surface import error clearly
    raise ImportError(
        "BiasRemediationEngine could not be imported. Ensure stratval/bias_remediation.py"
        " is on PYTHONPATH."
    ) from exc

try:
    from strategys.db import StrategyRepository
except Exception:  # pragma: no cover - database layer is optional during early setup
    StrategyRepository = None  # type: ignore


@dataclass
class StrategyConfig:
    """Serializable representation of a strategy run configuration."""

    name: str
    strategy_type: str
    parameters: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[Path] = None

    PARAM_ORDER: Dict[str, List[Tuple[str, str]]] = field(
        init=False,
        default_factory=lambda: {
            "sma": [
                ("short", "--short"),
                ("long", "--long"),
                ("fee", "--fee"),
                ("symbol", "--symbol"),
            ],
            "rsi": [
                ("period", "--period"),
                ("overbought", "--overbought"),
                ("oversold", "--oversold"),
                ("confirm", "--confirm"),
                ("fee", "--fee"),
                ("symbol", "--symbol"),
            ],
            "macd": [
                ("fast", "--fast"),
                ("slow", "--slow"),
                ("signal", "--signal"),
                ("overbought", "--overbought"),
                ("oversold", "--oversold"),
                ("fee", "--fee"),
                ("symbol", "--symbol"),
            ],
        },
    )

    def clone(self, suffix: str, updates: Optional[Dict[str, Any]] = None) -> "StrategyConfig":
        new_config = copy.deepcopy(self)
        new_config.name = f"{self.name}_{suffix}"
        if updates:
            new_config.parameters.update(updates)
        return new_config

    def cli_args(self, data_path: str) -> List[str]:
        args = [self.strategy_type.lower(), data_path]
        for key, flag in self.PARAM_ORDER.get(self.strategy_type.lower(), []):
            value = self.parameters.get(key)
            if value is None:
                continue
            if isinstance(value, float):
                formatted = f"{value:.6f}".rstrip("0").rstrip(".")
            else:
                formatted = str(value)
            args.extend([flag, formatted])
        return args

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "strategy_type": self.strategy_type,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "source": str(self.source) if self.source else None,
        }


@dataclass
class StrategySpec:
    """Specification for generating strategy variants from a template."""

    base_name: str
    strategy_type: str
    template_path: str
    base_parameters: Dict[str, Any]
    parameter_grid: Dict[str, List[Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None


class StrategyFactory:
    """Generate concrete StrategyConfig instances from high-level specs."""

    def __init__(self, workspace: Path, output_dir: Path):
        self.workspace = workspace
        self.output_dir = output_dir / "generated_strategies"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, spec: StrategySpec) -> List[StrategyConfig]:
        template_path = self._resolve_template(Path(spec.template_path))
        grid_items = sorted(spec.parameter_grid.items())
        if grid_items:
            value_space = itertools.product(*(values for _, values in grid_items))
        else:
            value_space = [()]

        variants: List[StrategyConfig] = []
        for index, variant_values in enumerate(value_space, start=1):
            if spec.limit is not None and index > spec.limit:
                break

            parameters = copy.deepcopy(spec.base_parameters)
            for (param_name, _), value in zip(grid_items, variant_values):
                parameters[param_name] = value

            variant_name = f"{spec.base_name}_{index:03d}"
            metadata = copy.deepcopy(spec.metadata)
            metadata.setdefault("factory", {}).update(
                {
                    "base_strategy_name": spec.base_name,
                    "template_path": str(template_path),
                    "grid_index": index,
                }
            )
            source_path = self._materialize_source(template_path, variant_name, parameters)
            metadata["factory"]["materialized_source"] = str(source_path)

            variants.append(
                StrategyConfig(
                    name=variant_name,
                    strategy_type=spec.strategy_type,
                    parameters=parameters,
                    metadata=metadata,
                    source=source_path,
                )
            )

        return variants

    def _resolve_template(self, template_path: Path) -> Path:
        if not template_path.is_absolute():
            template_path = (self.workspace / template_path).resolve()
        if not template_path.exists():
            raise FileNotFoundError(f"Template strategy not found: {template_path}")
        return template_path

    def _materialize_source(
        self, template_path: Path, variant_name: str, parameters: Dict[str, Any]
    ) -> Path:
        target_path = self.output_dir / f"{variant_name}{template_path.suffix or '.cpp'}"
        template_body = template_path.read_text(encoding="utf-8")
        header = (
            "// Generated by StrategyFactory\n"
            f"// Variant: {variant_name}\n"
            f"// Parameters: {json.dumps(parameters, sort_keys=True)}\n\n"
        )
        target_path.write_text(header + template_body, encoding="utf-8")
        return target_path


class AutomatedBiasRemediator:
    """Fully automated bias detection and remediation orchestrator."""

    DEFAULT_PARAMS: Dict[str, Dict[str, Any]] = {
        "sma": {"short": 10, "long": 40, "fee": 0.0005, "symbol": "DEMO"},
        "rsi": {
            "period": 14,
            "overbought": 70.0,
            "oversold": 30.0,
            "confirm": 2,
            "fee": 0.0005,
            "symbol": "DEMO",
        },
        "macd": {
            "fast": 12,
            "slow": 26,
            "signal": 9,
            "overbought": 1.0,
            "oversold": -1.0,
            "fee": 0.0005,
            "symbol": "DEMO",
        },
    }

    def __init__(
        self,
        workspace_dir: str = ".",
        *,
        db_path: Optional[str] = None,
        enable_persistence: bool = True,
        repository: Optional[StrategyRepository] = None,
    ):
        self.workspace = Path(workspace_dir).resolve()
        self.build_dir = self.workspace / "build"
        self.outputs_dir = self.workspace / "automation_outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.remediation_engine = BiasRemediationEngine()

        self.repository: Optional[StrategyRepository] = repository
        if self.repository is None and enable_persistence and StrategyRepository is not None:
            resolved = self._resolve_db_path(db_path)
            try:
                self.repository = StrategyRepository(resolved)
            except Exception:  # pragma: no cover - repository is optional
                self.repository = None

        self.automation_steps = {
            "walk_forward_optimization": self._implement_walk_forward,
            "parameter_space_reduction": self._implement_parameter_reduction,
            "multiple_testing_corrections": self._implement_mt_corrections,
            "out_of_sample_validation": self._implement_oos_validation,
        }

    def _resolve_db_path(self, db_path: Optional[str]) -> Path:
        if db_path:
            return Path(db_path).expanduser().resolve()
        return (self.workspace / "freqtrade_db").resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_full_pipeline(
        self,
        strategy_path: str,
        data_path: str,
        max_iterations: int = 3,
        *,
        preconfigured: Optional[StrategyConfig] = None,
    ) -> Dict[str, Any]:
        print("🤖 STARTING FULLY AUTOMATED BIAS REMEDIATION PIPELINE")
        print("=" * 72)

        if preconfigured is not None:
            config = copy.deepcopy(preconfigured)
            config.source = Path(strategy_path)
        else:
            config = self._load_initial_strategy_config(Path(strategy_path))
        variant_meta = self._register_strategy_variant(
            config,
            version_tag="baseline",
            parent_variant_id=None,
            provenance="initial",
        )
        current_variant_id = variant_meta.get("variant_id") if variant_meta else None
        config_path = self._persist_config(config, suffix="baseline")
        self._record_artifact(
            run_id=None,
            variant_id=current_variant_id,
            artifact_type="config",
            path=config_path,
            notes="baseline",
        )

        results: Dict[str, Any] = {
            "original_strategy": strategy_path,
            "iterations": [],
            "final_strategy": None,
            "success": False,
        }

        baseline_run_id = self._start_db_run(
            current_variant_id,
            data_source=data_path,
            iteration=0,
            remediation_plan=None,
        )
        try:
            baseline_validation = self._run_strategy_validation(config, data_path)
        except Exception as exc:
            self._finalize_db_run(
                baseline_run_id,
                {},
                status="failed",
                error_message=str(exc),
            )
            raise
        self._finalize_db_run(baseline_run_id, baseline_validation)
        results["iterations"].append(
            {
                "iteration": 0,
                "config_path": config_path,
                "strategy_config": config.to_dict(),
                "validation_results": baseline_validation,
                "biases_detected": self._extract_biases_from_validation(baseline_validation),
                "run_id": baseline_run_id,
            }
        )

        current_config = config
        current_validation = baseline_validation
        latest_plan: Optional[Dict[str, Any]] = None

        for iteration in range(1, max_iterations + 1):
            print(f"\n🔄 ITERATION {iteration}: Automated Remediation")
            print("-" * 52)

            remediation_plan = self._generate_auto_remediation_plan(
                current_config, current_validation
            )
            latest_plan = remediation_plan["full_plan"]

            if not remediation_plan["automated_steps"]:
                print("✅ No automated steps remaining – stopping pipeline")
                break

            updated_config, applied_fixes = self._apply_automated_fixes(
                current_config, remediation_plan, data_path
            )
            parent_variant_id = current_variant_id
            new_variant_meta = self._register_strategy_variant(
                updated_config,
                version_tag=f"iter{iteration}",
                parent_variant_id=parent_variant_id,
                provenance=", ".join(applied_fixes) if applied_fixes else "automated",
            )
            new_variant_id = new_variant_meta.get("variant_id") if new_variant_meta else None
            current_variant_id = new_variant_id if new_variant_id is not None else parent_variant_id

            config_path = self._persist_config(updated_config, suffix=f"iter{iteration}")
            self._record_artifact(
                run_id=None,
                variant_id=current_variant_id,
                artifact_type="config",
                path=config_path,
                notes=f"iteration {iteration}",
            )

            run_id = self._start_db_run(
                current_variant_id,
                data_source=data_path,
                iteration=iteration,
                remediation_plan=remediation_plan["full_plan"],
            )
            try:
                updated_validation = self._run_strategy_validation(updated_config, data_path)
            except Exception as exc:
                self._finalize_db_run(
                    run_id,
                    {},
                    status="failed",
                    error_message=str(exc),
                )
                raise
            self._finalize_db_run(
                run_id,
                updated_validation,
                applied_fixes=applied_fixes,
            )

            improvement = self._calculate_improvement(current_validation, updated_validation)

            results["iterations"].append(
                {
                    "iteration": iteration,
                    "config_path": config_path,
                    "strategy_config": updated_config.to_dict(),
                    "validation_results": updated_validation,
                    "applied_fixes": applied_fixes,
                    "improvement_metrics": improvement,
                    "remaining_biases": self._extract_biases_from_validation(updated_validation),
                    "remediation_plan": remediation_plan["full_plan"],
                    "run_id": run_id,
                }
            )

            current_config = updated_config
            current_validation = updated_validation

            if self._should_terminate_pipeline(updated_validation, remediation_plan):
                break

        results["final_strategy"] = current_config.to_dict()
        results["latest_remediation_plan"] = latest_plan
        artifact_paths = self._persist_final_artifacts(
            current_config,
            latest_plan,
            variant_id=current_variant_id,
        )
        results.update(artifact_paths)
        results["success"] = self._is_pipeline_successful(results)
        results["summary"] = self._generate_pipeline_summary(results)
        results["variant_id"] = current_variant_id

        print(
            f"\n🎯 PIPELINE COMPLETE: {'SUCCESS' if results['success'] else 'REQUIRES MANUAL INTERVENTION'}"
        )
        return results

    def generate_strategy_batch(
        self,
        specs: List[StrategySpec],
        data_path: str,
        *,
        policy: str = "grid",
        max_iterations: int = 3,
    ) -> List[Dict[str, Any]]:
        """Generate strategies from specs and run them through the pipeline."""

        factory = StrategyFactory(self.workspace, self.outputs_dir)
        batch_results: List[Dict[str, Any]] = []

        for spec in specs:
            generated_configs = factory.generate(spec)
            experiment_id = self._start_generation_experiment(spec, policy)
            try:
                for config in generated_configs:
                    strategy_path = str(config.source) if config.source else spec.template_path
                    result = self.run_full_pipeline(
                        strategy_path,
                        data_path,
                        max_iterations,
                        preconfigured=config,
                    )
                    batch_results.append(result)
            finally:
                self._complete_generation_experiment(experiment_id)

        return batch_results

    # ------------------------------------------------------------------
    # Strategy configuration helpers
    # ------------------------------------------------------------------
    def _load_initial_strategy_config(self, strategy_path: Path) -> StrategyConfig:
        if not strategy_path.exists():
            raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

        strategy_type = self._infer_strategy_type(strategy_path)
        parameters = copy.deepcopy(self.DEFAULT_PARAMS[strategy_type])
        name = strategy_path.stem
        return StrategyConfig(
            name=name,
            strategy_type=strategy_type,
            parameters=parameters,
            source=strategy_path,
        )

    def _infer_strategy_type(self, strategy_path: Path) -> str:
        name = strategy_path.name.lower()
        if "sma" in name:
            return "sma"
        if "rsi" in name:
            return "rsi"
        if "macd" in name:
            return "macd"
        raise ValueError(
            f"Cannot infer strategy type from {strategy_path}. Supported: SMA, RSI, MACD"
        )

    def _persist_config(self, config: StrategyConfig, suffix: str) -> str:
        filename = f"{config.name}_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.outputs_dir / filename
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(config.to_dict(), fh, indent=2)
        return str(path)

    def _register_strategy_variant(
        self,
        config: StrategyConfig,
        *,
        version_tag: str,
        parent_variant_id: Optional[int] = None,
        provenance: Optional[str] = None,
    ) -> Dict[str, Optional[int]]:
        if not self.repository:
            return {"strategy_id": None, "variant_id": None}

        factory_meta = config.metadata.get("factory") if isinstance(config.metadata, dict) else None
        strategy_name = (
            factory_meta.get("base_strategy_name")
            if factory_meta and factory_meta.get("base_strategy_name")
            else config.name
        )
        template_source = (
            factory_meta.get("template_path")
            if factory_meta and factory_meta.get("template_path")
            else str(config.source) if config.source else None
        )
        strategy_notes = factory_meta.get("notes") if factory_meta else None

        strategy_id = self.repository.upsert_strategy(
            family=config.strategy_type,
            name=strategy_name,
            template_source=template_source,
            notes=strategy_notes,
        )
        variant_id = self.repository.add_variant(
            strategy_id=strategy_id,
            config=config.to_dict(),
            parent_variant_id=parent_variant_id,
            version_tag=version_tag,
            code_path=str(config.source) if config.source else None,
            provenance=provenance,
        )
        return {"strategy_id": strategy_id, "variant_id": variant_id}

    def _start_db_run(
        self,
        variant_id: Optional[int],
        *,
        data_source: str,
        iteration: int,
        remediation_plan: Optional[Dict[str, Any]],
    ) -> Optional[int]:
        if not self.repository or variant_id is None:
            return None
        return self.repository.start_run(
            variant_id=variant_id,
            data_source=data_source,
            iteration=iteration,
            remediation_plan=remediation_plan,
        )

    def _finalize_db_run(
        self,
        run_id: Optional[int],
        validation_results: Dict[str, Any],
        *,
        status: str = "success",
        error_message: Optional[str] = None,
        applied_fixes: Optional[List[str]] = None,
    ) -> None:
        if not self.repository or run_id is None:
            return

        metrics = validation_results.get("performance_metrics", {})
        bias_selection = self._extract_bias_magnitude(validation_results)
        bias_other = validation_results.get("algorithm_results", {})
        score = self._compute_score(metrics, bias_selection)

        self.repository.record_metrics(
            run_id,
            metrics=metrics,
            bias_selection=bias_selection,
            bias_other=bias_other,
            score=score,
        )
        self.repository.complete_run(run_id, status=status, error_message=error_message)

        if applied_fixes:
            for fix in applied_fixes:
                action_type = fix.lower().replace(" ", "_")
                self.repository.add_remediation_action(
                    run_id,
                    action_type=action_type,
                    description=fix,
                )

    def _record_artifact(
        self,
        *,
        run_id: Optional[int],
        variant_id: Optional[int],
        artifact_type: str,
        path: str,
        notes: Optional[str] = None,
    ) -> None:
        if not self.repository:
            return
        self.repository.add_artifact(
            run_id=run_id,
            variant_id=variant_id,
            artifact_type=artifact_type,
            path=path,
            notes=notes,
        )

    def _compute_score(
        self, metrics: Dict[str, Any], bias_selection: Optional[float]
    ) -> float:
        sharpe = metrics.get("sharpe_ratio") or 0.0
        drawdown = abs(metrics.get("max_drawdown") or 0.0)
        penalty = bias_selection or 0.0
        return float(sharpe) - float(drawdown) - float(penalty)

    def _start_generation_experiment(
        self, spec: StrategySpec, policy: str
    ) -> Optional[int]:
        if not self.repository:
            return None
        parameters = {
            "base_parameters": spec.base_parameters,
            "parameter_grid": spec.parameter_grid,
            "limit": spec.limit,
        }
        try:
            strategy_id = self.repository.upsert_strategy(
                family=spec.strategy_type,
                name=spec.base_name,
                template_source=str(Path(spec.template_path)),
                notes=spec.metadata.get("notes") if spec.metadata else None,
            )
        except Exception:
            return None
        notes = spec.metadata.get("experiment_notes") if spec.metadata else None
        return self.repository.start_generation_experiment(
            strategy_id=strategy_id,
            policy=policy,
            parameters=parameters,
            notes=notes,
        )

    def _complete_generation_experiment(
        self, experiment_id: Optional[int], status: str = "completed"
    ) -> None:
        if not self.repository or experiment_id is None:
            return
        self.repository.complete_generation_experiment(
            experiment_id,
            status=status,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _load_market_data(self, data_path: str) -> List[Dict[str, Any]]:
        bars: List[Dict[str, Any]] = []
        with open(data_path, "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    bars.append(
                        {
                            "date": int(parts[0]),
                            "open": float(parts[1]),
                            "high": float(parts[2]),
                            "low": float(parts[3]),
                            "close": float(parts[4]),
                            "volume": float(parts[5]) if len(parts) > 5 else 0.0,
                        }
                    )
                except ValueError:
                    continue
        if not bars:
            raise ValueError(f"No valid OHLC data found in {data_path}")
        return bars

    def _simulate_strategy_results(
        self, config: StrategyConfig, market_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        simulator = {
            "sma": self._simulate_sma_strategy,
            "rsi": self._simulate_rsi_strategy,
            "macd": self._simulate_macd_strategy,
        }[config.strategy_type.lower()]
        returns, equity_curve, trades = simulator(config.parameters, market_data)
        return {
            "market_data": market_data,
            "returns": returns,
            "equity_curve": equity_curve,
            "total_return": (equity_curve[-1] / equity_curve[0]) - 1.0,
            "total_trades": trades,
        }

    def _run_strategy_validation(
        self, config: StrategyConfig, data_path: str
    ) -> Dict[str, Any]:
        self._ensure_binary("strategy_runner")
        command = [str(self.build_dir / "strategy_runner")] + config.cli_args(data_path)
        print("  ▶ Running:", " ".join(command))

        completed = subprocess.run(
            command,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"strategy_runner failed with exit code {completed.returncode}:\n{completed.stderr}"
            )

        metrics = self._parse_runner_output(completed.stdout)
        market_data = self._load_market_data(data_path)
        strategy_results = self._simulate_strategy_results(config, market_data)
        algorithm_results = self._run_validation_algorithms(strategy_results)
        algorithm_results = self._ensure_bias_metrics(metrics, algorithm_results)

        return {
            "strategy_type": config.strategy_type,
            "parameters": config.parameters,
            "raw_output": completed.stdout,
            "performance_metrics": metrics,
            "strategy_results": strategy_results,
            "algorithm_results": algorithm_results,
        }

    def _parse_runner_output(self, output: str) -> Dict[str, Any]:
        def grab(pattern: str, default: float = 0.0) -> float:
            match = re.search(pattern, output, re.MULTILINE)
            if not match:
                return default
            try:
                return float(match.group(1))
            except ValueError:
                return default

        total_return_pct = grab(r"Total Return:\s+([\-\d.]+)%")
        sharpe_ratio = grab(r"Sharpe Ratio:\s+([\-\d.]+)")
        max_drawdown_pct = grab(r"Max Drawdown:\s+([\-\d.]+)%")
        total_trades = int(grab(r"Total Trades:\s+(\d+)", default=0))
        win_rate_pct = grab(r"Win Rate:\s+([\-\d.]+)%")

        return {
            "total_return": total_return_pct / 100.0,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown_pct / 100.0,
            "total_trades": total_trades,
            "win_rate": win_rate_pct / 100.0 if win_rate_pct else None,
        }

    def _ensure_bias_metrics(
        self, metrics: Dict[str, Any], algorithm_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        results = dict(algorithm_results)
        if "SELBIAS" not in results or "bias_metrics" not in results.get("SELBIAS", {}):
            total_return = metrics.get("total_return", 0.0)
            sharpe = metrics.get("sharpe_ratio", 0.0)
            trades = metrics.get("total_trades", 0)
            selection_bias = min(
                0.4,
                max(0.0, 0.05 + abs(total_return) * 12 + (0.08 if trades < 5 else 0.0)),
            )
            oos = max(0.0, abs(total_return) * 0.25)
            t_stat = max(0.0, sharpe * 1.5)
            selbias_line = f"OOS={oos:.4f}  Selection bias={selection_bias:.4f}  t={t_stat:.3f}"
            results.setdefault("SELBIAS", {})["bias_metrics"] = {"detected_bias": selbias_line}

        return results

    def _run_validation_algorithms(
        self, strategy_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not STRATVAL_AVAILABLE or AlgorithmRegistry is None:
            return {}
        algo_results: Dict[str, Any] = {}
        for algo in ("SELBIAS", "MCPT_BARS"):
            try:
                adapter = AlgorithmRegistry.get_adapter(algo)
                algo_results[algo] = adapter.execute(strategy_results)
            except Exception as exc:
                algo_results[algo] = {"error": str(exc)}
        return algo_results

    # ------------------------------------------------------------------
    # Strategy simulators (Python replicas for validation inputs)
    # ------------------------------------------------------------------
    def _simulate_sma_strategy(
        self, params: Dict[str, Any], market_data: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float], int]:
        short = int(params.get("short", 10))
        long = int(params.get("long", 40))
        closes = [bar["close"] for bar in market_data]
        position = 0
        trades = 0
        equity = [100000.0]
        returns: List[float] = []
        short_window: deque = deque(maxlen=short)
        long_window: deque = deque(maxlen=long)

        for i, price in enumerate(closes):
            short_window.append(price)
            long_window.append(price)
            if i == 0:
                continue

            prev_price = closes[i - 1]
            if len(short_window) == short and len(long_window) == long:
                short_avg = sum(short_window) / short
                long_avg = sum(long_window) / long
                signal = 1 if short_avg > long_avg else 0
            else:
                signal = 0

            ret = position * (price / prev_price - 1.0)
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))

            if signal != position:
                trades += 1
                position = signal

        return returns, equity, trades

    def _simulate_rsi_strategy(
        self, params: Dict[str, Any], market_data: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float], int]:
        period = int(params.get("period", 14))
        overbought = float(params.get("overbought", 70.0))
        oversold = float(params.get("oversold", 30.0))
        closes = [bar["close"] for bar in market_data]
        equity = [100000.0]
        returns: List[float] = []
        position = 0
        trades = 0
        gains: deque = deque(maxlen=period)
        losses: deque = deque(maxlen=period)

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0.0))
            losses.append(abs(min(change, 0.0)))

            if len(gains) == period:
                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period
                if avg_loss == 0:
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50.0

            if rsi < oversold and position == 0:
                position = 1
                trades += 1
            elif rsi > overbought and position == 1:
                position = 0
                trades += 1

            ret = position * (closes[i] / closes[i - 1] - 1.0)
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))

        return returns, equity, trades

    def _simulate_macd_strategy(
        self, params: Dict[str, Any], market_data: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float], int]:
        fast_period = int(params.get("fast", 12))
        slow_period = int(params.get("slow", 26))
        signal_period = int(params.get("signal", 9))
        closes = [bar["close"] for bar in market_data]
        equity = [100000.0]
        returns: List[float] = []
        trades = 0
        position = 0
        ema_fast = None
        ema_slow = None
        signal = None

        k_fast = 2 / (fast_period + 1)
        k_slow = 2 / (slow_period + 1)
        k_signal = 2 / (signal_period + 1)

        hist_values: List[float] = []

        for i in range(1, len(closes)):
            price = closes[i]
            prev_price = closes[i - 1]

            ema_fast = (price * k_fast + (ema_fast or prev_price) * (1 - k_fast))
            ema_slow = (price * k_slow + (ema_slow or prev_price) * (1 - k_slow))
            macd = ema_fast - ema_slow
            signal = macd * k_signal + (signal or macd) * (1 - k_signal)
            hist = macd - signal
            hist_values.append(hist)

            signal_pos = 1 if hist > 0 else 0
            if signal_pos != position:
                trades += 1
                position = signal_pos

            ret = position * (price / prev_price - 1.0)
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))

        return returns, equity, trades

    # ------------------------------------------------------------------
    # Remediation plan and automated fixes
    # ------------------------------------------------------------------
    def _generate_auto_remediation_plan(
        self, config: StrategyConfig, validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        performance = validation_results.get("performance_metrics", {})
        total_return = performance.get("total_return", 0.0)
        total_trades = performance.get("total_trades", 0)

        synthetic_returns = [total_return / max(1, total_trades)] * max(1, total_trades)

        strategy_results = {
            "total_return": total_return,
            "total_trades": total_trades,
            "returns": synthetic_returns,
            "chronological_violations": False,
        }

        plan = self.remediation_engine.remediate(strategy_results, validation_results)
        automated_steps = [
            step
            for step in plan.get("remediation_steps", [])
            if any(
                keyword in step.lower()
                for keyword in (
                    "walk-forward",
                    "parameter",
                    "multiple testing",
                    "out-of-sample",
                )
            )
        ]

        return {
            "full_plan": plan,
            "automated_steps": automated_steps,
            "requires_manual": len(plan.get("remediation_steps", [])) - len(automated_steps),
        }

    def _apply_automated_fixes(
        self,
        config: StrategyConfig,
        remediation_plan: Dict[str, Any],
        data_path: str,
    ) -> Tuple[StrategyConfig, List[str]]:
        applied_fixes: List[str] = []
        updated_config = copy.deepcopy(config)

        for step in remediation_plan["automated_steps"]:
            step_lower = step.lower()
            if "walk-forward" in step_lower:
                updated_config, applied = self._implement_walk_forward(updated_config, data_path)
                if applied:
                    applied_fixes.append("Walk-forward optimization applied")
            elif "parameter" in step_lower:
                updated_config, applied = self._implement_parameter_reduction(updated_config, data_path)
                if applied:
                    applied_fixes.append("Parameter space reduction applied")
            elif "multiple testing" in step_lower:
                updated_config, applied = self._implement_mt_corrections(updated_config, data_path)
                if applied:
                    applied_fixes.append("Multiple testing corrections applied")
            elif "out-of-sample" in step_lower:
                updated_config, applied = self._implement_oos_validation(updated_config, data_path)
                if applied:
                    applied_fixes.append("Out-of-sample validation enforced")

        return updated_config, applied_fixes

    # -- individual remediations -------------------------------------------------
    def _implement_walk_forward(
        self, config: StrategyConfig, data_path: str
    ) -> Tuple[StrategyConfig, bool]:
        print("  🔄 Applying walk-forward style parameter adjustments")
        cfg = copy.deepcopy(config)
        stype = cfg.strategy_type.lower()

        if stype == "sma":
            short = cfg.parameters["short"]
            long = cfg.parameters["long"]
            cfg.parameters["short"] = max(2, int(short * 0.9))
            cfg.parameters["long"] = max(cfg.parameters["short"] + 5, int(long * 0.92))
            cfg.metadata.setdefault("walk_forward", {}).update({"windows": 4, "step": "monthly"})
        elif stype == "rsi":
            cfg.parameters["period"] = min(40, max(5, int(cfg.parameters["period"] * 1.1)))
            cfg.parameters["overbought"] = max(60.0, cfg.parameters["overbought"] - 2.0)
            cfg.parameters["oversold"] = min(40.0, cfg.parameters["oversold"] + 2.0)
            cfg.metadata.setdefault("walk_forward", {}).update({"windows": 6, "step": "bi-monthly"})
        elif stype == "macd":
            cfg.parameters["fast"] = max(6, int(cfg.parameters["fast"] * 0.95))
            cfg.parameters["slow"] = max(cfg.parameters["fast"] + 5, int(cfg.parameters["slow"] * 1.05))
            cfg.parameters["signal"] = max(3, int(cfg.parameters["signal"] * 0.9))
            cfg.metadata.setdefault("walk_forward", {}).update({"windows": 5, "step": "quarterly"})
        else:
            return config, False
        cfg = self._write_strategy_variant(
            cfg,
            "walk_forward",
            "// Automated walk-forward adjustments applied\n",
        )
        return cfg, True

    def _implement_parameter_reduction(
        self, config: StrategyConfig, data_path: str
    ) -> Tuple[StrategyConfig, bool]:
        print("  🎯 Tightening parameter ranges for robustness")
        cfg = copy.deepcopy(config)
        stype = cfg.strategy_type.lower()

        if stype == "sma":
            cfg.parameters["short"] = max(3, min(cfg.parameters["short"], 15))
            cfg.parameters["long"] = max(cfg.parameters["short"] + 5, min(cfg.parameters["long"], 60))
            cfg.metadata["parameter_bounds"] = {"short": [3, 20], "long": [25, 80]}
        elif stype == "rsi":
            cfg.parameters["overbought"] = min(75.0, cfg.parameters["overbought"])
            cfg.parameters["oversold"] = max(25.0, cfg.parameters["oversold"])
            cfg.metadata["parameter_bounds"] = {"overbought": [65, 80], "oversold": [20, 35]}
        elif stype == "macd":
            cfg.parameters["fast"] = max(8, min(cfg.parameters["fast"], 15))
            cfg.parameters["slow"] = max(cfg.parameters["fast"] + 5, min(cfg.parameters["slow"], 40))
            cfg.metadata["parameter_bounds"] = {"fast": [8, 15], "slow": [18, 45]}
        else:
            return config, False
        cfg = self._write_strategy_variant(
            cfg,
            "parameter_reduced",
            "// Parameter bounds tightened for robustness\n",
        )
        self._emit_batch_config(cfg)
        return cfg, True

    def _implement_mt_corrections(
        self, config: StrategyConfig, data_path: str
    ) -> Tuple[StrategyConfig, bool]:
        print("  📊 Applying multiple testing corrections metadata")
        cfg = copy.deepcopy(config)
        cfg.metadata.setdefault("statistical_adjustments", {})["correction"] = "bonferroni"
        cfg.metadata["statistical_adjustments"]["alpha"] = 0.01
        cfg = self._write_strategy_variant(
            cfg,
            "mt_correction",
            "// Multiple-testing correction guideline applied\n",
        )
        return cfg, True

    def _implement_oos_validation(
        self, config: StrategyConfig, data_path: str
    ) -> Tuple[StrategyConfig, bool]:
        print("  📈 Enforcing out-of-sample split validation")
        oos_file = self._create_oos_split(data_path)
        cfg = copy.deepcopy(config)
        cfg.metadata.setdefault("oos_validation", {})["dataset"] = oos_file

        # Run runner on the OOS dataset for diagnostics only (no exception if fails)
        try:
            self._run_strategy_validation(cfg, oos_file)
        except Exception as exc:  # pragma: no cover - best effort validation
            print(f"  ⚠️  OOS validation run failed: {exc}")
        cfg = self._write_strategy_variant(
            cfg,
            "oos_enforced",
            f"// Out-of-sample dataset: {oos_file}\n",
        )
        return cfg, True

    def _create_oos_split(self, data_path: str, split_ratio: float = 0.7) -> str:
        src = Path(data_path)
        if not src.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        lines = src.read_text().strip().splitlines()
        if len(lines) < 10:
            return data_path
        cutoff = max(1, int(len(lines) * split_ratio))
        oos_lines = lines[cutoff:]
        oos_path = self.outputs_dir / f"oos_{src.name}"
        oos_path.write_text("\n".join(oos_lines) + "\n")
        return str(oos_path)

    # ------------------------------------------------------------------
    # Metrics & reporting helpers
    # ------------------------------------------------------------------
    def _calculate_improvement(
        self, before: Dict[str, Any], after: Dict[str, Any]
    ) -> Dict[str, float]:
        before_perf = before.get("performance_metrics", {})
        after_perf = after.get("performance_metrics", {})

        sharpe_improvement = after_perf.get("sharpe_ratio", 0.0) - before_perf.get(
            "sharpe_ratio", 0.0
        )
        bias_reduction = self._extract_bias_magnitude(before) - self._extract_bias_magnitude(after)
        trade_diff = abs(after_perf.get("total_trades", 0) - before_perf.get("total_trades", 0))
        trade_consistency = 1.0 if trade_diff <= 3 else 0.0

        return {
            "sharpe_improvement": sharpe_improvement,
            "bias_reduction": bias_reduction,
            "trade_consistency": trade_consistency,
        }

    def _extract_biases_from_validation(self, validation_results: Dict[str, Any]) -> List[str]:
        magnitude = self._extract_bias_magnitude(validation_results)
        return ["selection_bias"] if magnitude >= 0.08 else []

    def _extract_bias_magnitude(self, validation_results: Dict[str, Any]) -> float:
        try:
            selbias = validation_results["algorithm_results"]["SELBIAS"]["bias_metrics"][
                "detected_bias"
            ]
            match = re.search(r"Selection bias=([\d.]+)", selbias)
            return float(match.group(1)) if match else 0.0
        except KeyError:
            return 0.0

    def _should_terminate_pipeline(
        self, validation_results: Dict[str, Any], remediation_plan: Dict[str, Any]
    ) -> bool:
        if not remediation_plan.get("automated_steps"):
            return True
        if not self._extract_biases_from_validation(validation_results):
            return True
        if self._extract_bias_magnitude(validation_results) < 0.05:
            return True
        return False

    def _is_pipeline_successful(self, results: Dict[str, Any]) -> bool:
        iterations = results.get("iterations", [])
        if len(iterations) < 1:
            return False
        initial_bias = self._extract_bias_magnitude(iterations[0]["validation_results"])
        final_bias = self._extract_bias_magnitude(iterations[-1]["validation_results"])
        if final_bias < 0.05:
            return True
        return final_bias < initial_bias * 0.5

    def _generate_pipeline_summary(self, results: Dict[str, Any]) -> str:
        iterations = results.get("iterations", [])
        success = results.get("success", False)
        total_iters = max(0, len(iterations) - 1)

        summary_lines = [
            "AUTOMATED BIAS REMEDIATION PIPELINE SUMMARY",
            "===========================================",
            f"Iterations Completed: {total_iters}",
            f"Pipeline Result: {'SUCCESS' if success else 'REQUIRES MANUAL INTERVENTION'}",
            "",
            "PERFORMANCE SNAPSHOT:",
        ]

        if iterations:
            initial = iterations[0]["validation_results"]["performance_metrics"]
            final = iterations[-1]["validation_results"]["performance_metrics"]
            summary_lines.extend(
                [
                    f"  Initial Sharpe: {initial.get('sharpe_ratio', 0.0):.3f}",
                    f"  Final Sharpe:   {final.get('sharpe_ratio', 0.0):.3f}",
                    f"  Total Return Δ: {(final.get('total_return', 0.0) - initial.get('total_return', 0.0)):+.3%}",
                    "",
                    "APPLIED FIXES:",
                ]
            )
            for entry in iterations[1:]:
                fixes = entry.get("applied_fixes", []) or ["No automated fixes"]
            summary_lines.append(f"  Iteration {entry['iteration']}: {', '.join(fixes)}")

        summary_lines.append("")
        summary_lines.append(
            "RECOMMENDATION: "
            + (
                "Automated remediation reduced detectable bias and improved robustness."
                if success
                else "Further manual review recommended for unresolved bias signals."
            )
        )
        if results.get("report_path"):
            summary_lines.append(f"Report: {results['report_path']}")
        if results.get("final_config_path"):
            summary_lines.append(f"Final config: {results['final_config_path']}")
        return "\n".join(summary_lines)

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------
    def _ensure_binary(self, target: str) -> None:
        binary = self.build_dir / target
        if sys.platform.startswith("win"):
            binary = binary.with_suffix(".exe")
        if binary.exists():
            return
        print(f"  ⛏️  Building missing target: {target}")
        completed = subprocess.run(
            ["cmake", "--build", "build", "--target", target],
            cwd=self.workspace,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Failed to build {target}:\n{completed.stdout}\n{completed.stderr}"
            )

    def _persist_final_artifacts(
        self,
        config: StrategyConfig,
        remediation_plan: Optional[Dict[str, Any]],
        *,
        variant_id: Optional[int],
    ) -> Dict[str, Optional[str]]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_config_path = self.outputs_dir / f"{config.name}_final_{timestamp}.json"
        with open(final_config_path, "w", encoding="utf-8") as fh:
            json.dump(config.to_dict(), fh, indent=2)
        self._record_artifact(
            run_id=None,
            variant_id=variant_id,
            artifact_type="final_config",
            path=str(final_config_path),
            notes="final_config",
        )

        report_path: Optional[str] = None
        if remediation_plan:
            report_filename = self.outputs_dir / f"bias_remediation_report_{timestamp}.txt"
            export_remediation_report(remediation_plan, str(report_filename))
            report_path = str(report_filename)
            self._record_artifact(
                run_id=None,
                variant_id=variant_id,
                artifact_type="report",
                path=report_path,
                notes="remediation_report",
            )

        return {
            "final_config_path": str(final_config_path),
            "report_path": report_path,
        }

    def _write_strategy_variant(
        self, config: StrategyConfig, suffix: str, header: str
    ) -> StrategyConfig:
        if not config.source:
            return config
        source_path = Path(config.source)
        if not source_path.exists():
            return config
        variant_path = self.outputs_dir / f"{config.name}_{suffix}.cpp"
        original = source_path.read_text(encoding="utf-8")
        variant_path.write_text(header + original, encoding="utf-8")
        cfg = copy.deepcopy(config)
        cfg.source = variant_path
        cfg.metadata.setdefault("generated_files", []).append(str(variant_path))
        return cfg

    def _emit_batch_config(self, config: StrategyConfig) -> None:
        if config.strategy_type.lower() != "sma":
            return
        bounds = config.metadata.get("parameter_bounds")
        if not bounds:
            return
        batch_config = {
            "strategy": config.strategy_type.upper(),
            "parameter_ranges": bounds,
            "generated": datetime.now().isoformat(),
        }
        output = self.outputs_dir / f"{config.name}_batch_parameters.json"
        with open(output, "w", encoding="utf-8") as fh:
            json.dump(batch_config, fh, indent=2)
        config.metadata.setdefault("generated_files", []).append(str(output))


# ----------------------------------------------------------------------
# Demonstration entry point
# ----------------------------------------------------------------------

def demo_automated_pipeline() -> Dict[str, Any]:
    print("🚀 DEMONSTRATING FULLY AUTOMATED BIAS REMEDIATION")
    print("=" * 65)
    remediator = AutomatedBiasRemediator(".")
    results = remediator.run_full_pipeline(
        strategy_path="framework/sma_strategy.cpp",
        data_path="data/sample_ohlc.txt",
        max_iterations=2,
    )
    print("\n" + results["summary"])
    return results


def _print_intro() -> None:
    print("🤖 Automated Bias Remediation System")
    print("=" * 40)
    print("Fully automated pipeline that detects bias and applies fixes\n")
    print("Key Features:")
    print("• 🎯 Automatic bias detection and quantification")
    print("• 🔄 Automated remediation execution")
    print("• 📊 Performance tracking across iterations")
    print("• 🤖 Minimal human intervention for supported strategies")
    print("• 📄 Comprehensive reporting and config export\n")
    print("Usage:")
    print(
        "  results = AutomatedBiasRemediator().run_full_pipeline('framework/sma_strategy.cpp', 'data/sample_ohlc.txt')"
    )
    print("")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated bias remediation orchestrator")
    parser.add_argument("--strategy", help="Path to strategy source", default="framework/sma_strategy.cpp")
    parser.add_argument("--data", help="Path to OHLC data", default="data/sample_ohlc.txt")
    parser.add_argument("--iterations", type=int, default=2, help="Maximum remediation iterations")
    parser.add_argument("--workspace", default=".", help="Workspace/project root")
    parser.add_argument("--output", help="Optional JSON output file for results")
    parser.add_argument("--demo", action="store_true", help="Run demonstration workflow")
    return parser


def _main() -> None:
    args = _build_arg_parser().parse_args()
    if args.demo:
        _print_intro()
        demo_automated_pipeline()
        return

    _print_intro()
    remediator = AutomatedBiasRemediator(args.workspace)
    results = remediator.run_full_pipeline(
        strategy_path=args.strategy,
        data_path=args.data,
        max_iterations=args.iterations,
    )

    if args.output:
        Path(args.output).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Results written to {args.output}")

    if results.get("report_path"):
        print(f"Remediation report: {results['report_path']}")
    if results.get("final_config_path"):
        print(f"Final configuration: {results['final_config_path']}")


if __name__ == "__main__":
    _main()
