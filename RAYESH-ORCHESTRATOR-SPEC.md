# Rayesh Orchestrator and Workflow Runtime

## Status

Implemented v1 foundation; advanced host executors and richer workflow syntax remain incremental follow-up work.

## Purpose

Rayesh is the default human-facing orchestrator. Users state outcomes; Rayesh
selects a reusable YAML workflow, delegates bounded nodes to subagents using RPM
skills, evaluates evidence with `ACCEPTANCE-LOOP.md`, inserts run-local gap
resolution work when necessary, and advances until root acceptance or a
terminal/human state.

## Layering

1. User intent → `rayesh-rpm`
2. Long-horizon architecture → `workflows/*.yaml`
3. Bounded workers → subagents
4. Specialist procedure → existing RPM skills
5. Correctness → `ACCEPTANCE-LOOP.md`
6. Canonical product state → tracker/docs/commits
7. Ephemeral execution state → `.rayesh/`

Skills remain independently callable and do not depend on specific workflows.

## V1 runtime

The stdlib-only runtime provides:

- workflow parsing and semantic validation;
- workflow/skill registry validation;
- DAG frontier scheduling;
- intent matching;
- durable run-state helpers;
- canonical verdict handling;
- adaptive run-local gap-resolution nodes;
- a dry-plan CLI.

Actual subagent spawning is host-neutral by design: Claude Code, Codex,
ChatGPT Work, or another host can execute a ready node using the node's role,
skills, task, workspace, inputs, and acceptance contract.

## Follow-up surface

Future PRs may add host-specific executors, richer expression/condition support,
full JSON-Schema runtime validation, workflow migration tooling, run inspection
UI, cancellation hooks, and integration-worktree automation without changing
the v1 workflow ownership model.
