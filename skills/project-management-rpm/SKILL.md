---
name: project-management-rpm
description: Use when the question is about product phase, phase goal, roadmap, sprint, claim, readiness, completion, or phase review. Owns the lifecycle above engineering skills.
disable-model-invocation: true
---

# Project Management

This skill is the project/product lifecycle layer above the engineering skills.

It owns **what phase we are in, what outcome the phase must reach, what work is in the backlog, who can claim it, and whether the phase is complete**.

## Acceptance contract

Read [`../../ACCEPTANCE-LOOP.md`](../../ACCEPTANCE-LOOP.md) before advancing PM
state. This skill owns ticket, milestone, and product-phase evaluation; the PM
is the acceptance authority for product-phase decisions. Inputs are the live
project/phase records, their criteria, child work, evidence, and adapter state.
Every mutating mode must observe live state, select one gap, execute, verify,
evaluate, record one iteration, and return exactly one next action.

Ticket acceptance requires criterion-level evidence and both review axes.
Milestone outcomes and product phases are verified independently of child
completion counts. This skill writes tracker records and their configured
mirrors through the adapter. On a partial write, apply the recovery protocol and
report `state-drift`; never declare the parent accepted because a child closed.
Route gaps through the canonical matrix in the shared contract.

It does not replace specialist skills. Delegate uncertainty and execution deliberately:

- `wayfinder-rpm` — map multi-session uncertainty and decisions.
- `research-rpm` — answer knowledge gaps from high-trust sources.
- `grill-with-docs-rpm` — pressure-test decisions with the human while improving domain docs.
- `domain-modeling-rpm` — sharpen product/domain language.
- `prototype-rpm` — make a cheap artifact to learn from.
- `to-spec-rpm` — produce an implementation spec when appropriate.
- `to-tickets-rpm` — slice settled engineering implementation work into vertical engineering tickets.
- `tdd-rpm`, `implement-rpm`, `code-review-rpm` — execute/review engineering work.

Read `PHASES.md`, `PROJECT-ISSUE.md`, `PHASE-ISSUE.md`, and `TASK-ISSUE.md` before using this skill. For Phase 0, also read `PHASE-0-PROPOSAL.md`.
Read `ACCEPTANCE-ITERATION.md` before recording ticket-level or higher
progress.

The configured issue tracker and domain-doc layout should already exist. If not, tell the user to run `/setup-pr-skills-rpm`.

## Tracker adapter

Read the configured `docs/agents/issue-tracker.md` before tracker writes.

When it identifies **GitHub** as the tracker, also read `GITHUB-ADAPTER.md` and treat the bundled `github_adapter.py` as the preferred write path for PM lifecycle operations. The adapter keeps GitHub Issues canonical and, when authorized, mirrors sortable PM metadata into one GitHub Project. Its config is `docs/agents/github-pm.json`.

If `docs/agents/github-pm.json` is missing, run the adapter's idempotent `bootstrap` before creating PM records. If GitHub Projects access is unavailable, continue in Issues-only mode rather than blocking the PM workflow. Do not bypass Matt's issue-tracker conventions for non-GitHub trackers.

## Canonical project model

### Project record

The PM system has one canonical project-level issue/record labelled `pm:project`. It plays a role analogous to a Wayfinder map, but for execution and lifecycle state rather than decision discovery.

It contains the north star, current phase, active phase goal, exit criteria, roadmap, active sprint, Wayfinder links, artifacts, risks, and phase history.

Never create multiple active `pm:project` issues for one product unless the PM explicitly says the repo contains multiple separately-managed products.

### Phase record

Each active phase has one child issue/record labelled `pm:phase` plus `phase:<n>`. It contains the concrete goal and exit gate for that phase.

Tasks attach to the active phase. Wayfinder maps attach to the project/phase as discovery artifacts, but remain Wayfinder maps with Wayfinder tickets.

### Work tickets

Any executable work may be a PM task labelled `pm:task`. Coding is only one task kind. Valid work includes engineering, product, design, business, docs, ops, meetings, research, validation, access/procurement, and other project work.

