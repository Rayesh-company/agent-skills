"""Semantic validation for Rayesh workflow graphs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .yaml_subset import YamlSubsetError, load

API_VERSION = "rayesh.io/v1"
NODE_TYPES = {"agent", "foreach", "gate", "human", "workflow"}


def schema_document() -> dict[str, Any]:
    """Return the generated JSON Schema view of this executable contract."""
    string = {"type": "string", "minLength": 1}
    string_list = {"type": "array", "items": string}
    agent = {
        "type": "object",
        "required": ["role", "skills"],
        "properties": {
            "role": string,
            "skills": {**string_list, "minItems": 1},
        },
        "additionalProperties": True,
    }
    node = {
        "type": "object",
        "required": ["type", "acceptance"],
        "properties": {
            "type": {"enum": sorted(NODE_TYPES)},
            "depends_on": string_list,
            "task": string,
            "workspace": {"enum": ["readonly", "worktree", "shared"]},
            "agent": agent,
            "foreach": {
                "type": "object",
                "required": ["source"],
                "properties": {"source": string, "parallel": {"type": "boolean"}},
                "additionalProperties": True,
            },
            "workflow": string,
            "acceptance": {
                "type": "object",
                "required": ["criteria"],
                "properties": {"criteria": {**string_list, "minItems": 1}},
                "additionalProperties": True,
            },
        },
        "allOf": [
            {
                "if": {"properties": {"type": {"const": "agent"}}},
                "then": {"required": ["agent"]},
            },
            {
                "if": {"properties": {"type": {"const": "foreach"}}},
                "then": {"required": ["agent", "foreach"]},
            },
            {
                "if": {"properties": {"type": {"const": "workflow"}}},
                "then": {"required": ["workflow"]},
            },
            {
                "if": {"properties": {"type": {"const": "human"}}},
                "then": {"required": ["task"]},
            },
        ],
        "additionalProperties": True,
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://rayesh.company/schemas/workflow-v1.json",
        "$comment": "Generated from rayesh_runtime.validator.schema_document; do not edit directly.",
        "title": "Rayesh Workflow v1",
        "type": "object",
        "required": ["apiVersion", "kind", "metadata", "nodes"],
        "properties": {
            "apiVersion": {"const": API_VERSION},
            "kind": {"const": "Workflow"},
            "metadata": {
                "type": "object",
                "required": ["name", "version"],
                "properties": {
                    "name": string,
                    "version": {"type": "integer", "minimum": 1},
                    "description": {"type": "string"},
                },
                "additionalProperties": True,
            },
            "intent": {
                "type": "object",
                "properties": {"examples": {**string_list, "minItems": 1}},
                "additionalProperties": True,
            },
            "policies": {
                "type": "object",
                "properties": {
                    "max_parallel_agents": {"type": "integer", "minimum": 1}
                },
                "additionalProperties": True,
            },
            "nodes": {
                "type": "object",
                "minProperties": 1,
                "additionalProperties": node,
            },
        },
        "additionalProperties": True,
    }


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
    version = metadata.get("version")
    _require(
        isinstance(version, int) and not isinstance(version, bool) and version >= 1,
        "metadata.version must be an integer >= 1",
    )
    if "description" in metadata:
        _require(
            isinstance(metadata["description"], str),
            "metadata.description must be a string",
        )

    intent = workflow.get("intent", {})
    _require(isinstance(intent, dict), "intent must be a mapping")
    if "examples" in intent:
        _string_list(intent["examples"], "intent.examples", nonempty=True)

    policies = workflow.get("policies", {})
    _require(isinstance(policies, dict), "policies must be a mapping")
    if "max_parallel_agents" in policies:
        maximum = policies["max_parallel_agents"]
        _require(
            isinstance(maximum, int) and not isinstance(maximum, bool) and maximum >= 1,
            "policies.max_parallel_agents must be an integer >= 1",
        )

    nodes = workflow.get("nodes")
    _require(isinstance(nodes, dict) and nodes, "nodes must be a non-empty mapping")

    for node_id, node in nodes.items():
        _require(isinstance(node_id, str) and node_id, "node ids must be strings")
        _require(isinstance(node, dict), f"nodes.{node_id} must be a mapping")
        node_type = node.get("type")
        _require(node_type in NODE_TYPES, f"nodes.{node_id}.type must be one of {sorted(NODE_TYPES)}")
        if "task" in node:
            _require(
                isinstance(node["task"], str) and node["task"],
                f"nodes.{node_id}.task must be a non-empty string",
            )
        if "workspace" in node:
            _require(
                node["workspace"] in {"readonly", "worktree", "shared"},
                f"nodes.{node_id}.workspace must be readonly, worktree, or shared",
            )

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

        if "agent" in node or node_type in {"agent", "foreach"}:
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

        if "foreach" in node or node_type == "foreach":
            foreach = node.get("foreach")
            _require(isinstance(foreach, dict), f"nodes.{node_id}.foreach is required")
            _require(isinstance(foreach.get("source"), str) and foreach["source"], f"nodes.{node_id}.foreach.source is required")
            if "parallel" in foreach:
                _require(isinstance(foreach["parallel"], bool), f"nodes.{node_id}.foreach.parallel must be boolean")
            if foreach.get("parallel") is True:
                _require(node.get("workspace", "worktree") != "shared", f"nodes.{node_id}: parallel foreach may not use shared workspace")

        if "workflow" in node or node_type == "workflow":
            target = node.get("workflow")
            _require(isinstance(target, str) and target, f"nodes.{node_id}.workflow is required")
            if workflow_names is not None:
                _require(target in workflow_names, f"nodes.{node_id} references unknown workflow {target}")

        if node_type == "human":
            _require(isinstance(node.get("task"), str) and node["task"], f"nodes.{node_id}.task is required")

    _check_cycle(nodes)
    referenced = {dep for node in nodes.values() for dep in node.get("depends_on", [])}
    terminals = [node_id for node_id in nodes if node_id not in referenced]
    _require(
        all(nodes[node_id]["type"] == "gate" for node_id in terminals),
        "every terminal workflow node must be an explicit acceptance gate",
    )
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
