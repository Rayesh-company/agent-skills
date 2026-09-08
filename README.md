# Agent Skills

This repository contains 38 composable RPM skills plus the Rayesh workflow
orchestration layer. Each skill is a specialist; the workflow is held together
by one acceptance contract rather than duplicated completion rules.

## Recommended interaction

Use **Rayesh** (`/rayesh-rpm`) as the normal human-facing entry point. Describe
the outcome you want. Rayesh selects or resumes a reusable YAML workflow,
delegates bounded nodes to subagents with the required RPM skills, evaluates
criterion-level evidence, routes gaps, and returns the outcome.

Specialist skills remain directly callable for advanced/manual operation.

Reusable long-horizon architectures live in `workflows/*.yaml`. The v1 runtime
supports agent, foreach, gate, human, and nested-workflow nodes with explicit
dependencies and acceptance criteria.

## Lifecycle

Read [`ACCEPTANCE-LOOP.md`](ACCEPTANCE-LOOP.md) for the operational loop and gap
routing. Rayesh composes that contract at workflow level; specialists continue
to own only their own scopes. `project-management-rpm` owns product and delivery
state, Wayfinder owns unresolved decisions, and the spec → tickets →
implementation → review pipeline owns settled engineering work.

Behavior, seam, ticket, milestone, product-phase, and workflow acceptance are
distinct. An accepted child contributes evidence to its parent and never
accepts it automatically.

## Validate a change

```bash
python3 scripts/validate_contracts.py
python3 scripts/validate_workflows.py
python3 -m compileall -q scripts rayesh_runtime skills/project-management-rpm
python3 -m unittest discover -s tests -v
```

The contract validator checks the machine-readable skill inventory, metadata,
canonical `-rpm` references, relative links, router modes, core acceptance-loop
pointers, and proposed-spec status markers.

The workflow validator checks the versioned Rayesh YAML subset, skill/workflow
references, node contracts, dependency DAGs, and unsafe parallel shared
workspaces. CI runs both.

## Runtime CLI

Preview workflow selection without writing state:

```bash
python3 scripts/rayesh.py plan "fix the intermittent login bug"
```

Start a durable run, inspect or pause it, and resume it later:

```bash
python3 scripts/rayesh.py start "fix the intermittent login bug" --workflow bug-fix
python3 scripts/rayesh.py status <run-id>
python3 scripts/rayesh.py claim <run-id> reproduce
python3 scripts/rayesh.py stop <run-id> --summary "waiting for upstream access"
python3 scripts/rayesh.py resume <run-id>
```

Hosts record a ready node's evaluated result with evidence pointers. A node
cannot advance before its dependencies, and `Accepted` is rejected without
inspectable evidence:

```bash
python3 scripts/rayesh.py result <run-id> reproduce \
  --verdict Accepted \
  --criterion-evidence C1=artifacts/reproduction.md \
  --criterion-verification C1="python3 -m unittest tests.test_reproduction" \
  --criterion-evidence C2=artifacts/observations.md \
  --criterion-verification C2="manual observation review" \
  --critical-findings 0 \
  --state-agrees
```

Runs are stored under `.rayesh/runs/` by default. Use `--runs-dir` on stateful
commands to select another location. If no workflow has a meaningful intent
match, selection fails explicitly so Rayesh can route the goal through
Wayfinder instead of silently choosing an unrelated workflow.

`claim` returns the host-neutral execution descriptor and marks the node
running. `result` accepts one or more `--gap` values, criterion evidence,
optional `--output-json` for downstream `foreach` sources, and
`--authority-confirmed` for human checkpoints. Accepted evidence must include a
verification method and validation timestamp; acceptance also requires an
explicit zero-critical-findings result and canonical/mirror agreement. Failed
or blocked results require a canonical gap and retain its next route. Blocked
work must pass through that resolution node before retry. Plan and status
output include the expanded graph, ready/running/waiting sets, parallelism,
human checkpoints, and exactly one suggested next transition.

Run-state schema v1 is migrated to v2 on load. Workflow definitions are pinned
by version and hash; resume blocks and records a `state-drift` route when the
installed workflow no longer matches the run.
Hosts may provide a canonical-state reader to `WorkflowEngine`; resume records
the reconciliation result and blocks on reported tracker/document/commit drift.
The CLI supplies a repository reader by default and uses a per-run lock so
concurrent claims cannot bypass the parallelism limit. Terminal gates require
fresh evidence and an independent verification method for every root criterion.
The engine also consults the configured canonical-state reader during node
acceptance rather than trusting the caller's state-agreement flag alone.

## Compatibility

Skill directory/frontmatter names ending in `-rpm` remain canonical package
names. The user-facing orchestrator is displayed as **Rayesh** while its
canonical package/command remains `rayesh-rpm`.

Tracker labels and user-facing display names are separate metadata and must not
be treated as package aliases.

Renames, mode removals, label/state changes, template changes, workflow-schema
changes, and adapter config changes require a documented migration. Preserve
Issues-only operation and existing specialist entry points during the Rayesh
migration.
