#!/usr/bin/env python3
"""Pure acceptance-loop policy used by fixtures and tracker adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


GAP_ORDER = {
    "knowledge": 0,
    "decision": 0,
    "specification": 1,
    "design": 2,
    "runnable-uncertainty": 2,
    "behavior": 3,
    "test": 3,
    "dependency": 3,
    "quality": 4,
    "evidence": 5,
    "state-drift": 5,
    "scope": 0,
}

GAP_ROUTES = {
    "knowledge": "research-rpm",
    "decision": "wayfinder-rpm",
    "specification": "to-spec-rpm",
    "design": "codebase-design-rpm",
    "runnable-uncertainty": "prototype-rpm",
    "behavior": "implement-rpm",
    "test": "tdd-rpm",
    "dependency": "project-management-rpm",
    "quality": "code-review-rpm",
    "evidence": "owning-execution-skill",
    "state-drift": "tracker-reconcile",
    "scope": "acceptance-authority",
}


@dataclass(frozen=True)
class Criterion:
    identifier: str
    has_current_evidence: bool
    verification_passed: bool


@dataclass(frozen=True)
class Iteration:
    scope: str
    gap: str
    evidence_fingerprint: str
    verdict: str
    next_actions: tuple[str, ...]


@dataclass
class ScopeState:
    identity: str
    accepted: bool = False
    evidence: dict[str, str] = field(default_factory=dict)


def evaluate(
    criteria: Iterable[Criterion],
    *,
    critical_findings: int = 0,
    state_agrees: bool = True,
    authority_required: bool = False,
    authority_confirmed: bool = False,
    blocked: bool = False,
) -> str:
    criteria = list(criteria)
    if blocked:
        return "Blocked"
    if authority_required and not authority_confirmed:
        return "Needs decision"
    if (
        criteria
        and all(item.has_current_evidence and item.verification_passed for item in criteria)
        and critical_findings == 0
        and state_agrees
    ):
        return "Accepted"
    return "Not accepted"


def select_gap(gaps: Iterable[str]) -> tuple[str, str]:
    candidates = list(gaps)
    if not candidates:
        raise ValueError("at least one gap is required")
    unknown = [gap for gap in candidates if gap not in GAP_ORDER]
    if unknown:
        raise ValueError(f"unknown gap types: {', '.join(unknown)}")
    gap = min(enumerate(candidates), key=lambda pair: (GAP_ORDER[pair[1]], pair[0]))[1]
    return gap, GAP_ROUTES[gap]


def progress_guard(history: Iterable[Iteration]) -> str:
    history = list(history)
    if any(len(item.next_actions) != 1 for item in history):
        return "Invalid iteration"
    if len(history) < 2:
        return "Continue"
    previous, current = history[-2:]
    if previous.gap == current.gap and previous.evidence_fingerprint == current.evidence_fingerprint:
        return "Stalled"
    return "Continue"


def promote_child_evidence(parent: ScopeState, child: ScopeState) -> ScopeState:
    for criterion, evidence in child.evidence.items():
        parent.evidence[f"{child.identity}:{criterion}"] = evidence
    return parent