Use `TASK-ISSUE.md`. A work ticket must say what outcome it produces, why it matters, deadline/timing, effort, skills, technical depth, prerequisites, blockers, collaboration mode, and acceptance criteria.

Existing engineering tickets produced by `to-tickets-rpm` can also be enrolled in the PM backlog. Do **not** duplicate them: add/link the PM metadata (phase/milestone, deadline, effort, skill fit, technical depth, prerequisites, sprint state) to the existing issue and treat that issue as the managed work item. The project layer therefore manages one mixed backlog containing Matt-style engineering tickets and PM-native non-code tickets.

## Product phases

Use exactly these phase identities unless the PM intentionally changes the model:

- Phase 0 — Research & business planning
- Phase 1 — Demo
- Phase 2 — MVP
- Phase 3 — V1
- Phase 4 — Full product

Do not decide the phase only from repository/code maturity. Ask the PM which product-development question is currently being pursued, recommend the closest phase, and let the PM confirm.

## Invocation

Interpret the user's request as one of these modes:

- `init` — initialize PM state after setup.
- `status` — show current phase, goal, exit criteria, active sprint, blockers, and next recommended work.
- `wayfind` — start or resume discovery for the phase goal.
- `roadmap` — convert a sufficiently-clear route into milestones and backlog.
- `backlog` — create/refine/prioritize all-discipline tasks.
- `sprint` — plan or review a Scrum sprint.
- `claim` — recommend claimable work for a teammate.
- `prepare <ticket>` — check prerequisite knowledge/readiness before starting, especially before grilling.
- `done <ticket>` — record completion and update sprint/phase state.
- `phase-review` — evaluate phase exit criteria and choose advance/extend/pivot/pause/stop.

If the user just invokes the skill, load current state and recommend the next mode rather than restarting setup. The **mode-dispatcher** below is the entry point for every invocation and decides which mode actually runs.

## Mode dispatcher

Before running any mode, inspect PM state and route the user. The dispatcher runs once per turn; downstream modes trust the routing. Do not duplicate routing logic inside individual modes -- this section is the single source of truth.

### State probe (run first, in order; stop at first failure)

1. `pm:project` exists? (label `pm:project`, or canonical record per `docs/agents/issue-tracker.md`)
2. `pm:phase` exists? (label `pm:phase` + `phase:<n>`)
3. Phase goal and 3-7 exit criteria set in the phase issue body?
4. Active sprint? (open `Sprint` field, or a `sprint:<name>` label group with `start` <= today <= `end`)
5. Work in flight? (any open issue with `pm:claimed` or `pm:in-progress`)
6. Open blockers? (any open issue with `pm:blocked`, excluding the current item being inspected)

If the issue tracker is unreachable, do not run any mutating mode. Offer `status` from cached state if available; otherwise stop and ask the user to restore tracker access.

If multiple active `pm:project` issues exist, refuse to act and ask the PM to disambiguate, matching the canonical-record rule.

### Routing table

| Requested mode | Required state | If precondition not met, redirect to |
|---|---|---|
| `init` | none (re-init requires explicit confirmation) | If `pm:project` exists, ask PM to confirm re-init or route to `status` |
| `status` | `pm:project` | `init` |
| `wayfind` | `pm:project` + `pm:phase` | `init` |
| `roadmap` | `pm:project` + `pm:phase` with goal + exit criteria | `init` if missing, else `wayfind` if uncertainty still open |
| `backlog` | `pm:project` + `pm:phase` | `init` |
| `sprint` | `pm:project` + `pm:phase` + at least one `pm:ready` task | `init` if missing, else `roadmap` if no ready tasks |
| `claim` | `pm:project` + `pm:phase` + at least one eligible `pm:ready` task | `init` if missing, else `backlog` if no ready tasks |
| `prepare <ticket>` | `pm:project` + ticket reachable by id | `init` if no project, else ask user to confirm ticket id |
| `done <ticket>` | `pm:project` + ticket is `pm:claimed` by user (or `pm:in-progress`) | `init` if no project, else `prepare <ticket>` if not yet claimed |
| `phase-review` | `pm:project` + `pm:phase` with at least partial evidence | `init` |

