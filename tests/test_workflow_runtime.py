import unittest
from pathlib import Path

from rayesh_runtime.engine import WorkflowEngine
from rayesh_runtime.registry import WorkflowRegistry
from rayesh_runtime.scheduler import frontier
from rayesh_runtime.validator import WorkflowValidationError, validate_workflow
from rayesh_runtime.yaml_subset import loads


ROOT = Path(__file__).resolve().parents[1]


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
        self.engine.record_result(run, "reproduce", verdict="Accepted", evidence=["repro"])
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


if __name__ == "__main__":
    unittest.main()
