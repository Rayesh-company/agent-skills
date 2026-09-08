import unittest
import json
from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
from copy import deepcopy

from rayesh_runtime.engine import WorkflowEngine
from rayesh_runtime.registry import WorkflowRegistry
from rayesh_runtime.scheduler import frontier
from rayesh_runtime.state import load_run, save_run
from rayesh_runtime.validator import WorkflowValidationError, validate_workflow
from rayesh_runtime.yaml_subset import loads


ROOT = Path(__file__).resolve().parents[1]


def verified_criteria(run, node_id):
    validated_at = datetime.now(timezone.utc).isoformat()
    return {
        criterion_id: {
            "evidence": [
                {
                    "pointer": f"artifacts/{node_id}-{criterion_id}.md",
                    "relation": "proves",
                    "verification": f"focused test for {node_id}",
                    "validated_at": validated_at,
                    "passed": True,
                }
            ]
        }
        for criterion_id in run["node_states"][node_id]["criteria"]
    }


def accept(engine, run, node_id, *, outputs=None, authority_confirmed=False):
    engine.record_result(
        run,
        node_id,
        verdict="Accepted",
        criteria=verified_criteria(run, node_id),
        outputs=outputs,
        authority_confirmed=authority_confirmed,
        critical_findings=0,
        state_agrees=True,
    )


class YamlSubsetTests(unittest.TestCase):
    def test_parses_mapping_and_flow_list(self):
        data = loads(
            'apiVersion: rayesh.io/v1\n'
            'kind: Workflow\n'
            'metadata:\n'
            '  name: demo\n'
            '  version: 1\n'
            'items: ["a", "b"]\n'
        )
        self.assertEqual(data["metadata"]["name"], "demo")
        self.assertEqual(data["items"], ["a", "b"])