### Implicit invocation (no mode keyword) -- `resume`

When the skill is invoked without a mode keyword, behave as `resume`:

- No `pm:project` -> auto-route to `init` and tell the user why.
- `pm:project` + `pm:phase` + no work in flight -> run `status`, then recommend the next mode from: `wayfind` (uncertainty open), `roadmap` (uncertainty closed), `sprint` (backlog ready), `claim` (ready tasks + idle teammate), `phase-review` (exit-criteria evidence accumulating).
- Work in flight -> run `status` and highlight the in-flight work first; recommend `done <ticket>` for stale claims or `sprint` review for stale sprints.

### Override

The PM can always override by saying e.g. "force `init`" or "skip dispatch and run `claim`". The dispatcher must surface a one-line warning ("state X is missing, proceeding anyway") and record the override in the next `status` report. The override is not blocked.

### How each mode uses the dispatcher

Each mode below contains a one-line precondition note at its top pointing to this table. The dispatcher enforces; the per-mode line is a pointer, not a duplicate of the routing logic.

# Mode: init

**Preconditions.** None. If `pm:project` already exists, the dispatcher asks the PM to confirm re-init. See mode-dispatcher.

### 1. Load context

Read:
- configured issue tracker,
- domain docs and ADRs,
- existing specs/product docs/business docs,
- open Wayfinder maps,
- existing issues/tasks/milestones,
- `docs/agents/project-management.md` if present.

Summarize evidence that may indicate the current phase, but do not silently select it.

### 2. Set the current phase

Present the five phases with a one-line purpose. Recommend one based on evidence, then ask the PM to confirm or choose another.

If the product is between phases, choose the phase containing the **next uncertainty/outcome to prove**, and note the previous phase evidence separately.

### 3. Set the phase goal

Interview the PM one question at a time until there is:

- one primary outcome goal,
- 3–7 observable exit criteria,
- a target date or explicit decision not to set one,
- major known constraints,
- obvious out-of-scope boundaries.

The goal is an outcome, not a task list.

For Phase 0, the goal must include producing the bilingual English/Farsi proposal described in `PHASE-0-PROPOSAL.md`.

### 4. Create PM records

If GitHub is configured, ensure the GitHub adapter is bootstrapped first. Use `github_adapter.py issue-create` for the project and phase records so labels, native relationships, and Project metadata stay synchronized. For other trackers, follow their configured conventions.

Publish:

1. one canonical project issue/record from `PROJECT-ISSUE.md`, labelled `pm:project`,
2. one active phase issue/record from `PHASE-ISSUE.md`, labelled `pm:phase` and `phase:<n>` and linked as a child/sub-issue where supported,
3. `docs/agents/project-management.md` containing:
   - phase names,
   - PM label mapping,
   - task work-kind labels,
   - effort convention (story points or T-shirt sizes),
   - sprint cadence,
   - definition of claim,
   - tracker-specific notes if needed.

If the PM has not chosen an effort convention or sprint cadence, recommend 1/2/3/5/8 story points and a 1- or 2-week sprint depending on team cadence; ask before recording.

### 5. Propose the initial Wayfinder

The initial map's destination is **not** "finish the phase." Its destination is:

> The major unknowns blocking a credible roadmap to the active phase goal are resolved enough that the PM can sequence milestones and executable work.

Explain that Wayfinder is for decisions/fog, while PM tasks are for execution.

With the PM's go-ahead, call the Skill tool for `wayfinder-rpm` to chart that map. Include the current phase goal and exit criteria in the Wayfinder Notes. Also put this standing rule in the map Notes: before any `wayfinder:grilling` ticket begins, run `project-management prepare <ticket>`; if the claimer lacks material prerequisite knowledge, create/resolve a focused research blocker first instead of starting the grill.

When charting stops, return control to project-management and recommend `roadmap` after enough frontier decisions have been resolved.

