# Technical Implementation Spec: PM Intelligence and Evidence-Driven Initialization

## Status

Proposed implementation specification for `skills/project-management-rpm`.

## Problem

`project-management-rpm` has a strong project model, but its human experience is optimized more for complete records than for fast understanding and evidence-backed steering.

Two problems should be solved together:

1. **Operational clarity.** PMs and teammates should understand project state, health, blockers, decisions, ownership, and next actions without manually reading multiple issues.
2. **Initialization quality.** Existing projects must be initialized from their actual history. Prior-phase evidence, failed assumptions, pilots, releases, customer usage, decisions, and unresolved gaps must be reconstructed before the active phase is selected.

The PM skill should evolve from a project-record manager into a **project-management intelligence layer** over canonical project records.

## Goals

The implementation must:

- Keep GitHub Issues as durable human-readable contracts and preserve tracker abstraction.
- Make `status` a one-screen PM cockpit answering: where are we, are we on track, what changed, what needs attention, what decisions are pending, and what should the PM do next.
- Add teammate-specific views answering: what am I doing, why, what does done mean, what blocks me, what is waiting for me, and what should I do next.
- Add an evidence ledger with explicit states, confidence, freshness, sources, and contradictory evidence.
- Rebuild `init` around artifact discovery, history reconstruction, prior-phase evidence audit, phase recommendation, evidence-based pushback, inherited gaps, team model, and operating model.
- Separate product maturity, phase evidence/health, and delivery progress.
- Make decisions and blockers first-class PM concerns with age, ownership, downstream impact, and escalation guidance.
- Make meaningful tasks traceable to milestone, phase exit criterion, phase goal, and project north star where applicable.
- Generate exactly one recommended next PM action in status-oriented PM views.
- Support migration of existing PM-managed projects without recreating canonical issues.

## Non-goals

This work must not:

- Replace Wayfinder for structured uncertainty exploration.
- Replace `to-spec-rpm`, `to-tickets-rpm`, `implement-rpm`, `tdd-rpm`, or `code-review-rpm`.
- Require GitHub Projects; Issues-only mode must continue to work.
- Automatically advance a product phase without PM confirmation.
- Require every prior-phase criterion to be perfect before proceeding.
- Turn initialization into a fixed questionnaire.
- Duplicate existing engineering or Wayfinder issues just to enroll them in PM.
- Treat task completion percentage as phase completion.

---

# 1. Canonical PM model

Use this hierarchy consistently in PM output and templates:

```text
PROJECT
  -> PHASE
      -> MILESTONE
          -> TASK
```

A sprint is a time grouping over tasks, not another outcome level.

Every meaningful task should support this outcome chain:

```text
TASK
  -> MILESTONE
      -> PHASE EXIT CRITERION
          -> PHASE GOAL
              -> PROJECT NORTH STAR
```

Administrative or operational tasks may not have every link. In that case the issue should explain which risk, decision, operating requirement, or project outcome justifies the task.

The agent should challenge work that appears unrelated to any project outcome, risk, decision, or operating requirement.

---

# 2. New evidence model

## 2.1 New artifact: `EVIDENCE-LEDGER.md`

Add `skills/project-management-rpm/EVIDENCE-LEDGER.md` as the template and contract for evidence records.

For project instances, the actual evidence ledger should live in the configured project-document area, preferably `docs/agents/project-evidence.md` unless the repository already has a stronger convention.

Each material phase claim or foundational assumption should support:

- stable evidence ID, e.g. `E-001`,
- product phase,
- exit criterion / assumption / claim,
- evidence state,
- evidence summary,
- evidence sources/links,
- evidence date,
- last validated date,
- confidence,
- freshness,
- owner,
- contradictory evidence,
- follow-up / evidence gap.

Canonical evidence states:

- `Proven`
- `Partial`
- `Assumed`
- `Unknown`
- `Contradicted`

Canonical confidence values:

- `High`
- `Medium`
- `Low`

Canonical freshness values:

- `Current`
- `Aging`
- `Stale`
- `Not time-sensitive`

