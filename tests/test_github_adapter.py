from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "github_adapter", ROOT / "skills" / "project-management-rpm" / "github_adapter.py"
)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


class FakeGh:
    def __init__(self, *, fail_target_once: bool = False) -> None:
        self.labels = {"pm:ready", "pm:task"}
        self.assignees: set[str] = set()
        self.fail_target_once = fail_target_once
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        args = command[1:]
        if args[:2] == ["issue", "view"]:
            fields = args[args.index("--json") + 1].split(",")
            data: dict[str, object] = {}
            if "number" in fields:
                data["number"] = 7
            if "state" in fields:
                data["state"] = "OPEN"
            if "url" in fields:
                data["url"] = "https://example.test/issues/7"
            if "labels" in fields:
                data["labels"] = [{"name": label} for label in sorted(self.labels)]
            if "assignees" in fields:
                data["assignees"] = [{"login": owner} for owner in sorted(self.assignees)]
            return subprocess.CompletedProcess(command, 0, json.dumps(data), "")
        if args[:2] == ["issue", "edit"]:
            if "--remove-label" in args:
                self.labels -= set(args[args.index("--remove-label") + 1].split(","))
            if "--add-label" in args:
                labels = set(args[args.index("--add-label") + 1].split(","))
                if self.fail_target_once and "pm:in-progress" in labels:
                    self.fail_target_once = False
                    return subprocess.CompletedProcess(command, 1, "", "injected partial failure")
                self.labels |= labels
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected fake gh command: {command}")


class AdapterTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_runner = adapter.GH_RUNNER
        self.config = {"repo": "owner/repo", "projects_enabled": False}

    def tearDown(self) -> None:
        adapter.GH_RUNNER = self.original_runner

    def test_success_and_idempotent_retry(self) -> None:
        fake = FakeGh()
        adapter.GH_RUNNER = fake

        first = adapter.set_state(7, "In Progress", self.config)
        second = adapter.set_state(7, "In Progress", self.config)

        self.assertEqual("Accepted", first.final_verdict)
        self.assertEqual("Accepted", second.final_verdict)
        self.assertEqual([], second.completed_writes)
        self.assertEqual(["In Progress"], adapter.workflow_statuses(adapter.issue_snapshot(7, self.config)))

    def test_partial_failure_restores_before_state(self) -> None:
        fake = FakeGh(fail_target_once=True)
        adapter.GH_RUNNER = fake

        result = adapter.set_state(7, "In Progress", self.config)

        self.assertEqual("Recovered", result.final_verdict)
        self.assertIn("restored workflow labels", result.recovery_writes)
        self.assertEqual(["Ready"], adapter.workflow_statuses(adapter.issue_snapshot(7, self.config)))

    def test_reconcile_reports_repairable_project_drift(self) -> None:
        snapshot = {
            "issue": 7,
            "labels": ["pm:ready", "pm:task"],
            "assignees": [],
        }
        report = adapter.reconcile_snapshot(snapshot, "Backlog")
        self.assertEqual("Drift", report["verdict"])
        self.assertFalse(report["ambiguous"])
        self.assertTrue(report["differences"][0]["repairable"])

    def test_reconcile_reports_missing_expected_project_mirror(self) -> None:
        snapshot = {
            "issue": 7,
            "labels": ["pm:ready", "pm:task"],
            "assignees": [],
        }
        report = adapter.reconcile_snapshot(snapshot, None, mirror_expected=True)
        self.assertEqual("Drift", report["verdict"])
        self.assertIsNone(report["differences"][0]["observed"])

    def test_reconcile_refuses_ambiguous_canonical_labels(self) -> None:
        snapshot = {
            "issue": 7,
            "labels": ["pm:ready", "pm:blocked"],
            "assignees": [],
        }
        report = adapter.reconcile_snapshot(snapshot, "Ready")
        self.assertEqual("Ambiguous", report["verdict"])
        self.assertTrue(report["ambiguous"])


if __name__ == "__main__":
    unittest.main()
