"""Host-neutral Rayesh workflow engine.

The engine owns graph state, acceptance transitions, and adaptive gap nodes.
Actual subagent spawning is intentionally supplied by the host (Claude Code,
Codex, ChatGPT Work, etc.) so the workflow model is portable.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .registry import WorkflowRegistry
from .scheduler import frontier
from .state import append_event, new_run

VERDICTS = {"Accepted", "Not accepted", "Blocked", "Needs decision", "Stopped"}

GAP_SKILLS = {
    "knowledge": ["research-rpm"],
    "decision": ["wayfinder-rpm", "grill-with-docs-rpm"],
    "specification": ["grilling-rpm", "to-spec-rpm"],
    "design": ["codebase-design-rpm"],
    "runnable-uncertainty": ["prototype-rpm"],
    "behavior": ["implement-rpm", "tdd-rpm"],
    "test": ["tdd-rpm"],
    "dependency": ["project-management-rpm", "wizard-rpm"],
    "quality": ["code-review-rpm"],
    "evidence": ["project-management-rpm"],
    "state-drift": ["project-management-rpm"],
    "scope": ["project-management-rpm"],
}


class WorkflowEngine:
    def __init__(self, registry: WorkflowRegistry):
        self.registry = registry

    def plan(self, goal: str, workflow_name: str | None = None) -> dict[str, Any]:
        if workflow_name is None:
            workflow_name, score = self.registry.match(goal)
        else:
            score = 1.0
        workflow = deepcopy(self.registry.get(workflow_name))
        run = new_run(goal, workflow)
        append_event(run, "workflow_started", workflow=workflow_name, match_score=score)
        return run

    def frontier(self, run: dict[str, Any]) -> list[str]:
        return frontier(run["runtime_workflow"], run["node_states"])

    def record_result(
        self,
        run: dict[str, Any],
        node_id: str,
        *,
        verdict: str,
        evidence: list[Any] | None = None,
        gap: str | None = None,
        summary: str | None = None,
    ) -> None:
        if verdict not in VERDICTS:
            raise ValueError(f"invalid verdict {verdict!r}")
        if node_id not in run["node_states"]:
            raise KeyError(node_id)

        state = run["node_states"][node_id]
        state["attempt"] += 1
        state["evidence"].extend(evidence or [])
        if summary:
            state["summary"] = summary

        if verdict == "Accepted":
            state["status"] = "accepted"
            append_event(run, "node_accepted", node=node_id)
            return

        if verdict == "Stopped":
            state["status"] = "stopped"
            append_event(run, "node_stopped", node=node_id)
            return

        if verdict == "Blocked":
            state["status"] = "blocked"
            append_event(run, "node_blocked", node=node_id, gap=gap)
            return

        if verdict == "Needs decision" and not gap:
            gap = "decision"

        if gap:
            self.insert_gap_resolution(run, node_id, gap)
            append_event(run, "gap_detected", node=node_id, gap=gap, verdict=verdict)
        else:
            state["status"] = "not_accepted"
            append_event(run, "node_not_accepted", node=node_id)

    def insert_gap_resolution(self, run: dict[str, Any], origin: str, gap: str) -> str:
        skills = GAP_SKILLS.get(gap)
        if not skills:
            raise ValueError(f"unknown canonical gap {gap!r}")

        workflow = run["runtime_workflow"]
        origin_node = workflow["nodes"][origin]
        index = 1
        base = f"resolve-{origin}-{gap}".replace("_", "-")
        node_id = base
        while node_id in workflow["nodes"]:
            index += 1
            node_id = f"{base}-{index}"

        resolution = {
            "type": "agent",
            "depends_on": list(origin_node.get("depends_on", [])),
            "agent": {
                "role": f"{gap}-gap-resolver",
                "skills": skills,
            },
            "task": f"Resolve the {gap} gap discovered by node {origin}.",
            "acceptance": {
                "criteria": [
                    f"The {gap} gap is resolved with inspectable evidence or an authorized decision.",
                    f"Node {origin} has enough updated context to retry with a materially changed state.",
                ]
            },
        }

        workflow["nodes"][node_id] = resolution
        run["node_states"][node_id] = {"status": "pending", "attempt": 0, "evidence": []}
        run["dynamic_nodes"][node_id] = {"origin": origin, "gap": gap}
        deps = list(origin_node.get("depends_on", []))
        deps.append(node_id)
        origin_node["depends_on"] = deps
        run["node_states"][origin]["status"] = "pending"
        append_event(run, "dynamic_node_inserted", node=node_id, origin=origin, gap=gap)
        return node_id