### 6. Post-condition check (PM initialization is atomic)

`init` writes four cross-cutting artifacts in one logical commit. Before exiting, verify:

- (a) a single `pm:project` issue exists with title `pm:project` and the `pm:project` label,
- (b) one `pm:phase` child issue exists labelled `pm:phase` and `phase:<n>` for the phase the PM confirmed,
- (c) `docs/agents/project-management.md` is written and contains: phase names, PM label mapping, work-kind labels, effort convention, sprint cadence, definition of claim, and any tracker-specific notes,
- (d) when the GitHub adapter is in use, the project/phase entries in `docs/agents/github-pm.json` (or the Issues-only fallback note) reflect the same records.

If any check fails, abort and report the missing artifact to the PM before declaring init complete.

# Mode: status

**Preconditions.** `pm:project` exists. If missing, the dispatcher routes to `init`. See mode-dispatcher.

Load the canonical `pm:project` record, active `pm:phase`, active sprint, open blockers, current Wayfinder, and the highest-priority ready work.

Report concisely:
- current product phase and phase goal,
- exit-criteria confidence/evidence gaps,
- active sprint goal and dates,
- done / in progress / claimed / ready / blocked counts or representative items,
- deadline risks and newly-unblocked work,
- active Wayfinder frontier when discovery is still open,
- current acceptance scope and canonical gap,
- last material evidence change and next owner,
- one recommended next PM action.

When GitHub is configured, read `docs/agents/github-pm.json`. If Projects is enabled, use it as the structured index for PM fields while treating GitHub issue bodies/relationships/assignment as canonical. If Projects is disabled, report `GitHub Issues-only PM mode` rather than treating the missing board as an error.

Do not mutate project state in `status` unless the user explicitly asks to correct stale metadata.

### Post-condition check (status read is atomic)

`status` must return a single coherent read snapshot. Before exiting, verify the report contains:

- (a) current product phase number and a one-line phase goal,
- (b) exit-criteria confidence and any evidence gaps,
- (c) active sprint goal and dates, or an explicit "no active sprint",
- (d) counts or representative items across done / in-progress / claimed / ready / blocked,
- (e) deadline risks and any newly-unblocked work, or an explicit "none",
- (f) active Wayfinder frontier pointer, or an explicit "no open map",
- (g) current acceptance scope/gap, last evidence change, and next owner,
- (h) exactly one recommended next PM action.

Also confirm no labels, comments, fields, or issues were written during the call. If any required section is missing or a silent mutation occurred, abort and surface the gap rather than returning a partial status.

# Mode: wayfind

**Preconditions.** `pm:project` + `pm:phase` exist. If missing, the dispatcher routes to `init`. See mode-dispatcher.

Load the active phase and existing Wayfinder maps.

- If no map exists and meaningful uncertainty remains, propose/chart one using the destination rule above.
- If a map exists, resume it using `wayfinder-rpm`.
- If the route is already clear enough to sequence delivery, do not create a ceremonial Wayfinder. Recommend `roadmap`.

Research/grilling/prototype tickets created inside Wayfinder remain Wayfinder tickets. Do not mirror them into the PM backlog unless they are execution work needed after the decision is made. For every Wayfinder grilling ticket, enforce the map Notes readiness rule: run `prepare` before the grilling exchange and turn material knowledge gaps into research blockers.

# Mode: roadmap

**Preconditions.** `pm:project` + `pm:phase` with goal + exit criteria, and major uncertainties closed enough to sequence delivery. See mode-dispatcher.

Use this only when the active phase goal and main uncertainties are sufficiently clear.

### 1. Synthesize the route

Read the active phase record, relevant closed Wayfinder decisions, ADRs/domain context, specs, research, and prototypes.

### 2. Draft milestones

Create outcome-oriented milestones that collectively satisfy the phase exit criteria. A milestone should be demonstrable/verifiable and may mix disciplines.

For each milestone show:
- outcome,
- exit criteria it advances,
- dependencies,
- key risks/unknowns,
- likely work kinds.

Review the milestone sequence with the PM.

