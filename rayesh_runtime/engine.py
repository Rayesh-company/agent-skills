"""Host-neutral Rayesh workflow engine.

The engine owns graph expansion, run transitions, and acceptance evaluation.
Hosts execute the ready work descriptors and return criterion-level evidence.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from typing import Any, Callable

from .acceptance import Criterion, GAP_ROUTES, Iteration, evaluate, progress_guard, select_gap
from .registry import WorkflowRegistry
from .scheduler import frontier
from .state import append_event, new_node_state, new_run, workflow_hash

WORKER_VERDICTS = {"Accepted", "Not accepted", "Blocked", "Needs decision", "Stopped"}
DEFAULT_MAX_PARALLEL_AGENTS = 4

# Canonical routes that name a responsibility rather than an installable skill
# are adapted here to the operational skill that owns the work.
ROUTE_SKILL_ADAPTERS = {
    "acceptance-authority": "project-management-rpm",
    "owning-execution-skill": "project-management-rpm",
    "tracker-reconcile": "project-management-rpm",
}


class WorkflowEngine:
    def __init__(
        self,
        registry: WorkflowRegistry,
        canonical_state_reader: Callable[[], dict[str, Any]] | None = None,
    ):
        self.registry = registry
        self.canonical_state_reader = canonical_state_reader

    def plan(self, goal: str, workflow_name: str | None = None) -> dict[str, Any]:
        if workflow_name is None:
            workflow_name, score = self.registry.match(goal)
        else:
            score = 1.0
        workflow = deepcopy(self.registry.get(workflow_name))
        run = new_run(goal, workflow)
        if self.canonical_state_reader:
            run["canonical_state"] = self.canonical_state_reader()
        append_event(run, "workflow_started", workflow=workflow_name, match_score=score)
        return run

    def frontier(self, run: dict[str, Any]) -> list[str]:
        if run.get("status", "active") != "active":
            return []
        self._expand_structural_nodes(run)
        ready = frontier(run["runtime_workflow"], run["node_states"])
        if (
            not ready
            and not any(state["status"] == "running" for state in run["node_states"].values())
            and not self._workflow_is_accepted(run)
        ):
            run["status"] = "stalled"
            append_event(
                run,
                "workflow_stalled",
                gap="state-drift",
                route=GAP_ROUTES["state-drift"],
            )
        return ready

    def execution_descriptor(self, run: dict[str, Any], node_id: str) -> dict[str, Any]:
        if node_id not in self.frontier(run):
            raise ValueError(f"node {node_id!r} is not ready")
        node = run["runtime_workflow"]["nodes"][node_id]
        return {
            "node": node_id,
            "type": node["type"],
            "agent": node.get("agent"),
            "task": node.get("task"),
            "workspace": node.get("workspace", "readonly"),
            "inputs": node.get("inputs", {}),
            "acceptance": run["node_states"][node_id]["criteria"],
            "authority_required": node["type"] == "human",
        }

    def claim(self, run: dict[str, Any], node_id: str) -> dict[str, Any]:
        descriptor = self.execution_descriptor(run, node_id)
        running = [
            current_id
            for current_id, state in run["node_states"].items()
            if state["status"] == "running"
        ]
        maximum = run["runtime_workflow"].get("policies", {}).get(
            "max_parallel_agents", DEFAULT_MAX_PARALLEL_AGENTS
        )
        if len(running) >= maximum:
            raise ValueError(f"max_parallel_agents limit reached ({maximum})")
        if (running and descriptor["workspace"] == "shared") or any(
            run["runtime_workflow"]["nodes"][current_id].get("workspace", "readonly")
            == "shared"
            for current_id in running
        ):
            raise ValueError("shared workspace collides with a running node")
        run["node_states"][node_id]["status"] = "running"
        append_event(run, "node_started", node=node_id)
        return descriptor

    def stop(self, run: dict[str, Any], *, summary: str | None = None) -> None:
        if run.get("status") == "accepted":
            raise ValueError("an accepted workflow cannot be stopped")
        run["status"] = "stopped"
        append_event(run, "workflow_stopped", summary=summary)

    def resume(self, run: dict[str, Any]) -> None:
        status = run.get("status", "active")
        if status == "accepted":
            raise ValueError("an accepted workflow cannot be resumed")
        current = self.registry.get(run["workflow"]["name"])
        current_identity = (current["metadata"]["version"], workflow_hash(current))
        pinned_identity = (run["workflow"]["version"], run["workflow"]["hash"])
        if current_identity != pinned_identity:
            run["status"] = "blocked"
            append_event(
                run,
                "workflow_drift_detected",
                pinned={"version": pinned_identity[0], "hash": pinned_identity[1]},
                current={"version": current_identity[0], "hash": current_identity[1]},
                route=GAP_ROUTES["state-drift"],
            )
            return
        if self.canonical_state_reader:
            current_state = self.canonical_state_reader()
            if current_state.get("state_agrees") is not True:
                run["status"] = "blocked"
                append_event(
                    run,
                    "canonical_state_drift_detected",
                    before=run.get("canonical_state"),
                    current=current_state,
                    route=GAP_ROUTES["state-drift"],
                )
                return
            changes = {
                key: {"before": run.get("canonical_state", {}).get(key), "current": value}
                for key, value in current_state.items()
                if run.get("canonical_state", {}).get(key) != value
            }
            run["canonical_state"] = current_state
            append_event(
                run,
                "canonical_state_reconciled",
                state=current_state,
                changes=changes,
            )
        if status == "active":
            return
        origins_with_resolvers = {
            metadata["origin"]
            for metadata in run["dynamic_nodes"].values()
            if "origin" in metadata
        }
        for node_id, state in run["node_states"].items():
            if state["status"] in {"stopped", "stalled"} or (
                state["status"] == "blocked" and node_id not in origins_with_resolvers
            ):
                state["status"] = "pending"
        run["status"] = "active"
        append_event(run, "workflow_resumed", previous_status=status)

    def record_result(
        self,
        run: dict[str, Any],
        node_id: str,
        *,
        verdict: str,
        criteria: dict[str, dict[str, Any]] | None = None,
        evidence: list[Any] | None = None,
        outputs: dict[str, Any] | None = None,
        gaps: list[str] | None = None,
        gap: str | None = None,
        summary: str | None = None,
        authority_confirmed: bool = False,
        critical_findings: int | None = None,
        state_agrees: bool | None = None,
    ) -> None:
        if verdict not in WORKER_VERDICTS:
            raise ValueError(f"invalid verdict {verdict!r}")
        if critical_findings is not None and (
            not isinstance(critical_findings, int)
            or isinstance(critical_findings, bool)
            or critical_findings < 0
        ):
            raise ValueError("critical_findings must be a non-negative integer")
        if state_agrees is not None and not isinstance(state_agrees, bool):
            raise ValueError("state_agrees must be boolean")
        if outputs is not None and not isinstance(outputs, dict):
            raise ValueError("outputs must be a mapping")
        if evidence is not None and (
            not isinstance(evidence, list)
            or not all(isinstance(item, str) and item for item in evidence)
        ):
            raise ValueError("evidence must be a list of non-empty pointers")
        if node_id not in run["node_states"]:
            raise KeyError(node_id)
        if run.get("status", "active") != "active":
            raise ValueError(f"workflow is {run['status']!r}, not active")

        state = run["node_states"][node_id]
        ready = node_id in self.frontier(run)
        if not ready and state["status"] != "running":
            raise ValueError(f"node {node_id!r} is not ready or running")

        submitted_gaps = list(gaps or [])
        if gap:
            submitted_gaps.append(gap)
        if verdict == "Needs decision" and not submitted_gaps:
            submitted_gaps.append("decision")
        if verdict in {"Not accepted", "Blocked"} and not submitted_gaps:
            raise ValueError(f"{verdict} requires at least one canonical gap")
        selected_gap = select_gap(submitted_gaps)[0] if submitted_gaps else None
        if verdict == "Accepted" and selected_gap:
            raise ValueError("Accepted cannot include an unresolved gap")

        projected_criteria = deepcopy(state["criteria"])
        self._apply_criterion_updates(projected_criteria, criteria or {})
        if verdict == "Accepted" and (critical_findings is None or state_agrees is None):
            raise ValueError("Accepted requires critical-findings and state-agreement results")
        observed_canonical_state = None
        if self.canonical_state_reader:
            observed_canonical_state = self.canonical_state_reader()
            state_agrees = bool(state_agrees) and observed_canonical_state.get("state_agrees") is True
        node = run["runtime_workflow"]["nodes"][node_id]
        evaluated = evaluate(
            [
                Criterion(
                    key,
                    self._criterion_has_current_evidence(value, run["created_at"]),
                    self._criterion_verified(value, run["created_at"]),
                )
                for key, value in projected_criteria.items()
            ],
            critical_findings=critical_findings or 0,
            state_agrees=bool(state_agrees),
            authority_required=node["type"] == "human",
            authority_confirmed=authority_confirmed,
            blocked=verdict == "Blocked",
        )
        if verdict == "Accepted" and evaluated != "Accepted":
            missing = [
                key
                for key, value in projected_criteria.items()
                if not self._criterion_verified(value, run["created_at"])
            ]
            if node["type"] == "human" and not authority_confirmed:
                raise ValueError("human acceptance requires authority confirmation")
            if critical_findings:
                raise ValueError("Accepted requires zero critical findings")
            if state_agrees is not True:
                raise ValueError("Accepted requires canonical and mirrored state agreement")
            raise ValueError(f"Accepted requires verified evidence for: {', '.join(missing)}")
        if verdict == "Accepted" and not self._root_evidence_is_independent(
            run, node_id, projected_criteria
        ):
            raise ValueError("root gate requires evidence independent from child nodes")

        state["attempt"] += 1
        state["criteria"] = projected_criteria
        for item in evidence or []:
            if item not in state["evidence"]:
                state["evidence"].append(item)
        state["outputs"].update(outputs or {})
        if observed_canonical_state is not None:
            run["canonical_state"] = observed_canonical_state
            append_event(
                run,
                "canonical_state_evaluated",
                node=node_id,
                state=observed_canonical_state,
                agrees=state_agrees,
            )
        if summary:
            state["summary"] = summary

        if verdict == "Accepted":
            state["status"] = "accepted"
            state["next_action"] = None
            append_event(run, "node_accepted", node=node_id)
            dynamic = run["dynamic_nodes"].get(node_id, {})
            if "origin" in dynamic:
                run["node_states"][dynamic["origin"]]["status"] = "pending"
            if self._workflow_is_accepted(run):
                run["status"] = "accepted"
                append_event(run, "workflow_accepted")
            return
        if verdict == "Stopped":
            state["status"] = "stopped"
            run["status"] = "stopped"
            append_event(run, "node_stopped", node=node_id)
            return
        if verdict == "Blocked":
            self.insert_gap_resolution(run, node_id, selected_gap)
            state["status"] = "blocked"
            state["next_action"] = select_gap([selected_gap])[1]
            run["status"] = "blocked"
            append_event(
                run,
                "node_blocked",
                node=node_id,
                gap=selected_gap,
                route=state["next_action"],
            )
            return

        if selected_gap:
            fingerprint = self._evidence_fingerprint(
                projected_criteria,
                [*state["evidence"]],
                {**state["outputs"]},
            )
            route = select_gap([selected_gap])[1]
            state["next_action"] = route
            state["iterations"].append(
                {"scope": node_id, "gap": selected_gap, "evidence_fingerprint": fingerprint, "verdict": verdict, "next_actions": [route]}
            )
            recent = [Iteration(**item) for item in state["iterations"][-2:]]
            if progress_guard(recent) == "Stalled":
                state["status"] = "stalled"
                run["status"] = "stalled"
                append_event(run, "node_stalled", node=node_id, gap=selected_gap, route=route)
                return
            self.insert_gap_resolution(run, node_id, selected_gap)
            append_event(run, "gap_detected", node=node_id, gap=selected_gap, verdict=verdict)

    def insert_gap_resolution(self, run: dict[str, Any], origin: str, gap: str) -> str:
        route = GAP_ROUTES[gap]
        skills = [ROUTE_SKILL_ADAPTERS.get(route, route)]
        workflow = run["runtime_workflow"]
        origin_node = workflow["nodes"][origin]
        base = f"resolve-{origin}-{gap}".replace("_", "-")
        node_id = base
        index = 1
        while node_id in workflow["nodes"]:
            index += 1
            node_id = f"{base}-{index}"
        resolution = {
            "type": "agent",
            "depends_on": list(origin_node.get("depends_on", [])),
            "agent": {"role": f"{gap}-gap-resolver", "skills": skills},
            "task": f"Resolve the {gap} gap discovered by node {origin}.",
            "acceptance": {"criteria": [
                f"The {gap} gap is resolved with inspectable evidence or an authorized decision.",
                f"Node {origin} has enough updated context to retry with a materially changed state.",
            ]},
        }
        workflow["nodes"][node_id] = resolution
        run["node_states"][node_id] = new_node_state(resolution)
        run["dynamic_nodes"][node_id] = {"origin": origin, "gap": gap}
        origin_node.setdefault("depends_on", []).append(node_id)
        run["node_states"][origin]["status"] = "pending"
        append_event(run, "dynamic_node_inserted", node=node_id, origin=origin, gap=gap)
        return node_id

    @staticmethod
    def _apply_criterion_updates(current: dict[str, dict[str, Any]], updates: dict[str, dict[str, Any]]) -> None:
        unknown = sorted(set(updates) - set(current))
        if unknown:
            raise ValueError(f"unknown criteria: {', '.join(unknown)}")
        for criterion_id, update in updates.items():
            if not isinstance(update, dict):
                raise ValueError(f"criterion {criterion_id} update must be a mapping")
            evidence = update.get("evidence", [])
            if not isinstance(evidence, list):
                raise ValueError(f"criterion {criterion_id} evidence must be a list")
            for record in evidence:
                if not isinstance(record, dict):
                    raise ValueError(f"criterion {criterion_id} evidence must contain records")
                required = {"pointer", "relation", "verification", "validated_at", "passed"}
                if not required.issubset(record):
                    raise ValueError(f"criterion {criterion_id} evidence record is incomplete")
                if record["relation"] not in {"proves", "supports", "contradicts", "does-not-address"}:
                    raise ValueError(f"criterion {criterion_id} evidence relation is invalid")
                if not all(isinstance(record[key], str) and record[key] for key in ["pointer", "verification", "validated_at"]):
                    raise ValueError(f"criterion {criterion_id} evidence metadata must be non-empty strings")
                if not isinstance(record["passed"], bool):
                    raise ValueError(f"criterion {criterion_id} evidence passed must be boolean")
                try:
                    validated_at = datetime.fromisoformat(record["validated_at"])
                except ValueError as exc:
                    raise ValueError(
                        f"criterion {criterion_id} validated_at must be ISO-8601"
                    ) from exc
                if validated_at.tzinfo is None:
                    raise ValueError(f"criterion {criterion_id} validated_at must include a timezone")
            for record in evidence:
                if record not in current[criterion_id]["evidence"]:
                    current[criterion_id]["evidence"].append(record)
            current[criterion_id]["verified"] = any(
                item["relation"] == "proves" and item["passed"]
                for item in current[criterion_id]["evidence"]
            )

    @staticmethod
    def _evidence_fingerprint(
        criteria: dict[str, Any], evidence: list[Any], outputs: dict[str, Any]
    ) -> str:
        payload = json.dumps(
            {"criteria": criteria, "evidence": evidence, "outputs": outputs},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _criterion_has_current_evidence(criterion: dict[str, Any], created_at: str) -> bool:
        created = datetime.fromisoformat(created_at)
        return any(
            datetime.fromisoformat(item["validated_at"]) >= created
            for item in criterion["evidence"]
        )

    @classmethod
    def _criterion_verified(cls, criterion: dict[str, Any], created_at: str) -> bool:
        created = datetime.fromisoformat(created_at)
        return any(
            datetime.fromisoformat(item["validated_at"]) >= created
            and item["relation"] == "proves"
            and item["passed"]
            for item in criterion["evidence"]
        )

    @classmethod
    def _root_evidence_is_independent(
        cls,
        run: dict[str, Any],
        node_id: str,
        projected: dict[str, dict[str, Any]],
    ) -> bool:
        nodes = run["runtime_workflow"]["nodes"]
        referenced = {dep for node in nodes.values() for dep in node.get("depends_on", [])}
        if node_id in referenced or nodes[node_id]["type"] != "gate":
            return True
        child_records = [
            record
            for child_id, state in run["node_states"].items()
            if child_id != node_id
            for criterion in state["criteria"].values()
            for record in criterion["evidence"]
            if record["relation"] == "proves" and record["passed"]
        ]
        child_pointers = {record["pointer"] for record in child_records}
        child_methods = {record["verification"] for record in child_records}
        accepted_times = [
            datetime.fromisoformat(event["at"])
            for event in run["events"]
            if event["type"] == "node_accepted" and event.get("node") != node_id
        ]
        latest_child_acceptance = max(accepted_times) if accepted_times else None
        for criterion in projected.values():
            independent = any(
                record["relation"] == "proves"
                and record["passed"]
                and record["pointer"] not in child_pointers
                and record["verification"] not in child_methods
                and (
                    latest_child_acceptance is None
                    or datetime.fromisoformat(record["validated_at"]) >= latest_child_acceptance
                )
                for record in criterion["evidence"]
            )
            if not independent:
                return False
        return True

    @staticmethod
    def _workflow_is_accepted(run: dict[str, Any]) -> bool:
        nodes = run["runtime_workflow"]["nodes"]
        referenced = {dep for node in nodes.values() for dep in node.get("depends_on", [])}
        terminals = [node_id for node_id in nodes if node_id not in referenced]
        return bool(terminals) and all(
            nodes[node_id]["type"] == "gate"
            and run["node_states"][node_id]["status"] == "accepted"
            for node_id in terminals
        )

    def _expand_structural_nodes(self, run: dict[str, Any]) -> None:
        while True:
            ready = frontier(run["runtime_workflow"], run["node_states"])
            structural = [node_id for node_id in ready if run["runtime_workflow"]["nodes"][node_id]["type"] in {"foreach", "workflow"}]
            if not structural:
                return
            for node_id in structural:
                node = run["runtime_workflow"]["nodes"][node_id]
                if node["type"] == "foreach":
                    self._expand_foreach(run, node_id)
                else:
                    self._expand_nested_workflow(run, node_id)

    def _expand_foreach(self, run: dict[str, Any], node_id: str) -> None:
        workflow = run["runtime_workflow"]
        node = workflow["nodes"][node_id]
        source = node["foreach"]["source"]
        items = self._resolve_output(run, source)
        if not isinstance(items, list):
            raise ValueError(f"foreach source {source!r} must resolve to a list")
        child_ids = []
        parallel = node["foreach"].get("parallel", False)
        for index, item in enumerate(items, start=1):
            child_id = f"{node_id}[{index}]"
            child = deepcopy(node)
            child["type"] = "agent"
            child.pop("foreach", None)
            child["inputs"] = {"item": item, "index": index, "source": source}
            if not parallel and child_ids:
                child["depends_on"] = [child_ids[-1]]
            workflow["nodes"][child_id] = child
            run["node_states"][child_id] = new_node_state(child)
            child_ids.append(child_id)
        node["type"] = "gate"
        node.pop("agent", None)
        node.pop("foreach", None)
        node["depends_on"] = child_ids or list(node.get("depends_on", []))
        run["dynamic_nodes"][node_id] = {"kind": "foreach", "children": child_ids, "source": source}
        append_event(run, "foreach_expanded", node=node_id, children=child_ids)

    def _expand_nested_workflow(self, run: dict[str, Any], node_id: str) -> None:
        workflow = run["runtime_workflow"]
        node = workflow["nodes"][node_id]
        nested = deepcopy(self.registry.get(node["workflow"]))
        mapping = {child_id: f"{node_id}::{child_id}" for child_id in nested["nodes"]}
        referenced = {dep for child in nested["nodes"].values() for dep in child.get("depends_on", [])}
        terminal_ids = [mapping[child_id] for child_id in nested["nodes"] if child_id not in referenced]
        outer_deps = list(node.get("depends_on", []))
        for child_id, child in nested["nodes"].items():
            expanded = deepcopy(child)
            child_deps = child.get("depends_on", [])
            expanded["depends_on"] = [mapping[dep] for dep in child_deps] or outer_deps
            expanded_id = mapping[child_id]
            workflow["nodes"][expanded_id] = expanded
            run["node_states"][expanded_id] = new_node_state(expanded)
        node["type"] = "gate"
        node.pop("workflow", None)
        node["depends_on"] = terminal_ids
        run["dynamic_nodes"][node_id] = {"kind": "workflow", "workflow": nested["metadata"]["name"], "children": list(mapping.values())}
        append_event(run, "workflow_expanded", node=node_id, children=list(mapping.values()))

    @staticmethod
    def _resolve_output(run: dict[str, Any], source: str) -> Any:
        parts = source.split(".")
        if len(parts) < 2 or parts[0] not in run["node_states"]:
            raise ValueError(f"invalid foreach source {source!r}")
        value: Any = run["node_states"][parts[0]]["outputs"]
        for part in parts[1:]:
            if not isinstance(value, dict) or part not in value:
                raise ValueError(f"foreach source {source!r} has no value")
            value = value[part]
        return value
