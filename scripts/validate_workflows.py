#!/usr/bin/env python3
"""Validate all Rayesh YAML workflow graphs using stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rayesh_runtime.registry import WorkflowRegistry
from rayesh_runtime.validator import WorkflowValidationError, schema_document


def validate(root: Path) -> list[str]:
    schema_path = root / "workflow-schema" / "workflow.schema.json"
    expected_schema = json.dumps(schema_document(), indent=2) + "\n"
    try:
        actual_schema = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [str(exc)]
    if actual_schema != expected_schema:
        return ["workflow schema is stale; run validate_workflows.py --write-schema"]
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
    parser.add_argument("--write-schema", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.write_schema:
        path = root / "workflow-schema" / "workflow.schema.json"
        path.write_text(json.dumps(schema_document(), indent=2) + "\n", encoding="utf-8")
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("workflow validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