Confidence refers to confidence in the evidence, not confidence expressed by the PM or team.

## 2.2 Evidence evaluation rules

Prefer observable evidence over unsupported opinion. Stronger evidence may include production usage, repeated customer behavior, payment/revenue behavior, signed commitments, reproducible measurements, and repeated experiments. Interviews, pilots, and structured qualitative evidence may be high-quality depending on method and sample. Team intuition without supporting evidence should normally remain an assumption.

Always distinguish:

- facts,
- evidence-backed conclusions,
- assumptions.

When the target segment, product, market, technology, or operating environment materially changes, old evidence may no longer be current. The skill should downgrade freshness and surface revalidation as a risk or attention item.

---

# 3. Inherited gaps

## 3.1 New artifact: `INHERITED-GAP.md`

Add `skills/project-management-rpm/INHERITED-GAP.md`.

An inherited gap records a material earlier-phase criterion that was not sufficiently proven before the project intentionally proceeded.

Fields:

- stable gap ID, e.g. `G-001`,
- source phase,
- criterion / assumption,
- current evidence state,
- why the project proceeded anyway,
- risk level: Low / Medium / High / Critical,
- owner,
- required follow-up,
- revisit date,
- related current milestone / criterion,
- impact if wrong,
- resolution state.

Inherited gaps allow real projects to advance without either pretending all earlier work was complete or mechanically blocking progress.

Inherited gaps remain visible in PM status until resolved, deliberately accepted as a continuing risk, or superseded by a later decision/evidence item.

---

# 4. Decisions as first-class PM state

## 4.1 New artifact: `DECISION.md`

Add `skills/project-management-rpm/DECISION.md` as a tracker-neutral decision record.

A decision record should support:

- stable decision ID, e.g. `D-014`,
- decision question,
- context,
- owner / decision authority,
- needed-by date,
- options considered,
- current recommendation,
- evidence supporting the recommendation,
- risks/tradeoffs,
- tasks/milestones/criteria blocked,
- status: `Open`, `Investigating`, `Ready to decide`, `Decided`, `Superseded`,
- final decision,
- rationale,
- Wayfinder link when uncertainty is explored there.

The PM layer must not duplicate Wayfinder detail. If Wayfinder owns the uncertainty work, PM status only summarizes owner, deadline, impact, state, recommendation, and link.

---

# 5. Rewrite `init` as evidence-driven onboarding

Replace the current short initialization sequence with an adaptive onboarding flow.

## Stage 1 — Artifact discovery

Before asking the PM questions, inspect existing evidence:

- canonical project/phase records if present,
- `docs/agents/*`,
- domain docs and ADRs,
- product/business docs,
- proposals,
- research,
- prior specs,
- Wayfinder maps and resolved decisions,
- open and closed issues,
- milestones/releases,
- customer validation artifacts when available,
- usage/analytics evidence when available through project-provided sources.

The objective is to avoid asking the PM to repeat information that is already reasonably established.

Build a provisional project model with confidence markers before the interview begins.

## Stage 2 — Project identity

Establish or confirm:

- product/project name,
- what is being built,
- primary user,
- customer/payer if different,
- problem/job-to-be-done,
- value proposition,
- why the project exists now,
- 12–24 month durable desired outcome,
- north star.

Ask only about unresolved, missing, or contradictory items.

## Stage 3 — Project-history reconstruction

For existing projects, reconstruct material history:

- project origin,
- major experiments and prototypes,
- releases/deployments,
- pilots/customer engagements,
- product/business/technical decisions,
- failed approaches,
- abandoned work,
- pivots,
- target-segment changes,
- business-model changes,
- invalidated assumptions.

Summarize history as:

- Tried
- Learned
- Decided
- Abandoned
- Still uncertain

Do not require perfect chronology. Capture only history that affects current project decisions or prevents repeated mistakes.

## Stage 4 — Prior-phase evidence audit

Starting at Phase 0, evaluate each phase before the candidate current phase.

For every material criterion, determine:

1. What evidence exists?
2. How directly does it support the criterion?
3. How strong is it?
4. How recent is it?
5. Is contradictory evidence present?
6. What remains unknown?
7. Is the missing evidence still relevant to the current product?

Ask the PM only when the repository/tracker evidence cannot resolve these questions.

Write/update evidence-ledger entries as conclusions stabilize.

## Stage 5 — Recommend current phase

Do not begin by asking the PM which phase they are in.

Produce a recommendation containing:

- recommended phase,
- confidence: High / Medium / Low,
- strongest supporting evidence,
- unresolved criteria from earlier phases,
- contradictory evidence,
- reason the next higher phase is not yet recommended when applicable.

Example:

```text
Recommended phase: Phase 2 — MVP
Confidence: High

Why
- Phase 0 problem/customer evidence is sufficient.
- The core value proposition has been demonstrated.
- Real-user usage exists.
- Repeatable successful usage is only partially evidenced.
- Retention evidence is still missing.
```

## Stage 6 — Evidence-based challenge and PM confirmation

The PM remains final authority, but the agent must not silently accept a phase claim that materially conflicts with evidence.

If the PM chooses a higher phase than recommended, surface the exact evidence conflict and offer two explicit paths:

1. remain in the recommended phase, or
2. proceed to the PM-selected phase while recording unresolved criteria as inherited gaps.

When the PM overrides, record:

- the override,
- evidence gap,
- reason for proceeding,
- risk owner.

Do not challenge for stylistic differences or low-impact uncertainty.

## Stage 7 — Define the current phase

Capture:

- one outcome-oriented phase goal,
- 3–7 observable exit criteria,
- evidence plan for each material criterion,
- target date or explicit no-date decision,
- scope,
- out of scope,
- major assumptions,
- material risks,
- critical decisions.

Each evidence plan should contain:

- evidence required,
- source/mechanism,
- target/threshold where applicable,
- owner,
- current state.

## Stage 8 — Team model

Capture enough team context to support task recommendation and escalation:

- members,
- roles,
- relevant skills,
- technical depth,
- availability/capacity,
- decision authority,
- external collaborators/dependencies.

Do not store sensitive personal data beyond what is needed for execution.

## Stage 9 — Operating model

Capture:

- sprint/Scrum vs continuous flow,
- sprint length if applicable,
- planning cadence,
- PM/status review cadence,
- retrospective cadence if used,
- estimation convention,
- Definition of Ready,
- Definition of Done,
- assignment/claim convention,
- review convention.

Recommend defaults only when necessary and ask the PM to confirm.

## Stage 10 — Baseline confirmation

Before creating/updating PM records, present one consolidated baseline:

- north star,
- recommended and confirmed phase,
- recommendation confidence,
- prior-phase evidence summary,
- inherited gaps,
- invalidated assumptions,
- current foundational assumptions,
- phase goal,
- exit criteria + evidence plans,
- major risks,
- critical decisions,
- team model,
- operating model,
- first recommended PM action.

Ask the PM to confirm or correct the baseline.

Only after confirmation should initialization write canonical state.

## Init completion contract

Initialization is complete only when:

- project identity and north star exist,
- existing artifacts were inspected,
- relevant project history was reconstructed,
- prior phases were audited sufficiently,
- evidence ledger exists,
- phase recommendation + confidence were produced,
- PM confirmed or overrode the recommendation,
- inherited gaps were recorded,
- current phase goal + 3–7 exit criteria exist,
- evidence plans exist for material criteria,
- current risks/assumptions/decisions are recorded,
- team and operating models are sufficient,
- PM confirmed the baseline,
- canonical project/phase records exist,
- a coherent PM cockpit can render,
- exactly one next PM action can be recommended.

---

# 6. Rewrite `status` as a PM cockpit

The default status response should fit on one screen where practical and use progressive disclosure.

Required sections, in order:

1. Project + north-star summary.
2. Current phase + phase goal.
3. Health classification + one-line reason.
4. Phase evidence summary.
5. Delivery summary.
6. Current focus.
7. Attention Required.
8. Decisions Needed.
9. Critical blockers.
10. Material risks.
11. Team snapshot.
12. Important changes since the last PM review when available.
13. Exactly one Next Best PM Action.

