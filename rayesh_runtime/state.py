"""Durable workflow-run state."""

from __future__ import annotations

import hashlib
import json
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


def new_run(goal: str, workflow: dict[str, Any]) -> dict[str, Any]:
    run_id = "rayesh-" + uuid.uuid4().hex[:12]
    return {
        "schema_version": 1,
        "run_id": run_id,
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
            node_id: {"status": "pending", "attempt": 0, "evidence": []}
            for node_id in workflow["nodes"]
        },
        "dynamic_nodes": {},
        "events": [],
    }


def append_event(run: dict[str, Any], event_type: str, **fields: Any) -> None:
    run["events"].append({"at": _now(), "type": event_type, **fields})
    run["updated_at"] = _now()


def save_run(run: dict[str, Any], directory: Path) -> Path:
    run_dir = Path(directory) / run["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "state.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def load_run(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