When GitHub is configured, represent approved roadmap milestones as native GitHub Milestones when that improves grouping/deadline visibility. Use the adapter's `milestone-ensure`; do not create duplicate milestones with the same title.

### 3. Create backlog work

Break approved milestones into PM tasks using `TASK-ISSUE.md`.

Do not force every task through `to-tickets-rpm`:
- use PM tasks directly for research, product, design, business, docs, ops, meetings, validation, and small/coherent engineering tasks;
- use `to-tickets-rpm` when an engineering item is large enough to need tracer-bullet implementation slicing. Enroll the resulting engineering issues directly into this phase/backlog instead of creating wrapper duplicates. Add only the missing PM metadata needed for sprinting/claiming.

For every task, fill deadline/timing, effort, required/helpful skills, technical depth, prerequisites, blockers, collaboration mode, and acceptance criteria.

When GitHub is configured:
- create PM-native work with `github_adapter.py issue-create`,
- enroll existing `to-tickets-rpm`/eligible Wayfinder issues with `github_adapter.py enroll`,
- synchronize `Product Phase`, `PM Status`, `Sprint`, `Effort`, `Deadline`, `Technical Depth`, `Work Type`, and `Priority` when Projects is enabled,
- keep the full skills/prerequisites/acceptance contract in the issue body even when structured Project fields exist.

### 4. Wire dependencies

Use the tracker's native blocking/sub-issue relationships when available; otherwise follow the configured issue-tracker convention. On GitHub use `github_adapter.py relate`, which uses native parent/sub-issue and blocking relationships rather than comments that merely describe dependencies.

A task is `pm:ready` only when:
- its outcome/acceptance criteria are clear,
- blockers are either closed or accurately represented,
- prerequisite knowledge/read-first material is specified,
- required access is known,
- estimate and timing are present.

Otherwise keep it in `pm:backlog` or `pm:blocked`.

Update the project and active phase roadmap sections with milestone/task pointers rather than duplicating full task detail.

# Mode: backlog

**Preconditions.** `pm:project` + `pm:phase` exist. See mode-dispatcher.

Operate the product backlog as a living ordered set.

### Prioritization order

Recommend backlog order using this hierarchy:

1. work that unblocks the phase goal or multiple downstream tasks,
2. hard deadlines/events/compliance/external dependencies,
3. risk-reduction and learning that can invalidate expensive work,
4. sprint/phase goal contribution,
5. value relative to effort,
6. nice-to-have work.

Do not hide tradeoffs behind a magic numerical score. Explain the top ranking reasons in plain language.

### Readiness refinement

For selected backlog items:
- clarify outcome and acceptance criteria,
- estimate effort,
- add skills/technical depth,
- add prerequisite knowledge and read-first sources,
- add blockers,
- choose collaboration mode,
- move to `pm:ready` when ready. On GitHub, use the adapter `state` operation so the label and `PM Status` field change together.

# Mode: sprint

**Preconditions.** `pm:project` + `pm:phase` + at least one `pm:ready` task. See mode-dispatcher.

Use Scrum as a lightweight execution rhythm, not ceremony for its own sake.

### Sprint planning

1. Review active phase goal and current roadmap.
2. Review incomplete prior-sprint work and blockers.
3. Agree one sprint goal.
4. Pull only `pm:ready` tasks whose blockers allow meaningful progress during the sprint.
5. Check capacity using the team's recent velocity if known; otherwise be conservative and ask the PM/team to validate capacity.
6. Ensure the sprint contains the research/decision work needed before dependent delivery work.
7. Record sprint goal, dates/cadence, committed tasks, and known risks in the active phase/project record. On GitHub, enroll/update committed issues with the sprint name so the `Sprint` Project field stays queryable.

Do not assign every task during planning. Leave suitable tasks unassigned/claimable unless ownership is already known.

### Daily/ongoing status

When asked for sprint status, show:
- sprint goal confidence,
- done / in progress / ready / blocked,
- deadline risks,
- newly-unblocked work,
- items whose prerequisites are missing,
- one recommended PM action.

