#!/usr/bin/env python3
"""Validate all Rayesh YAML workflow graphs using stdlib only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rayesh_runtime.registry import WorkflowRegistry
from rayesh_runtime.validator import WorkflowValidationError


def validate(root: Path) -> list[str]:
    try:
        registry = WorkflowRegistry(root / "workflows", root / "skills")
        workflows = registry.discover()
    except (OSError, ValueError, WorkflowValidationError) as exc:
        return [str(exc)]
    if not workflows:
        return ["no workflows found"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("workflow validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