Do not dump all open work.

## 6.1 Three-level status separation

Always distinguish:

- **Product maturity:** current product phase.
- **Phase state:** evidence progress + phase health.
- **Delivery state:** sprint/milestone/work progress.

Never use delivery completion as phase completion.

## 6.2 Phase evidence summary

Prefer state counts over a misleading percentage:

```text
Phase evidence
3 Proven / 2 Partial / 2 Unknown
```

A percentage may be secondary, but the evidence states remain authoritative.

---

# 7. Project/phase health model

Canonical health values:

- `On Track`
- `At Risk`
- `Off Track`
- `Unknown`

Derive health from explainable signals such as:

- critical blocker count and age,
- deadline/milestone slippage,
- phase evidence gaps,
- missing evidence plans,
- unresolved critical decisions,
- unowned P0/P1 work,
- sprint commitment vs capacity,
- dependency risk,
- inherited high-risk gaps,
- contradictory evidence.

Do not use a black-box numerical score as source of truth.

A health classification should expose the top 1–3 reasons.

Use `Unknown` rather than false certainty when evidence is insufficient.

---

# 8. `Attention Required`

Add an explicit PM-cockpit section containing only items requiring human intervention.

Examples:

- critical blocker older than configured threshold,
- P0 work without owner,
- critical decision overdue,
- milestone forecast late,
- phase criterion with no evidence plan,
- contradictory evidence threatening a foundational assumption,
- idle teammate while high-priority eligible work exists,
- access/dependency issue requiring escalation.

If nothing needs intervention, print `None`.

Each attention item should state:

- what happened,
- why it matters,
- who needs to act when known.

---

# 9. New `decisions` mode

Add a `decisions` mode to `SKILL.md`.

Show open decisions ordered by impact and needed-by date, including:

- owner,
- deadline,
- status,
- blocked tasks/milestones,
- current recommendation,
- Wayfinder pointer when applicable.

`status` shows only critical decisions; `decisions` provides the operational list.

Critical decisions with no owner appear in Attention Required.

---

# 10. Blocker intelligence

For blocked work derive/store where possible:

- blocker issue/decision,
- blocked-since date,
- blocker age,
- blocker owner,
- direct downstream tasks,
- milestone impact,
- exit-criterion impact,
- deadline impact,
- escalation need.

Rank blockers by impact and age, not merely by `Blocked` state.

When a task transitions to Blocked, the adapter should support recording a blocked timestamp in structured metadata when Projects is enabled. In Issues-only mode, use a machine-readable issue marker/comment according to the adapter contract.

When the task leaves Blocked, preserve historical evidence where useful but clear the active blocked timestamp.

---

# 11. Workflow simplification

Change the conceptual workflow to:

```text
Backlog -> Ready -> In Progress -> Review -> Done
                 \-> Blocked -> Ready/In Progress
```

Ownership is a separate dimension represented by GitHub assignee.

Deprecate `Claimed` as a persistent work-progress state.

Compatibility behavior:

- existing `pm:claimed` issues remain readable,
- migration maps `Claimed` + assignee to `Ready` unless there is evidence work has started,
- `claim` remains an assignment action but no longer needs a distinct persistent status,
- `start <ticket>` transitions assigned Ready work to In Progress.

This avoids conflating reservation/ownership with execution state.

---

# 12. New teammate modes

## `my-work`

Show the invoking teammate's assigned active work.

Required sections:

- current task(s),
- status/priority/due date,
- why it matters / outcome chain,
- acceptance-criteria summary,
- blockers,
- reviews/waiting items,
- next ready task,
- brief project/phase context.

## `pick-next`

Rank eligible Ready work.

Eligibility requires:

- blockers resolved,
- prerequisites satisfied or intentionally accepted as first work,
- no conflicting owner,
- required access available.

Ranking signals:

1. phase-goal/exit-criterion impact,
2. priority,
3. unlocking value/downstream dependencies,
4. deadline urgency,
5. sprint commitment,
6. milestone criticality,
7. skill match,
8. technical-depth match,
9. capacity/effort fit.

