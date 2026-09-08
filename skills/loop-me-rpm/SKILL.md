---
name: loop-me-rpm
description: "Grill the user about the SPEC of a reusable Rayesh workflow, scoped to this workspace's existing skills and tools. Use iteratively until a validated YAML workflow could be executed without an implementer asking a process question."
disable-model-invocation: true
argument-hint: "A workflow to design, or nothing to go find one"
---

# Loop Me — Rayesh workflow authoring

Use `grilling-rpm` to turn a recurring or long-horizon process into a reusable
Rayesh workflow definition.

A **workflow** is the declarative architecture of a long-horizon task: which
subagent roles are needed, what RPM skills each receives, dependency edges,
parallelism, required outputs, human checkpoints, and acceptance criteria.

Reusable workflow source of truth:

`workflows/*.yaml`

The execution contract and canonical gap routing remain in
[`../../ACCEPTANCE-LOOP.md`](../../ACCEPTANCE-LOOP.md).

## Authoring loop

1. Establish the root outcome and acceptance authority.
2. Identify the smallest stable agent/workflow nodes rather than copying an
   existing conversation transcript.
3. For every node define role, skills, task, dependencies, outputs when useful,
   and observable acceptance criteria.
4. Mark safe parallel work explicitly and default mutating workers to isolated
   worktrees.
5. Add human nodes only where actual authority or information requires them;
   push checkpoints as late as safely possible and present a decision-ready
   brief.
6. Use nested workflows for reusable long-horizon sub-processes instead of
   duplicating their graphs.
7. Let the canonical acceptance loop handle unexpected gaps at runtime rather
   than predicting every failure branch in YAML.
8. Validate with `python3 scripts/validate_workflows.py`.
9. Dry-plan with `python3 scripts/rayesh.py plan "<goal>" --workflow <name>`.
10. Iterate until an orchestrator can execute the workflow without a process
    clarification.

## Rayesh YAML v1

Read `../../workflow-schema/README.md`. The repository keeps validation
stdlib-only, so v1 uses indentation-based mappings plus JSON-style flow
lists/maps. Every node requires an acceptance contract.

Supported node types:

- `agent`
- `foreach`
- `gate`
- `human`
- `workflow`

Generated one-off graphs should remain run-local. Promote a workflow into
`workflows/` only when it is intentionally reusable.