class WorkflowValidationTests(unittest.TestCase):
    def setUp(self):
        self.registry = WorkflowRegistry(ROOT / "workflows", ROOT / "skills")

    def test_all_builtin_workflows_validate(self):
        workflows = self.registry.discover()
        self.assertGreaterEqual(len(workflows), 5)
        self.assertIn("engineering-feature", workflows)

    def test_boolean_metadata_version_is_rejected(self):
        workflow = deepcopy(self.registry.get("bug-fix"))
        workflow["metadata"]["version"] = True
        with self.assertRaisesRegex(WorkflowValidationError, "integer"):
            validate_workflow(workflow)

    def test_cycle_is_rejected(self):
        workflow = {
            "apiVersion": "rayesh.io/v1",
            "kind": "Workflow",
            "metadata": {"name": "cycle", "version": 1},
            "nodes": {
                "a": {"type": "gate", "depends_on": ["b"], "acceptance": {"criteria": ["ok"]}},
                "b": {"type": "gate", "depends_on": ["a"], "acceptance": {"criteria": ["ok"]}},
            },
        }
        with self.assertRaises(WorkflowValidationError):
            validate_workflow(workflow)

    def test_parallel_foreach_rejects_shared_workspace(self):
        workflow = {
            "apiVersion": "rayesh.io/v1",
            "kind": "Workflow",
            "metadata": {"name": "unsafe", "version": 1},
            "nodes": {
                "a": {
                    "type": "foreach",
                    "foreach": {"source": "x.items", "parallel": True},
                    "agent": {"role": "worker", "skills": ["tdd-rpm"]},
                    "workspace": "shared",
                    "acceptance": {"criteria": ["ok"]},
                }
            },
        }
        with self.assertRaises(WorkflowValidationError):
            validate_workflow(workflow, skills={"tdd-rpm"})

    def test_nested_workflow_cycle_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / "workflows"
            workflows.mkdir()
            for name, target in [("alpha", "beta"), ("beta", "alpha")]:
                (workflows / f"{name}.yaml").write_text(
                    "\n".join(
                        [
                            "apiVersion: rayesh.io/v1",
                            "kind: Workflow",
                            "metadata:",
                            f"  name: {name}",
                            "  version: 1",
                            "nodes:",
                            "  nested:",
                            "    type: workflow",
                            f"    workflow: {target}",
                            "    acceptance:",
                            '      criteria: ["Child completes."]',
                            "  complete:",
                            "    type: gate",
                            '    depends_on: ["nested"]',
                            "    acceptance:",
                            '      criteria: ["Workflow completes."]',
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(WorkflowValidationError, "nested workflow cycle"):
                WorkflowRegistry(workflows, root / "skills").discover()


class SchedulerAndEngineTests(unittest.TestCase):
    def setUp(self):
        self.registry = WorkflowRegistry(ROOT / "workflows", ROOT / "skills")
        self.registry.discover()
        self.engine = WorkflowEngine(self.registry)

    def test_frontier_advances_after_dependency_acceptance(self):
        workflow = {
            "nodes": {
                "a": {"depends_on": []},
                "b": {"depends_on": []},
                "c": {"depends_on": ["a", "b"]},
            }
        }
        states = {
            "a": {"status": "pending"},
            "b": {"status": "pending"},
            "c": {"status": "pending"},
        }
        self.assertEqual(frontier(workflow, states), ["a", "b"])
        states["a"]["status"] = "accepted"
        self.assertEqual(frontier(workflow, states), ["b"])
        states["b"]["status"] = "accepted"
        self.assertEqual(frontier(workflow, states), ["c"])

    def test_gap_inserts_resolution_node_before_retry(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        accept(self.engine, run, "reproduce")
        self.engine.record_result(
            run,
            "diagnose",
            verdict="Not accepted",
            gap="knowledge",
            evidence=["missing upstream API fact"],
        )
        dynamic = list(run["dynamic_nodes"])
        self.assertEqual(len(dynamic), 1)
        resolution = dynamic[0]
        self.assertIn(resolution, run["runtime_workflow"]["nodes"]["diagnose"]["depends_on"])
        self.assertIn(resolution, self.engine.frontier(run))

    def test_intent_match_prefers_bug_fix(self):
        name, score = self.registry.match("fix this intermittent login bug")
        self.assertEqual(name, "bug-fix")
        self.assertGreater(score, 0)

    def test_intent_match_rejects_an_unmatched_goal(self):
        with self.assertRaisesRegex(LookupError, "no adequate workflow"):
            self.registry.match("frobnicate ultraviolet zeppelins")

    def test_result_cannot_skip_dependencies(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        with self.assertRaisesRegex(ValueError, "not ready"):
            self.engine.record_result(
                run,
                "diagnose",
                verdict="Accepted",
                evidence=["diagnosis.md"],
            )

    def test_acceptance_requires_evidence(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.engine.record_result(
                run,
                "reproduce",
                verdict="Accepted",
                critical_findings=0,
                state_agrees=True,
            )

    def test_invalid_gap_does_not_partially_mutate_a_node(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        before = dict(run["node_states"]["reproduce"])
        before["evidence"] = list(before["evidence"])

        with self.assertRaisesRegex(ValueError, "unknown gap"):
            self.engine.record_result(
                run,
                "reproduce",
                verdict="Not accepted",
                evidence=["partial evidence"],
                gap="mystery",
            )

        self.assertEqual(run["node_states"]["reproduce"], before)

    def test_failed_result_requires_a_canonical_gap(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        with self.assertRaisesRegex(ValueError, "requires at least one canonical gap"):
            self.engine.record_result(run, "reproduce", verdict="Not accepted")
        self.assertEqual(run["node_states"]["reproduce"]["attempt"], 0)

    def test_repeated_unchanged_gap_stalls_the_run(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        for attempt in range(2):
            self.engine.record_result(
                run,
                "reproduce",
                verdict="Not accepted",
                evidence=["same-evidence"],
                gap="knowledge",
            )
            if attempt == 0:
                resolver = next(iter(run["dynamic_nodes"]))
                accept(self.engine, run, resolver)
        self.assertEqual(run["status"], "stalled")
        self.assertEqual(run["node_states"]["reproduce"]["status"], "stalled")
        self.assertEqual(run["events"][-1]["type"], "node_stalled")

    def test_foreach_expands_from_an_accepted_node_output(self):
        run = self.engine.plan("improve codebase architecture", "codebase-improvement")
        for node_id in ["assess", "design"]:
            accept(self.engine, run, node_id)
        accept(
            self.engine,
            run,
            "tickets",
            outputs={"frontier": [{"id": 1}, {"id": 2}]},
        )
        self.assertEqual(self.engine.frontier(run), ["implementation[1]", "implementation[2]"])
        descriptor = self.engine.execution_descriptor(run, "implementation[1]")
        self.assertEqual(descriptor["inputs"]["item"], {"id": 1})

    def test_non_parallel_foreach_expands_sequentially(self):
        run = self.engine.plan("improve codebase architecture", "codebase-improvement")
        run["runtime_workflow"]["nodes"]["implementation"]["foreach"]["parallel"] = False
        for node_id in ["assess", "design"]:
            accept(self.engine, run, node_id)
        accept(
            self.engine,
            run,
            "tickets",
            outputs={"frontier": ["first", "second"]},
        )
        self.assertEqual(self.engine.frontier(run), ["implementation[1]"])

    def test_human_node_requires_authority_confirmation(self):
        workflow = {
            "metadata": {"name": "human-check", "version": 1},
            "nodes": {
                "decide": {
                    "type": "human",
                    "task": "Choose.",
                    "acceptance": {"criteria": ["Decision is recorded."]},
                }
            },
        }
        from rayesh_runtime.state import new_run

        run = new_run("choose", workflow)
        with self.assertRaisesRegex(ValueError, "authority confirmation"):
            self.engine.record_result(
                run,
                "decide",
                verdict="Accepted",
                criteria=verified_criteria(run, "decide"),
                critical_findings=0,
                state_agrees=True,
            )

    def test_nested_workflow_expands_into_prefixed_nodes(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "parent", "version": 1},
            "nodes": {
                "delivery": {
                    "type": "workflow",
                    "workflow": "bug-fix",
                    "acceptance": {"criteria": ["Child evidence is accepted."]},
                }
            },
        }
        run = new_run("deliver", workflow)
        self.assertEqual(self.engine.frontier(run), ["delivery::reproduce"])
        self.assertEqual(run["runtime_workflow"]["nodes"]["delivery"]["type"], "gate")

    def test_resume_blocks_when_the_pinned_workflow_has_drifted(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        self.engine.stop(run)
        self.registry._workflows["bug-fix"]["metadata"]["version"] += 1
        self.engine.resume(run)
        self.assertEqual(run["status"], "blocked")
        self.assertEqual(run["events"][-1]["type"], "workflow_drift_detected")

    def test_resume_uses_host_canonical_state_reconciliation(self):
        snapshots = iter(
            [
                {"state_agrees": True, "revision": "before"},
                {"state_agrees": False, "revision": "drifted"},
            ]
        )
        engine = WorkflowEngine(self.registry, canonical_state_reader=lambda: next(snapshots))
        run = engine.plan("fix authentication bug", "bug-fix")
        engine.stop(run)
        engine.resume(run)
        self.assertEqual(run["status"], "blocked")
        self.assertEqual(run["events"][-1]["type"], "canonical_state_drift_detected")

    def test_acceptance_consults_host_canonical_state_reader(self):
        engine = WorkflowEngine(
            self.registry,
            canonical_state_reader=lambda: {"state_agrees": False, "reason": "conflict"},
        )
        run = engine.plan("fix authentication bug", "bug-fix")
        with self.assertRaisesRegex(ValueError, "state agreement"):
            engine.record_result(
                run,
                "reproduce",
                verdict="Accepted",
                criteria=verified_criteria(run, "reproduce"),
                critical_findings=0,
                state_agrees=True,
            )

    def test_claim_enforces_parallel_limit(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "parallel-limit", "version": 1},
            "policies": {"max_parallel_agents": 1},
            "nodes": {
                node_id: {
                    "type": "agent",
                    "agent": {"role": node_id, "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": [f"{node_id} completes."]},
                }
                for node_id in ["first", "second"]
            },
        }
        run = new_run("parallel", workflow)
        self.engine.claim(run, "first")
        with self.assertRaisesRegex(ValueError, "max_parallel_agents"):
            self.engine.claim(run, "second")

    def test_single_shared_workspace_claim_is_allowed_but_collisions_are_not(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "shared", "version": 1},
            "nodes": {
                "shared": {
                    "type": "agent",
                    "workspace": "shared",
                    "agent": {"role": "writer", "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": ["Write completes."]},
                },
                "other": {
                    "type": "agent",
                    "agent": {"role": "reader", "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": ["Read completes."]},
                },
            },
        }
        run = new_run("shared", workflow)
        self.engine.claim(run, "shared")
        with self.assertRaisesRegex(ValueError, "shared workspace collides"):
            self.engine.claim(run, "other")

    def test_child_acceptance_does_not_accept_the_workflow_root(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "root-gate", "version": 1},
            "nodes": {
                "work": {
                    "type": "agent",
                    "agent": {"role": "worker", "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": ["Work completes."]},
                },
                "complete": {
                    "type": "gate",
                    "depends_on": ["work"],
                    "acceptance": {"criteria": ["Root outcome is independently verified."]},
                },
            },
        }
        run = new_run("complete", workflow)
        accept(self.engine, run, "work")
        self.assertEqual(run["status"], "active")
        accept(self.engine, run, "complete")
        self.assertEqual(run["status"], "accepted")

    def test_root_gate_rejects_reused_child_evidence(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "root-gate", "version": 1},
            "nodes": {
                "work": {
                    "type": "agent",
                    "agent": {"role": "worker", "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": ["Work completes."]},
                },
                "complete": {
                    "type": "gate",
                    "depends_on": ["work"],
                    "acceptance": {"criteria": ["Outcome is independently verified."]},
                },
            },
        }
        run = new_run("complete", workflow)
        shared_pointer = "artifacts/shared.md"
        child = verified_criteria(run, "work")
        child["C1"]["evidence"][0]["pointer"] = shared_pointer
        self.engine.record_result(
            run,
            "work",
            verdict="Accepted",
            criteria=child,
            critical_findings=0,
            state_agrees=True,
        )
        root = verified_criteria(run, "complete")
        root["C1"]["evidence"][0]["pointer"] = shared_pointer
        before = deepcopy(run["node_states"]["complete"])
        with self.assertRaisesRegex(ValueError, "independent"):
            self.engine.record_result(
                run,
                "complete",
                verdict="Accepted",
                criteria=root,
                critical_findings=0,
                state_agrees=True,
            )
        self.assertEqual(run["node_states"]["complete"], before)

    def test_each_root_criterion_requires_an_independent_verification_method(self):
        from rayesh_runtime.state import new_run

        workflow = {
            "metadata": {"name": "root-gate", "version": 1},
            "nodes": {
                "work": {
                    "type": "agent",
                    "agent": {"role": "worker", "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": ["Work completes."]},
                },
                "complete": {
                    "type": "gate",
                    "depends_on": ["work"],
                    "acceptance": {"criteria": ["Outcome A.", "Outcome B."]},
                },
            },
        }
        run = new_run("complete", workflow)
        accept(self.engine, run, "work")
        root = verified_criteria(run, "complete")
        root["C2"]["evidence"][0]["verification"] = "focused test for work"
        with self.assertRaisesRegex(ValueError, "independent"):
            self.engine.record_result(
                run,
                "complete",
                verdict="Accepted",
                criteria=root,
                critical_findings=0,
                state_agrees=True,
            )

    def test_blocked_node_routes_through_resolution_before_retry(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        self.engine.record_result(run, "reproduce", verdict="Blocked", gap="dependency")
        resolver = next(iter(run["dynamic_nodes"]))
        self.engine.resume(run)
        self.assertEqual(self.engine.frontier(run), [resolver])
        self.assertEqual(run["node_states"]["reproduce"]["status"], "blocked")
        accept(self.engine, run, resolver)
        self.assertEqual(run["node_states"]["reproduce"]["status"], "pending")

    def test_evidence_freshness_compares_instants_not_iso_strings(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        run["created_at"] = "2026-09-08T07:00:00+00:00"
        criteria = verified_criteria(run, "reproduce")
        for item in criteria.values():
            item["evidence"][0]["validated_at"] = "2026-09-08T08:00:00+02:00"
        with self.assertRaisesRegex(ValueError, "verified evidence"):
            self.engine.record_result(
                run,
                "reproduce",
                verdict="Accepted",
                criteria=criteria,
                critical_findings=0,
                state_agrees=True,
            )

    def test_deadlocked_active_run_becomes_stalled(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        run["node_states"]["reproduce"]["status"] = "not_accepted"
        self.assertEqual(self.engine.frontier(run), [])
        self.assertEqual(run["status"], "stalled")

    def test_stop_and_resume_round_trip(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        self.engine.stop(run, summary="paused by operator")
        self.assertEqual(run["status"], "stopped")
        self.assertEqual(self.engine.frontier(run), [])

        self.engine.resume(run)
        self.assertEqual(run["status"], "active")
        self.assertEqual(self.engine.frontier(run), ["reproduce"])

        with TemporaryDirectory() as directory:
            path = save_run(run, Path(directory))
            restored = load_run(path)
        self.assertEqual(restored["run_id"], run["run_id"])
        self.assertEqual(restored["status"], "active")

    def test_v1_run_state_is_migrated_when_loaded(self):
        run = self.engine.plan("fix authentication bug", "bug-fix")
        run["schema_version"] = 1
        run.pop("status")
        for state in run["node_states"].values():
            for key in ["criteria", "outputs", "iterations"]:
                state.pop(key)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(run), encoding="utf-8")
            migrated = load_run(path)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["status"], "active")
        self.assertIn("C1", migrated["node_states"]["reproduce"]["criteria"])


if __name__ == "__main__":
    unittest.main()
