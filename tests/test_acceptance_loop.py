from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("acceptance_loop", ROOT / "scripts" / "acceptance_loop.py")
assert SPEC and SPEC.loader
loop = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = loop
SPEC.loader.exec_module(loop)


class AcceptanceScenarioTests(unittest.TestCase):
    def test_wayfinder_decision_hands_to_specification(self) -> None:
        verdict = loop.evaluate([loop.Criterion("D-1", True, True)], authority_required=True, authority_confirmed=True)
        self.assertEqual("Accepted", verdict)
        self.assertEqual(("specification", "to-spec-rpm"), loop.select_gap(["specification"]))

    def test_behavior_fails_then_reaches_acceptance(self) -> None:
        red = loop.evaluate([loop.Criterion("AC-1", True, False)])
        green = loop.evaluate([loop.Criterion("AC-1", True, True)])
        self.assertEqual(("Not accepted", "Accepted"), (red, green))

    def test_review_failure_routes_to_implementation(self) -> None:
        verdict = loop.evaluate([loop.Criterion("AC-1", True, True)], critical_findings=1)
        self.assertEqual("Not accepted", verdict)
        self.assertEqual(("behavior", "implement-rpm"), loop.select_gap(["behavior"]))

    def test_ambiguous_criterion_routes_before_design_and_behavior(self) -> None:
        self.assertEqual(("specification", "to-spec-rpm"), loop.select_gap(["behavior", "design", "specification"]))

    def test_blocked_scope_is_not_retried_as_failure(self) -> None:
        self.assertEqual("Blocked", loop.evaluate([loop.Criterion("AC-1", False, False)], blocked=True))

    def test_child_acceptance_updates_but_never_accepts_parent(self) -> None:
        parent = loop.ScopeState("milestone-1")
        child = loop.ScopeState("ticket-2", accepted=True, evidence={"AC-1": "commit:abc"})
        updated = loop.promote_child_evidence(parent, child)
        self.assertFalse(updated.accepted)
        self.assertEqual("commit:abc", updated.evidence["ticket-2:AC-1"])

    def test_phase_requires_explicit_pm_authority(self) -> None:
        criteria = [loop.Criterion("PC-1", True, True)]
        self.assertEqual("Needs decision", loop.evaluate(criteria, authority_required=True))
        self.assertEqual("Accepted", loop.evaluate(criteria, authority_required=True, authority_confirmed=True))

    def test_stalled_loop_escalates_after_unchanged_iterations(self) -> None:
        history = [
            loop.Iteration("ticket-1", "test", "same", "Not accepted", ("tdd-rpm",)),
            loop.Iteration("ticket-1", "test", "same", "Not accepted", ("tdd-rpm",)),
        ]
        self.assertEqual("Stalled", loop.progress_guard(history))

    def test_changed_evidence_justifies_another_iteration(self) -> None:
        history = [
            loop.Iteration("ticket-1", "test", "red-1", "Not accepted", ("tdd-rpm",)),
            loop.Iteration("ticket-1", "test", "green-2", "Not accepted", ("tdd-rpm",)),
        ]
        self.assertEqual("Continue", loop.progress_guard(history))

    def test_every_iteration_has_exactly_one_next_action(self) -> None:
        invalid = [loop.Iteration("ticket-1", "quality", "v1", "Not accepted", ("review", "refactor"))]
        self.assertEqual("Invalid iteration", loop.progress_guard(invalid))


if __name__ == "__main__":
    unittest.main()
