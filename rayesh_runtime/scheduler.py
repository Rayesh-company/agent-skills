"""Dependency-frontier scheduling."""

from __future__ import annotations

from typing import Any

TERMINAL_PASS = {"accepted", "skipped"}


def frontier(workflow: dict[str, Any], node_states: dict[str, Any]) -> list[str]:
    ready: list[str] = []
    for node_id, node in workflow["nodes"].items():
        status = node_states.get(node_id, {}).get("status", "pending")
        if status != "pending":
            continue
        deps = node.get("depends_on", [])
        if all(node_states.get(dep, {}).get("status") in TERMINAL_PASS for dep in deps):
            ready.append(node_id)
    return ready
