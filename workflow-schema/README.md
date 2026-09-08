# Rayesh workflow format v1

Rayesh workflows are YAML files under `workflows/` with `apiVersion: rayesh.io/v1`.

The v1 repository parser intentionally supports a strict, dependency-free YAML
subset: indentation-based mappings plus quoted/bare scalar values and JSON-style
flow lists/maps. Use `["a", "b"]` instead of block-list syntax. This keeps CI
stdlib-only and makes workflow parsing deterministic.

`rayesh_runtime/validator.py` is the executable source of truth. The checked-in
`workflow.schema.json` is generated from it for editor and external-tool use;
refresh and verify it with `python3 scripts/validate_workflows.py --write-schema`.

Every node must declare an acceptance contract. Supported node types are:

- `agent` — one specialist subagent;
- `foreach` — repeat an agent over a runtime collection, optionally in parallel;
- `gate` — evaluate evidence without specialist execution;
- `human` — explicit human authority/checkpoint;
- `workflow` — invoke a nested reusable workflow.

Run `python3 scripts/validate_workflows.py` after editing workflow definitions.
