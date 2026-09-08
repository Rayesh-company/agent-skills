"""Workflow discovery and intent matching."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .validator import WorkflowValidationError, load_and_validate
from .yaml_subset import load

_WORD = re.compile(r"[a-z0-9]+")


class WorkflowRegistry:
    def __init__(self, root: Path, skills_root: Path | None = None):
        self.root = Path(root)
        self.skills_root = Path(skills_root) if skills_root else self.root.parent / "skills"
        self._workflows: dict[str, dict[str, Any]] = {}

    @property
    def skill_names(self) -> set[str]:
        if not self.skills_root.exists():
            return set()
        return {path.name for path in self.skills_root.iterdir() if path.is_dir()}

    def discover(self) -> dict[str, dict[str, Any]]:
        paths = sorted(self.root.glob("*.yaml"))
        shallow: dict[str, dict[str, Any]] = {}
        for path in paths:
            data = load(path)
            name = data.get("metadata", {}).get("name")
            if not isinstance(name, str) or not name:
                raise WorkflowValidationError(f"{path}: metadata.name is required")
            if name in shallow:
                raise WorkflowValidationError(f"duplicate workflow name {name}")
            shallow[name] = data

        names = set(shallow)
        validated: dict[str, dict[str, Any]] = {}
        for path in paths:
            workflow = load_and_validate(
                path,
                skills=self.skill_names,
                workflow_names=names,
            )
            validated[workflow["metadata"]["name"]] = workflow
        self._check_workflow_cycles(validated)
        self._workflows = validated
        return dict(validated)

    @staticmethod
    def _check_workflow_cycles(workflows: dict[str, dict[str, Any]]) -> None:
        temporary: list[str] = []
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                start = temporary.index(name)
                cycle = temporary[start:] + [name]
                raise WorkflowValidationError(
                    f"nested workflow cycle: {' -> '.join(cycle)}"
                )
            temporary.append(name)
            targets = {
                node["workflow"]
                for node in workflows[name]["nodes"].values()
                if node.get("type") == "workflow"
            }
            for target in sorted(targets):
                visit(target)
            temporary.pop()
            permanent.add(name)

        for name in sorted(workflows):
            visit(name)

    def get(self, name: str) -> dict[str, Any]:
        if not self._workflows:
            self.discover()
        try:
            return self._workflows[name]
        except KeyError as exc:
            raise KeyError(f"unknown workflow {name!r}") from exc

    def match(self, goal: str) -> tuple[str, float]:
        if not self._workflows:
            self.discover()
        goal_words = set(_WORD.findall(goal.lower()))
        best_name = ""
        best_score = -1.0
        for name, workflow in self._workflows.items():
            examples = workflow.get("intent", {}).get("examples", [])
            haystack = " ".join([name.replace("-", " "), *examples]).lower()
            words = set(_WORD.findall(haystack))
            overlap = len(goal_words & words)
            score = overlap / max(1, len(goal_words))
            if score > best_score:
                best_name, best_score = name, score
        if not best_name:
            raise KeyError("no workflows registered")
        if best_score <= 0:
            raise LookupError(
                "no adequate workflow matches this goal; route to wayfinder-rpm"
            )
        return best_name, best_score
