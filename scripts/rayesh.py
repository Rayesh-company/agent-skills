#!/usr/bin/env python3
"""Inspect Rayesh workflow selection and graph state without spawning agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rayesh_runtime.engine import WorkflowEngine
from rayesh_runtime.registry import WorkflowRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("goal")
    plan.add_argument("--workflow")

    args = parser.parse_args(argv)
    registry = WorkflowRegistry(ROOT / "workflows", ROOT / "skills")
    engine = WorkflowEngine(registry)

    if args.command == "plan":
        run = engine.plan(args.goal, args.workflow)
        payload = {
            "run_id": run["run_id"],
            "workflow": run["workflow"],
            "goal": run["goal"],
            "frontier": engine.frontier(run),
        }
        print(json.dumps(payload, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
