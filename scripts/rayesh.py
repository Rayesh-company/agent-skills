#!/usr/bin/env python3
"""Inspect Rayesh workflow selection and graph state without spawning agents."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rayesh_runtime.engine import DEFAULT_MAX_PARALLEL_AGENTS, WORKER_VERDICTS, WorkflowEngine
from rayesh_runtime.registry import WorkflowRegistry
from rayesh_runtime.state import load_run, save_run, save_run_file


DEFAULT_RUNS_DIR = ROOT / ".rayesh" / "runs"


def _canonical_state() -> dict:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    conflicts = [item for item in git("diff", "--name-only", "--diff-filter=U").splitlines() if item]
    documents = [path for path in [ROOT / "CONTEXT.md", *sorted((ROOT / "docs").glob("**/*.md"))] if path.is_file()]
    return {
        "state_agrees": not conflicts,
        "git_head": git("rev-parse", "HEAD"),
        "unmerged_paths": conflicts,
        "documents": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in documents
        },
        "tracker_configured": (ROOT / "docs" / "agents" / "issue-tracker.md").is_file(),
    }


@contextmanager
def _run_lock(path: Path):
    lock_path = path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _add_runs_dir(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)


def _run_path(target: str, runs_dir: Path) -> Path:
    explicit = Path(target)
    if explicit.is_file():
        return explicit
    candidate = runs_dir / target / "state.json"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(f"run state not found: {target}")


def _summary(engine: WorkflowEngine, run: dict) -> dict:
    ready = engine.frontier(run)
    nodes = run["runtime_workflow"]["nodes"]
    node_states = run["node_states"]
    graph = {
        node_id: {
            "type": node["type"],
            "depends_on": node.get("depends_on", []),
            "status": node_states[node_id]["status"],
        }
        for node_id, node in nodes.items()
    }
    human_checkpoints = [node_id for node_id, node in nodes.items() if node["type"] == "human"]
    waiting = [
        node_id
        for node_id, state in node_states.items()
        if state["status"] == "pending" and node_id not in ready
    ]
    status = run.get("status", "active")
    if ready:
        next_transition = f"execute frontier: {', '.join(ready)}"
    elif status == "stopped":
        next_transition = "resume the run"
    elif status == "blocked":
        next_transition = "resolve the recorded blocker or state drift"
    elif status == "stalled":
        next_transition = "route to specification, design, research, scope, or human authority"
    elif status == "accepted":
        next_transition = "terminal: workflow accepted"
    else:
        next_transition = "no executable transition"
    return {
        "run_id": run["run_id"],
        "status": status,
        "workflow": run["workflow"],
        "goal": run["goal"],
        "frontier": ready,
        "running": [node_id for node_id, state in node_states.items() if state["status"] == "running"],
        "accepted": [node_id for node_id, state in node_states.items() if state["status"] == "accepted"],
        "blocked": [node_id for node_id, state in node_states.items() if state["status"] == "blocked"],
        "waiting": waiting,
        "human_checkpoints": human_checkpoints,
        "parallelism": {
            "max_agents": run["runtime_workflow"].get("policies", {}).get(
                "max_parallel_agents", DEFAULT_MAX_PARALLEL_AGENTS
            ),
            "ready_count": len(ready),
        },
        "next_transition": next_transition,
        "graph": graph,
        "nodes": node_states,
    }


def _keyed_values(values: list[str], label: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for value in values:
        criterion_id, separator, item = value.partition("=")
        if not separator or not criterion_id or not item:
            raise ValueError(f"{label} must use C<number>=<value>")
        parsed.setdefault(criterion_id, []).append(item)
    return parsed


def _criterion_updates(evidence_values: list[str], verification_values: list[str]) -> dict[str, dict]:
    evidence = _keyed_values(evidence_values, "criterion evidence")
    verifications = _keyed_values(verification_values, "criterion verification")
    if set(evidence) != set(verifications):
        raise ValueError("every criterion evidence entry requires a matching verification method")
    updates: dict[str, dict] = {}
    validated_at = datetime.now(timezone.utc).isoformat()
    for criterion_id, pointers in evidence.items():
        methods = verifications[criterion_id]
        if len(methods) != 1:
            raise ValueError(f"criterion {criterion_id} requires exactly one verification method")
        updates[criterion_id] = {
            "evidence": [
                {
                    "pointer": pointer,
                    "relation": "proves",
                    "verification": methods[0],
                    "validated_at": validated_at,
                    "passed": True,
                }
                for pointer in pointers
            ]
        }
    return updates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan")
    plan.add_argument("goal")
    plan.add_argument("--workflow")

    start = sub.add_parser("start")
    start.add_argument("goal")
    start.add_argument("--workflow")
    _add_runs_dir(start)

    status = sub.add_parser("status")
    status.add_argument("run")
    _add_runs_dir(status)

    stop = sub.add_parser("stop")
    stop.add_argument("run")
    stop.add_argument("--summary")
    _add_runs_dir(stop)

    resume = sub.add_parser("resume")
    resume.add_argument("run")
    _add_runs_dir(resume)

    claim = sub.add_parser("claim")
    claim.add_argument("run")
    claim.add_argument("node")
    _add_runs_dir(claim)

    result = sub.add_parser("result")
    result.add_argument("run")
    result.add_argument("node")
    result.add_argument("--verdict", required=True, choices=sorted(WORKER_VERDICTS))
    result.add_argument("--evidence", action="append", default=[])
    result.add_argument("--criterion-evidence", action="append", default=[])
    result.add_argument("--criterion-verification", action="append", default=[])
    result.add_argument("--output-json")
    result.add_argument("--gap", action="append", default=[])
    result.add_argument("--summary")
    result.add_argument("--authority-confirmed", action="store_true")
    result.add_argument("--critical-findings", type=int)
    result.add_argument("--state-agrees", action="store_true", default=None)
    _add_runs_dir(result)

    args = parser.parse_args(argv)
    registry = WorkflowRegistry(ROOT / "workflows", ROOT / "skills")
    engine = WorkflowEngine(registry, canonical_state_reader=_canonical_state)

    try:
        if args.command == "plan":
            run = engine.plan(args.goal, args.workflow)
            print(json.dumps(_summary(engine, run), indent=2))
            return 0

        if args.command == "start":
            run = engine.plan(args.goal, args.workflow)
            payload = _summary(engine, run)
            path = save_run(run, args.runs_dir)
            payload["state_path"] = str(path.resolve())
            print(json.dumps(payload, indent=2))
            return 0

        path = _run_path(args.run, args.runs_dir)
        with _run_lock(path):
            run = load_run(path)

            if args.command == "stop":
                engine.stop(run, summary=args.summary)
            elif args.command == "resume":
                engine.resume(run)
            elif args.command == "claim":
                descriptor = engine.claim(run, args.node)
                payload = _summary(engine, run)
                payload["execution"] = descriptor
                save_run_file(run, path)
                print(json.dumps(payload, indent=2))
                return 0
            elif args.command == "result":
                outputs = json.loads(args.output_json) if args.output_json else {}
                if not isinstance(outputs, dict):
                    raise ValueError("--output-json must decode to an object")
                engine.record_result(
                    run,
                    args.node,
                    verdict=args.verdict,
                    criteria=_criterion_updates(
                        args.criterion_evidence, args.criterion_verification
                    ),
                    evidence=args.evidence,
                    outputs=outputs,
                    gaps=args.gap,
                    summary=args.summary,
                    authority_confirmed=args.authority_confirmed,
                    critical_findings=args.critical_findings,
                    state_agrees=args.state_agrees,
                )
            payload = _summary(engine, run)
            save_run_file(run, path)
        print(json.dumps(payload, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 1


if __name__ == "__main__":
    sys.exit(main())