Return one recommended task and at most two alternatives, with rationale.

## `team`

Show:

- teammate,
- active item,
- work status,
- blocker state,
- waiting reviews,
- idle status.

End with one flow recommendation when an obvious rebalance exists.

## `today`

Compact PM daily view:

- current health,
- attention count,
- top PM priorities,
- important changes since last review,
- newly unblocked work,
- overdue decisions,
- exactly one next PM action.

## Teammate lifecycle actions

Normalize/document:

- `start <ticket>`
- `block <ticket>`
- `handoff <ticket>`
- `review <ticket>`
- `done <ticket>`

Each action validates ownership/status and preserves reason/evidence for the transition.

---

# 13. Next Best Action engine

All PM status-style outputs (`status`, `today`, `phase-review`) should select exactly one next PM action.

Rank candidate actions by:

1. preventing phase-goal failure,
2. unblocking the largest amount of critical work,
3. resolving overdue/high-impact decisions,
4. addressing evidence gaps that gate phase completion,
5. protecting near-term milestones/deadlines,
6. assigning high-priority unowned work,
7. resolving team-flow bottlenecks.

Output:

- action,
- why it is highest priority,
- impacted milestone/criterion/work where relevant.

Avoid ending with a generic menu of suggestions.

---

# 14. Change detection

Add a lightweight PM-review snapshot mechanism.

Preferred implementation:

- store `last_pm_review_at` in `docs/agents/project-management.md` or tracker configuration,
- when rendering `today` or `status`, query changes after that timestamp,
- report material changes only,
- update the timestamp only for explicit PM review acknowledgement or mutating PM action, not every read.

Material changes include:

- workflow transition,
- blocker added/removed,
- decision opened/decided/overdue,
- new evidence or evidence-state change,
- milestone health change,
- deadline change,
- new high-severity risk,
- newly unblocked work,
- active teammate becoming idle.

The first version does not need perfect event sourcing. Use tracker timestamps/comments and current-vs-last-review state where possible.

---

# 15. Update `PROJECT-ISSUE.md`

Add concise sections:

- `Product maturity baseline`
  - current phase,
  - phase-confidence,
  - assessed date.
- `Project health`
  - classification,
  - top reasons.
- `Prior-phase evidence summary`
  - one line per phase + ledger link.
- `Inherited gaps`
  - IDs/links only.
- `Invalidated assumptions`
- `Open foundational assumptions`
- `Critical decisions`
- `Current PM priority`
  - exactly one action.
- `Evidence ledger`
  - pointer to canonical project evidence document.

Do not copy detailed evidence into the project issue; keep it as an index/cockpit anchor.

---

# 16. Update `PHASE-ISSUE.md`

Add:

- phase recommendation confidence at activation,
- health,
- exit-criterion evidence table,
- evidence plan per criterion or linked evidence-plan IDs,
- inherited gaps relevant to this phase,
- foundational assumptions,
- critical decisions,
- material risks,
- transition recommendation/evidence at phase review.

Each exit criterion should support:

- criterion ID,
- criterion,
- evidence state,
- evidence owner,
- evidence source/pointer,
- target/threshold where relevant.

---

# 17. Update `TASK-ISSUE.md`

Keep the detailed task contract but add a compact scan section near the top:

- Outcome
- Why this matters
- Owner (assignee remains authoritative)
- Status
- Priority
- Product phase
- Milestone
- Phase criterion
- Due date
- Blocked by
- Done when / acceptance-criteria summary

Add `Outcome traceability` below planning metadata:

- North-star contribution
- Phase goal
- Exit criterion
- Milestone

If a field is not applicable, state why rather than inventing a relationship.

Retain existing prerequisite, skill, technical-depth, collaboration, and acceptance-criteria sections.

---

# 18. Update `GITHUB-ADAPTER.md` and `github_adapter.py`

## Preserve source-of-truth split

Continue using:

- issue body for full work/evidence contracts,
- assignee for ownership,
- native relationships for parent/blocking edges,
- labels for portable PM identity/workflow,
- Project fields for sortable metadata.

## Canonical workflow values

Change `PM Status` values to:

- Backlog
- Ready
- In Progress
- Blocked
- Review
- Done

Treat `Claimed` as deprecated compatibility input.

## New Project fields when Projects is enabled

Add where practical:

- `Health` — On Track / At Risk / Off Track / Unknown
- `Evidence Status` — Proven / Partial / Assumed / Unknown / Contradicted
- `Evidence Confidence` — High / Medium / Low
- `Decision Status` — Open / Investigating / Ready to decide / Decided / Superseded
- `Blocked Since` — date
- `Risk Severity` — Low / Medium / High / Critical
- `Phase Criterion` — text
- `Next Review` — date

Do not mirror long-form explanations into Project fields.

## Adapter behavior/commands

Add/extend:

- `state <issue> <status>` with blocked timestamp semantics,
- `claim <issue>` as assignment without requiring Claimed status,
- `start <issue>` -> In Progress,
- `block <issue> --reason ... [--blocked-by ...]` -> Blocked + timestamp,
- `unblock <issue>` -> explicit/prior Ready or In Progress state,
- decision creation/update when decisions are represented as issues,
- evidence metadata enrollment/update where sortable Project metadata helps.

All mutations must re-read live state and protect against concurrent ownership/status conflicts.

## Bootstrap compatibility

Bootstrap must remain idempotent and non-destructive.

Do not destructively remove an existing `Claimed` option from an existing Project field. Add required new options, mark Claimed deprecated in docs/config, and normalize items gradually during migration.

---

# 19. New `migration` mode

Add `project-management migration` (or `migrate-pm`) for repositories already using the current/older PM model.

It should:

1. read canonical project + active phase,
2. inspect existing work and phase history,
3. build provisional prior-phase evidence from existing artifacts,
4. ask the PM only about unresolved high-value gaps,
5. initialize the evidence ledger,
6. identify inherited gaps and invalidated assumptions,
7. establish health and decision records,
8. migrate Claimed workflow state safely,
9. add missing outcome traceability to active/high-priority work first rather than rewriting the full backlog,
10. render a PM cockpit and ask the PM to confirm the migrated baseline.

Migration must not recreate existing project/phase/task issues.

---

# 20. Update mode dispatcher

Extend the dispatcher with:

- `today`
- `decisions`
- `team`
- `my-work`
- `pick-next`
- `start <ticket>`
- `block <ticket>`
- `handoff <ticket>`
- `review <ticket>`
- `migration`

Routing guidance:

- `today` requires an initialized project; otherwise route to `init`.
- `decisions` requires a project; returning no decisions is valid.
- `team` requires project + tracker access.
- `my-work` requires project + resolvable teammate identity.
- `pick-next` requires at least one eligible Ready task; otherwise explain why no work is claimable.
- `migration` requires existing older PM state; if none exists, recommend `init`.

When invoked without a mode, keep `resume` behavior but prefer a `today`/cockpit-style presentation for active projects.

---

# 21. Update `status` post-condition

A successful status must include:

- current product phase,
- phase goal,
- phase recommendation confidence where known,
- health + reasons,
- exit-criterion evidence summary,
- active sprint/milestone delivery summary or explicit none,
- current focus,
- Attention Required or explicit none,
- critical Decisions Needed or explicit none,
- critical blockers or explicit none,
- material risks or explicit none,
- teammate/work-flow snapshot,
- changes since last PM review when available,
- exactly one Next Best PM Action.

Status remains read-only unless the user explicitly requests correction/mutation.

---

# 22. Phase-review changes

`phase-review` must use evidence-ledger state, not only issue completion.

For each exit criterion report:

- evidence state,
- confidence,
- source,
- freshness,
- remaining gap.

Recommend one of:

- Advance
- Extend
- Pivot
- Pause
- Stop

If recommending Advance while unresolved criteria remain, explicitly propose inherited gaps and require PM confirmation.

A phase transition must snapshot:

- evidence summary,
- unresolved inherited gaps,
- invalidated assumptions,
- transition decision/rationale,
- PM override when recommendation was not followed.

---

# 23. Risk model

For material risks support:

- risk ID,
- description,
- probability: Low / Medium / High,
- impact: Low / Medium / High / Critical,
- owner,
- trigger/leading indicator,
- mitigation,
- target/review date,
- related milestone/criterion,
- status.

Only the highest-impact live risks belong in the default cockpit.

Do not force ordinary task concerns into formal risk records.

---

# 24. Milestone health

Milestones should support:

- outcome,
- target date,
- dependencies,
- related exit criteria,
- work progress,
- health,
- key blocker/risk,
- forecast completion where inferable.

Canonical milestone health:

- On Track
- At Risk
- Off Track
- Complete
- Unknown

Avoid false-precision forecasting when data is insufficient.

---

# 25. Agent pushback rules

Add an explicit `PM challenge rules` section to `SKILL.md`.

The agent should challenge when:

- a phase claim lacks material required evidence,
- a supposedly completed exit criterion lacks evidence,
- current evidence contradicts an assumption,
- stale evidence is treated as current despite material context change,
- a milestone has no observable outcome,
- a critical decision has no owner,
- P0/P1 Ready work is unowned without reason,
- project progression hides a material earlier-phase gap,
- a task has no meaningful connection to outcomes/risk/operations,
- stated project health conflicts with current evidence.

The agent should not challenge merely because:

- it prefers different wording,
- uncertainty is immaterial,
- the PM explicitly accepts a known and recorded risk,
- required evidence cannot reasonably exist yet.

Challenge should be specific and evidence-based: state the conflict, consequence, options, and recommendation; the PM decides.

---

# 26. File-by-file implementation plan

## `skills/project-management-rpm/SKILL.md`

Major additions/rewrites:

- product principles,
- expanded dispatcher,
- evidence-driven `init`,
- cockpit `status`,
- `today`, `decisions`, `team`, `my-work`, `pick-next`, teammate actions,
- `migration`,
- health model,
- Attention Required,
- next-best-action rules,
- blocker intelligence,
- change detection,
- phase-review evidence behavior,
- pushback rules,
- updated atomic post-condition checks.

## `skills/project-management-rpm/PROJECT-ISSUE.md`

Add maturity baseline, health, prior-phase evidence summary, inherited gaps, invalidated assumptions, open assumptions, critical decisions, evidence pointer, and current PM priority.

## `skills/project-management-rpm/PHASE-ISSUE.md`

Add evidence table/plans, phase confidence, health, inherited gaps, assumptions, decisions, risks, and evidence-based transition summary.

## `skills/project-management-rpm/TASK-ISSUE.md`

Add compact scan header and outcome traceability while retaining detailed prerequisites/skills/acceptance criteria.

## `skills/project-management-rpm/GITHUB-ADAPTER.md`

Document new status model, new fields, decision/evidence conventions, blocked-timestamp behavior, new commands, and compatibility migration.

## `skills/project-management-rpm/github_adapter.py`

Implement field/status additions, assignment-only claim semantics, start/block/unblock helpers, decision operations where GitHub-backed, and migration behavior.

## New: `skills/project-management-rpm/EVIDENCE-LEDGER.md`

Define project evidence-ledger contract.

## New: `skills/project-management-rpm/INHERITED-GAP.md`

Define inherited-gap records.

## New: `skills/project-management-rpm/DECISION.md`

Define PM decision records.

## Tests

If adapter tests do not currently exist, add focused unit tests around pure/state-transition logic before broad integration testing. Tests must not require live GitHub credentials.

---

# 27. Recommended implementation sequence

Implement in vertical increments.

## Increment 1 — Evidence foundation + init

Deliver:

- evidence templates,
- evidence states/confidence/freshness,
- prior-phase audit,
- phase recommendation/challenge,
- inherited gaps,
- baseline confirmation,
- project/phase template updates.

Acceptance signal: an existing project can be initialized without pretending it starts at Phase 0, and the baseline explains why the active phase is justified.

