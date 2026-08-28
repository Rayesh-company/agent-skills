# Agent Skills

This repository contains 37 composable RPM skills. Each skill is a specialist;
the workflow is held together by one acceptance contract rather than duplicated
completion rules.

## Lifecycle

Read [`ACCEPTANCE-LOOP.md`](ACCEPTANCE-LOOP.md) for the operational loop and gap
routing. Use `ask-matt-rpm` to orient, `project-management-rpm` for product and
delivery state, Wayfinder for unresolved decisions, and the spec → tickets →
implementation → review pipeline for settled engineering work.

Behavior, seam, ticket, milestone, and product-phase acceptance are distinct.
An accepted child contributes evidence to its parent and never accepts it.

## Validate a change

```bash
python3 scripts/validate_contracts.py
python3 -m compileall -q scripts skills/project-management-rpm
python3 -m unittest discover -s tests -v
```

The validator checks the machine-readable 37-skill inventory, skill metadata,
canonical `-rpm` references, relative links, router modes, core acceptance-loop
pointers, and proposed-spec status markers. CI runs the same checks.

## Compatibility

Skill directory/frontmatter names ending in `-rpm` are canonical package names.
Slash commands use those same names. Tracker labels and user-facing display
names are separate metadata and must not be treated as package aliases.

Renames, mode removals, label/state changes, template changes, and adapter
config changes require a documented migration. Add compatibility mappings
before removing an old path, preserve Issues-only operation, and remove a
compatibility path only in a documented breaking release.
