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
- criterion-level evidence and canonical verdict handling;
- adaptive run-local gap-resolution nodes;
- stall detection and pinned-workflow drift checks;
- runtime expansion for foreach and nested-workflow nodes;
- durable plan/start/status/claim/result/stop/resume CLI operations.

Accepted criterion evidence records a pointer, its relation to the criterion,
the verification method and result, and a timezone-aware validation timestamp.
Node acceptance additionally requires an explicit critical-finding count and
canonical/mirror agreement. Failed and blocked results must name canonical gaps
so the shared policy can retain exactly one next route. Terminal acceptance is
represented by explicit gate nodes; accepting ordinary child nodes never
accepts the workflow.

Hosts may inject a canonical-state reader for tracker, document, and commit
reconciliation. Resume records that observation and blocks on reported drift.
Claiming work enforces the workflow parallelism limit and rejects shared
workspace collisions. The CLI supplies a repository reader and serializes
state mutations with a per-run lock. Root gates must cite evidence not reused
from child nodes and use an independent verification method for every root
criterion. The engine consults its canonical-state reader during both resume
and node acceptance; blocked nodes route through a resolution node before retry.

Actual subagent spawning is host-neutral by design: Claude Code, Codex,
ChatGPT Work, or another host can execute a ready node using the node's role,
skills, task, workspace, inputs, and acceptance contract.

## Follow-up surface

Future PRs may add host-specific executors, richer expression/condition support,
run inspection UI, cancellation hooks, and integration-worktree automation
without changing the v1 workflow ownership model. Run-state schema v1 is
upgraded to v2 on load; the executable validator is canonical and its JSON
Schema view is generated for external tooling.