### Sprint review/retro

At sprint end:
- verify outcomes against acceptance criteria,
- move incomplete work back to backlog unless deliberately carried,
- capture evidence/demos/learnings,
- note estimation/process issues briefly,
- update phase-exit evidence,
- plan the next sprint only after reviewing the phase goal.

### Post-condition check (sprint plan is atomic)

A sprint plan is committed only when the phase body and the task labels are synchronized. Before exiting sprint planning, verify:

- (a) precondition: at least one `pm:ready` task exists in the active phase; if none, return to `backlog` to refine or create ready tasks before re-running sprint,
- (b) the active `pm:phase` body contains: sprint goal, sprint dates or cadence, and the committed-task list,
- (c) every committed task has been moved into the sprint's in-sprint state on both the label side and the Project `Sprint`/`PM Status` fields via the adapter's `state` operation,
- (d) any `pm:ready` task whose owner is unknown stays claimable (unassigned) rather than being silently auto-assigned,
- (e) known risks and blockers for the sprint are recorded in the phase or project record.

If any check fails, abort and resolve the half-committed state (revert label changes, restore prior body content) before declaring the sprint planned.

# Mode: claim

**Preconditions.** `pm:project` + `pm:phase` + at least one eligible `pm:ready` task. See mode-dispatcher.

The caller may provide their name, available time, skills, technical comfort, and deadline constraints. If some are missing, inspect known project/team context first; ask only for information needed to distinguish tasks.

### Eligibility filter

A ticket is claimable when:
- state is `pm:ready`,
- it is open and unassigned,
- all blockers are closed,
- prerequisite research/read-first requirements are satisfied or are realistically the first sub-step,
- the claimer has required access,
- deadline vs effort is feasible.

> **Invariant.** On GitHub, the `pm:claimed` label is valid only when an assignee is set. The adapter must refuse the label if assignment is empty.

### Promotion from ready-for-agent

Before recommending `pm:ready` tasks, query for issues carrying the triage state `ready-for-agent` that lack `pm:ready`. Engineering triage and PM backlog use parallel ready queues; without this bridge, claim mode will report "nothing claimable" while an AFK agent can already pick the item up.

For each candidate:
- Verify it has `ready-for-agent` and does not yet have `pm:ready`, is open, and the triage verdict has not been overturned (no `wontfix`, `needs-info`, or `needs-triage` also applied).
- Surface as "Triage-ready, not PM-ready" with a one-line reason (e.g. "agent brief posted; PM metadata missing").
- On confirm, apply `pm:ready` via the adapter's `state` operation so the label and `PM Status` Project field change together. Default: leave `ready-for-agent` in place — it points at the AFK agent queue and removing it silently could orphan work in flight. Ask before removing.

Inputs: auto-discovered from the tracker query, or an explicit issue number (e.g. `claim — promote #42`). This step is optional — skip it if the user says they only want `pm:ready` items, or if no triage-ready candidates exist.

### Recommendation

Rank eligible tasks by:
1. deadline urgency / expiring opportunity,
2. contribution to sprint goal and phase goal,
3. skill fit and technical-depth fit,
4. unblocking leverage,
5. smaller effort when all else is close.

Present 1–5 best matches with the reason each fits. Do not shame or disqualify a teammate for lacking knowledge; route them to a prerequisite research task when that is the safe path.

### Claim action

Once the user chooses:
- assign the issue to them using the configured tracker; on GitHub use `github_adapter.py claim` so the live assignment is re-checked before claiming,
- move `pm:ready` -> `pm:claimed` (or equivalent),
- record claim time/sprint when useful,
- tell them to run `prepare <ticket>` before a grilling/decision-heavy task or whenever prerequisites are nontrivial.

Assignment is the authoritative claim, mirroring Wayfinder's assignment-as-claim pattern. Re-read live assignment around a claim; do not pretend GitHub assignment is an atomic compare-and-set lock.

### Post-condition check (claim is atomic)

A claim combines label transition, assignment, and audit trail into one logical operation. Before exiting claim, verify:

- (a) the issue now carries `pm:claimed` and no longer carries `pm:ready`,
- (b) the issue has a non-empty assignee that matches the claimer,
- (c) a claim-time annotation is recorded (issue comment, audit field, or body timestamp),
- (d) the invariant from the eligibility section holds: `pm:claimed` exists only when assignee is set - the adapter rejected the inverse,
- (e) when the ticket is grilling/decision-heavy or has nontrivial prerequisites, the claimer was told to run `prepare <ticket>` before starting.

If (a)-(c) fail, abort and reverse any partial change so the ticket does not enter a half-claimed state that would distort ready-vs-claimed metrics.

# Mode: prepare <ticket>

**Preconditions.** `pm:project` exists and the ticket is reachable by id. See mode-dispatcher.

This is the readiness gate before starting a task, including a PM task, an enrolled engineering ticket, or a Wayfinder grilling ticket. It is especially important before `grill-with-docs-rpm` or technically unfamiliar work.

### 1. Read the ticket and linked context

Load acceptance criteria, prerequisites, key terms, research/docs, blockers, ADRs, and relevant Wayfinder decisions.

### 2. Build the readiness checklist

Show a concise checklist of what the claimer should know or have before starting. Tailor it to the ticket; do not use generic textbook prerequisites.

Examples:
- what Docker image/container/registry means before deciding a container deployment approach,
- what the existing auth flow and OAuth roles are before an auth grilling session,
- target segment/pricing assumptions before a business-model decision,
- current stack boundaries before choosing a new framework.

### 3. Detect knowledge gaps

Ask the claimer which checklist items they cannot confidently explain or verify.

For each material gap:
- recommend a focused research task,
- state the exact question it must answer,
- call `research-rpm` when the agent can perform it,
- or create a PM research ticket when a teammate must own it,
- block the original task when the gap would make the session low-quality or unsafe.

Do not make research mandatory for familiar concepts the user already understands.

### 4. Start the correct specialist workflow

When ready:
- decision/grilling -> call `grill-with-docs-rpm`,
- research -> call `research-rpm`,
- prototype -> call `prototype-rpm`,
- engineering implementation -> `to-spec-rpm`/`to-tickets-rpm`/`implement-rpm` as appropriate,
- non-code execution -> follow the PM task acceptance criteria directly.

### Post-condition check (prepare is atomic)

`prepare` gates start-up on readiness and hands the claimer to exactly one specialist workflow. Before exiting, verify:

- (a) the ticket's state is confirmed `pm:ready`, or the call is for a Wayfinder grilling ticket that the map's readiness rule applies to,
- (b) a tailored readiness checklist was produced for this ticket - not a generic textbook list - and shown to the claimer,
- (c) every material knowledge gap the claimer reported is recorded with either a research-blocker link, a `research-rpm` invocation note, or an explicit "no gap, proceed" decision with reason,
- (d) exactly one target specialist workflow is named (`grill-with-docs-rpm` / `research-rpm` / `prototype-rpm` / `to-spec-rpm` / `to-tickets-rpm` / `implement-rpm` / direct PM execution) and the caller's next action is to invoke it,
- (e) if a gap is material enough to make the session low-quality or unsafe, the original ticket is moved to `pm:blocked` with a pointer to the research resolution path.

If any check fails, do not hand off to the specialist workflow yet; return the readiness report to the claimer instead.

# Mode: done <ticket>

**Preconditions.** `pm:project` + the ticket is `pm:claimed` by the user (or `pm:in-progress`). See mode-dispatcher.

Verify acceptance criteria rather than treating "I worked on it" as completion.

Read the latest acceptance iteration first. Require implementation verification
and both `code-review-rpm` axes to have no unresolved blocking finding. If the
same gap has appeared in two consecutive iterations without a material evidence
change, record `Stalled` and route upstream or to the named authority instead of
retrying the same action.