## Increment 2 — PM cockpit

Deliver:

- status rewrite,
- health model,
- Attention Required,
- decision summary,
- blocker intelligence,
- one next-best action.

Acceptance signal: a PM can answer core status questions from one response without manually opening multiple issues.

## Increment 3 — Teammate experience

Deliver:

- `my-work`,
- `pick-next`,
- `team`,
- `today`,
- outcome traceability,
- lifecycle actions.

Acceptance signal: a teammate can identify current responsibility and next eligible work with rationale.

## Increment 4 — GitHub adapter + migration hardening

Deliver:

- workflow simplification,
- blocked timestamps,
- new Project fields,
- migration mode,
- compatibility behavior,
- adapter tests.

Acceptance signal: an existing GitHub-backed project migrates without duplicate issues or destructive Project-field changes.

## Increment 5 — Change detection + forecasting

Deliver:

- last-review snapshot,
- material change reporting,
- milestone health/forecast reasoning,
- evidence freshness alerts.

Acceptance signal: `today` emphasizes changes and required actions instead of repeating static status.

---

# 28. Acceptance criteria

## Initialization

- [ ] Existing artifacts are inspected before PM interview.
- [ ] PM is not asked to repeat reasonably established information.
- [ ] Relevant prior phases are audited into the evidence ledger.
- [ ] Evidence distinguishes Proven, Partial, Assumed, Unknown, and Contradicted.
- [ ] Evidence supports confidence and freshness.
- [ ] Agent recommends current phase and states confidence/reasons.
- [ ] Agent challenges materially unsupported phase claims.
- [ ] PM overrides are allowed and recorded.
- [ ] Unresolved prior criteria can become inherited gaps.
- [ ] Current phase has goal, 3–7 exit criteria, and evidence plans.
- [ ] Team and operating models are sufficiently established.
- [ ] PM confirms consolidated baseline before finalization.

## PM cockpit

- [ ] Status separates product maturity, phase evidence/health, and delivery.
- [ ] Status contains Attention Required, decisions, critical blockers, risks, team snapshot, and recent changes where available.
- [ ] Health is explainable using On Track / At Risk / Off Track / Unknown.
- [ ] Status ends with exactly one next-best PM action.
- [ ] PM can understand project condition without reading every active issue.

## Teammate experience

- [ ] `my-work` shows responsibility, why it matters, done criteria, blockers, waiting work, and next work.
- [ ] `pick-next` recommends only eligible work and explains ranking.
- [ ] `team` identifies blocked/idle/review bottlenecks.
- [ ] Meaningful tasks support an outcome chain to project goals.

## Decisions and blockers

- [ ] Critical decisions have owner, needed-by date, impact, and state.
- [ ] Open Wayfinder decisions can surface in status without duplicating full detail.
- [ ] Blocked tasks expose blocker age/downstream impact when available.
- [ ] Long-running/high-impact blockers are elevated into Attention Required.

## GitHub compatibility

- [ ] Issues remain canonical work contracts.
- [ ] Assignee remains canonical ownership.
- [ ] Native relationships remain canonical dependencies.
- [ ] Projects remains optional.
- [ ] Legacy Claimed state remains readable and migratable.
- [ ] Migration does not recreate existing PM/task issues.
- [ ] Bootstrap remains idempotent and non-destructive.

---

# 29. Definition of success

The finished PM layer should make the underlying model more sophisticated while making the human experience simpler.

A PM should be able to answer from one status view:

- Where are we?
- Are we on track?
- What are we trying to prove?
- What evidence do we have?
- What changed?
- What requires attention?
- What decisions are waiting?
- What is blocking progress?
- What is the team doing?
- What should I do next?

A teammate should be able to answer:

- What am I responsible for?
- Why does it matter?
- What does done mean?
- What blocks me?
- What is waiting for me?
- What should I work on next?

The implementation should preserve the current PM skill's durable records and lifecycle discipline while adding an evidence model, role-specific views, and an explicit intelligence layer that turns project data into decisions and actions.
