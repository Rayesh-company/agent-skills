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
