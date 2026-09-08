"""Durable workflow-run state."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workflow_hash(workflow: dict[str, Any]) -> str:
    payload = json.dumps(workflow, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def new_node_state(node: dict[str, Any]) -> dict[str, Any]:
    criteria = node.get("acceptance", {}).get("criteria", [])
    return {
        "status": "pending",
        "attempt": 0,
        "evidence": [],
        "outputs": {},
        "iterations": [],
        "criteria": {
            f"C{index}": {
                "statement": statement,
                "evidence": [],
                "verified": False,
            }
            for index, statement in enumerate(criteria, start=1)
        },
    }


def new_run(goal: str, workflow: dict[str, Any]) -> dict[str, Any]:
    run_id = "rayesh-" + uuid.uuid4().hex[:12]
    return {
        "schema_version": 2,
        "run_id": run_id,
        "status": "active",
        "goal": goal,
        "created_at": _now(),
        "updated_at": _now(),
        "workflow": {
            "name": workflow["metadata"]["name"],
            "version": workflow["metadata"]["version"],
            "hash": workflow_hash(workflow),
        },
        "runtime_workflow": deepcopy(workflow),
        "node_states": {
            node_id: new_node_state(node)
            for node_id, node in workflow["nodes"].items()
        },
        "dynamic_nodes": {},
        "events": [],
    }


def append_event(run: dict[str, Any], event_type: str, **fields: Any) -> None:
    run["events"].append({"at": _now(), "type": event_type, **fields})
    run["updated_at"] = _now()


def save_run(run: dict[str, Any], directory: Path) -> Path:
    if not re.fullmatch(r"rayesh-[0-9a-f]{12}", run.get("run_id", "")):
        raise ValueError("invalid Rayesh run id")
    run_dir = Path(directory) / run["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "state.json"
    return save_run_file(run, path)


def save_run_file(run: dict[str, Any], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def load_run(path: Path) -> dict[str, Any]:
    run = json.loads(Path(path).read_text(encoding="utf-8"))
    version = run.get("schema_version", 1)
    if version == 1:
        for node_id, old_state in run["node_states"].items():
            node = run["runtime_workflow"]["nodes"][node_id]
            migrated = new_node_state(node)
            migrated.update(
                {
                    "status": old_state.get("status", "pending"),
                    "attempt": old_state.get("attempt", 0),
                    "evidence": old_state.get("evidence", []),
                }
            )
            if "summary" in old_state:
                migrated["summary"] = old_state["summary"]
            run["node_states"][node_id] = migrated
        run["status"] = run.get("status", "active")
        run["schema_version"] = 2
    elif version != 2:
        raise ValueError(f"unsupported run-state schema version {version!r}")
    return run
