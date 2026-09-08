"""Semantic validation for Rayesh workflow graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .yaml_subset import YamlSubsetError, load

API_VERSION = "rayesh.io/v1"
NODE_TYPES = {"agent", "foreach", "gate", "human", "workflow"}


class WorkflowValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowValidationError(message)


def _string_list(value: Any, where: str, *, nonempty: bool = False) -> list[str]:
    _require(isinstance(value, list), f"{where} must be a list")
    _require(all(isinstance(item, str) and item for item in value), f"{where} must contain strings")
    if nonempty:
        _require(bool(value), f"{where} must not be empty")
    return value


def _check_cycle(nodes: dict[str, Any]) -> None:
    temporary: set[str] = set()
    permanent: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in permanent:
            return
        if node_id in temporary:
            raise WorkflowValidationError(f"dependency cycle includes {node_id}")
        temporary.add(node_id)
        for dep in nodes[node_id].get("depends_on", []):
            visit(dep)
        temporary.remove(node_id)
        permanent.add(node_id)

    for node_id in nodes:
        visit(node_id)


def validate_workflow(
    workflow: dict[str, Any],
    *,
    skills: set[str] | None = None,
    workflow_names: set[str] | None = None,
) -> dict[str, Any]:
    _require(workflow.get("apiVersion") == API_VERSION, f"apiVersion must be {API_VERSION}")
    _require(workflow.get("kind") == "Workflow", "kind must be Workflow")

    metadata = workflow.get("metadata")
    _require(isinstance(metadata, dict), "metadata is required")
    _require(isinstance(metadata.get("name"), str) and metadata["name"], "metadata.name is required")
    _require(isinstance(metadata.get("version"), int) and metadata["version"] >= 1, "metadata.version must be >= 1")

    intent = workflow.get("intent", {})
    _require(isinstance(intent, dict), "intent must be a mapping")
    if "examples" in intent:
        _string_list(intent["examples"], "intent.examples", nonempty=True)

    nodes = workflow.get("nodes")
    _require(isinstance(nodes, dict) and nodes, "nodes must be a non-empty mapping")

    for node_id, node in nodes.items():
        _require(isinstance(node_id, str) and node_id, "node ids must be strings")
        _require(isinstance(node, dict), f"nodes.{node_id} must be a mapping")
        node_type = node.get("type")
        _require(node_type in NODE_TYPES, f"nodes.{node_id}.type must be one of {sorted(NODE_TYPES)}")

        deps = node.get("depends_on", [])
        _string_list(deps, f"nodes.{node_id}.depends_on")
        for dep in deps:
            _require(dep in nodes, f"nodes.{node_id} depends on unknown node {dep}")
            _require(dep != node_id, f"nodes.{node_id} cannot depend on itself")

        acceptance = node.get("acceptance")
        _require(isinstance(acceptance, dict), f"nodes.{node_id}.acceptance is required")
        _string_list(
            acceptance.get("criteria"),
            f"nodes.{node_id}.acceptance.criteria",
            nonempty=True,
        )

        if node_type in {"agent", "foreach"}:
            agent = node.get("agent")
            _require(isinstance(agent, dict), f"nodes.{node_id}.agent is required")
            _require(isinstance(agent.get("role"), str) and agent["role"], f"nodes.{node_id}.agent.role is required")
            node_skills = _string_list(
                agent.get("skills"),
                f"nodes.{node_id}.agent.skills",
                nonempty=True,
            )
            if skills is not None:
                missing = sorted(set(node_skills) - skills)
                _require(not missing, f"nodes.{node_id} references unknown skills: {', '.join(missing)}")

        if node_type == "foreach":
            foreach = node.get("foreach")
            _require(isinstance(foreach, dict), f"nodes.{node_id}.foreach is required")
            _require(isinstance(foreach.get("source"), str) and foreach["source"], f"nodes.{node_id}.foreach.source is required")
            if "parallel" in foreach:
                _require(isinstance(foreach["parallel"], bool), f"nodes.{node_id}.foreach.parallel must be boolean")
            if foreach.get("parallel") is True:
                _require(node.get("workspace", "worktree") != "shared", f"nodes.{node_id}: parallel foreach may not use shared workspace")

        if node_type == "workflow":
            target = node.get("workflow")
            _require(isinstance(target, str) and target, f"nodes.{node_id}.workflow is required")
            if workflow_names is not None:
                _require(target in workflow_names, f"nodes.{node_id} references unknown workflow {target}")

        if node_type == "human":
            _require(isinstance(node.get("task"), str) and node["task"], f"nodes.{node_id}.task is required")

    _check_cycle(nodes)
    return workflow


def load_and_validate(
    path: Path,
    *,
    skills: set[str] | None = None,
    workflow_names: set[str] | None = None,
) -> dict[str, Any]:
    try:
        workflow = load(path)
    except YamlSubsetError as exc:
        raise WorkflowValidationError(f"{path}: {exc}") from exc
    return validate_workflow(workflow, skills=skills, workflow_names=workflow_names)