Then:
- mark/close the ticket according to tracker convention; on GitHub use `github_adapter.py done` so completion evidence is posted before a close that may already have happened through a commit/PR,
- update labels/state to `pm:done`,
- capture links to artifacts/evidence,
- surface newly-unblocked tasks,
- update sprint status,
- update any phase exit criterion for which this work supplies evidence.

If finishing the task changes a product/architecture decision, route that decision through domain docs/ADR conventions rather than burying it in a task comment.

### Post-condition check (done is atomic)

`done` records completion and propagates downstream effects in one logical commit. Before exiting, verify:

- (a) each acceptance criterion on the issue is annotated met or not-met, with an evidence link (artifact, commit, doc, demo) for met items and a blocker note for not-met items,
- (b) the issue body or a closing comment carries the artifact / evidence link referenced by (a),
- (c) the ticket's label and state are `pm:done` (and the issue is closed per tracker convention),
- (d) any ticket whose only blocker was this one is listed in the report as newly-unblocked, with links,
- (e) any phase exit criterion that this work supplies evidence for is updated in the active phase record, with the same evidence link,
- (f) the active sprint's done count or status field reflects the completion.
- (g) a new acceptance iteration records criterion ids, evidence, verdict, and
  exactly one next action.

If any acceptance criterion is not met, do not label `pm:done`; either keep the ticket open for revisions or mark it explicitly not-done with reason and let it revert to `pm:ready` or `pm:blocked`.

# Mode: phase-review

**Preconditions.** `pm:project` + `pm:phase` exist with at least partial evidence. See mode-dispatcher.

A phase is complete because its exit criteria have enough evidence, not because its backlog is empty.
Accepted tickets and milestones are inputs to evaluation, never automatic phase
acceptance.

### 1. Review evidence

For each exit criterion, show:
- met / partially met / not met,
- evidence links,
- remaining uncertainty.

For Phase 0, verify that the bilingual English/Farsi proposal exists and is sufficiently sourced.

### 2. Ask the PM for the phase decision

Recommend one of:
- `advance` — exit criteria are met; define the next phase goal,
- `extend` — stay in the phase with a revised goal/date,
- `pivot` — important evidence changes the thesis/direction,
- `pause` — intentionally stop active work while preserving state,
- `stop` — end the project/product effort.

The PM makes the final call.
Record the PM identity/role, decision, rationale, date, and evidence pointer in
the phase acceptance iteration.

### 3. Record transition

Update the project record's phase history and close/archive the phase issue when appropriate.

If advancing:
- create the next phase issue,
- set a fresh phase goal and exit criteria,
- then consider a new initial Wayfinder for that phase if meaningful uncertainty exists.

Do not carry the old roadmap forward unquestioned; re-evaluate it against the new phase goal.

### 4. Post-condition check (project-record update is atomic)

The project-record update is the atomic operation of phase-review. Before exiting phase-review, verify:

- (a) the old phase issue is closed with rationale,
- (b) the new phase issue is created or updated,
- (c) the project record body reflects the new phase + new phase-history entry,
- (d) the `phase:` label on the project record is updated.

If any check fails, abort.

# Special rule: Phase 0 proposal

Phase 0 requires a documented proposal in **English and Farsi**.

Use `PHASE-0-PROPOSAL.md` as the structure. Research claims should be cited. Separate fact, evidence, inference, and hypothesis. The Farsi section should be a faithful full version, not a short summary of the English.

The proposal may live in the repo as a Markdown document and be linked from the Phase 0 issue. The issue should hold status and pointers, not duplicate the full document.

# Safety and project-health rules

- Never fabricate research evidence, dates, ownership, velocity, deadlines, or team skills.
- Estimates are forecasts, not promises.
- Do not push a teammate into a task solely because a deadline is near when blockers/prerequisites make success unrealistic.
- Flag legal/security/privacy/compliance questions that require qualified human review.
- Keep one source of truth for each decision/artifact; project issues should point to detail rather than copy it everywhere. On GitHub, issue bodies are canonical and Project fields are structured indexes, not competing copies of the full task contract.
- Prefer explicit dependencies over implied ordering.
- Preserve the PM's ability to override priorities and phase decisions.
