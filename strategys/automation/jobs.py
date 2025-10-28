"""Job specifications for the automation controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from strategys.automated_bias_remediation import StrategySpec


@dataclass
class StrategyBatchJob:
    """Represents a batch strategy-generation and remediation job."""

    specs: List[StrategySpec]
    data_path: str
    max_iterations: int = 3
    policy: str = "grid"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "StrategyBatchJob":
        raw_specs = payload.get("specs") or []
        specs = []
        for spec in raw_specs:
            specs.append(
                StrategySpec(
                    base_name=spec["base_name"],
                    strategy_type=spec["strategy_type"],
                    template_path=spec["template_path"],
                    base_parameters=spec.get("base_parameters", {}),
                    parameter_grid=spec.get("parameter_grid", {}),
                    metadata=spec.get("metadata", {}),
                    limit=spec.get("limit"),
                )
            )
        return cls(
            specs=specs,
            data_path=payload["data_path"],
            max_iterations=payload.get("max_iterations", 3),
            policy=payload.get("policy", "grid"),
        )


def parse_job_spec(job_type: str, specification: Dict[str, Any]) -> Any:
    if job_type == "strategy_batch":
        return StrategyBatchJob.from_dict(specification)
    raise ValueError(f"Unsupported job type: {job_type}")
