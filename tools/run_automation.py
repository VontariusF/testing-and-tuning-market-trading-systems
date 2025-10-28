#!/usr/bin/env python3
"""CLI entry point for running the automation controller."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from strategys.automation import AutomationController
from strategys.db import StrategyRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run strategy automation jobs (batch or continuous)",
    )
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent),
        help="Project workspace containing freqtrade_db and build artifacts.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the SQLite database (defaults to <workspace>/freqtrade_db).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=60.0,
        help="Polling interval in seconds when running continuously.",
    )
    parser.add_argument(
        "--run-forever",
        action="store_true",
        help="Run the controller loop continuously instead of processing a single job.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity for controller output.",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(args.log_level)

    workspace = Path(args.workspace).resolve()
    db_path = Path(args.db).resolve() if args.db else workspace / "freqtrade_db"

    repository = StrategyRepository(db_path)
    controller = AutomationController(
        repository,
        workspace=str(workspace),
        poll_interval=args.poll_interval,
    )

    if args.run_forever:
        controller.run_forever()
    else:
        controller.run_once()
    return 0


if __name__ == "__main__":
    sys.exit(main())
