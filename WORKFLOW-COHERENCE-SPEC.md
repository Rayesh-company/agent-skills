# Technical Implementation Spec: Coherent Acceptance Loop

## Status

Proposed repository-level implementation specification.

## Problem

The repository contains strong specialist skills, but the complete workflow is
currently expressed as a set of handoffs rather than one enforceable lifecycle.
Each skill defines its own preconditions, completion checks, failure behavior,
and next step. Those local contracts are useful, but they can drift from the
router, project-management layer, templates, adapter, and neighboring skills.

This creates four stability risks:

1. a skill may declare completion while ticket or phase acceptance remains
   unsatisfied;
2. a failed verification may be patched locally instead of returning to the
   stage that owns the gap;
3. state can be partially updated across issue bodies, labels, assignment,
   relationships, Project fields, and repository artifacts;
4. a router or supporting document can continue promising behavior after the
   operational skill changes.

The workflow needs one canonical loop that every layer composes. The loop must
iterate until explicit acceptance, retain evidence from every pass, and stop
safely when acceptance cannot be reached within the current authority or scope.

## Goals

The implementation must:

- define one observable acceptance loop shared by every workflow;
- distinguish behavior work, ticket work, milestone work, and phase work;
- route each failed check to the skill or human that owns the missing decision;
- make acceptance evidence durable and traceable;
- keep one source of truth for each kind of state;
- make mutating operations idempotent, resumable, and recoverable;
- detect contract drift automatically in continuous integration;
- preserve tracker abstraction and GitHub Issues-only operation;
- keep the PM as final authority for product-phase decisions;
- end every iteration with exactly one next action or a terminal state.

## Non-goals

This work must not:

- merge all skills into one large skill;
- replace Wayfinder, project-management, TDD, implementation, or code review;
- treat tests as the only form of acceptance evidence;
- automatically accept product outcomes without PM confirmation;
- retry indefinitely without changing the evidence or approach;
- make GitHub Projects mandatory;
- duplicate an issue or artifact to enroll it in another workflow;
- require transactional infrastructure that the configured tracker cannot
  support.

---

# 1. Canonical vocabulary

Use these terms consistently across skills, templates, adapter output, and
reports.

## Scope

The smallest unit currently being advanced. A scope is exactly one of:

- **Behavior slice** — one observable behavior at one seam.
- **Ticket** — one executable work contract with acceptance criteria.
- **Milestone** — one outcome composed from accepted tickets.
- **Product phase** — one product question completed through exit evidence and
  an explicit PM decision.

An iteration operates on one scope. A parent scope may observe accepted child
scopes, but it does not silently absorb their unaccepted work.

## Acceptance contract

The acceptance contract is the durable statement of what must be true before a
scope is accepted. It contains:

- scope identity and owner;
- acceptance criteria;
- verification method for each criterion;
- required evidence;
- authority that accepts the result;
- terminal constraints or out-of-scope boundaries.

## Evidence

Evidence is an observable result linked to an acceptance criterion. Examples
include a failing-then-passing test, typecheck output, artifact, commit, review
finding resolution, research source, demo, usage signal, or PM decision.

Evidence must identify:

- the criterion it supports;
- where it can be inspected;
- when it was produced or validated;
- whether it proves, partially supports, contradicts, or does not address the
  criterion.

## Gap

A gap is the difference between current evidence and the acceptance contract.
Every failed verification must be classified as one gap type before more work
begins.

Canonical gap types:

- `behavior` — implementation does not produce the required behavior;
- `test` — verification is absent, insensitive, flaky, or invalid;
- `specification` — acceptance criteria are ambiguous, contradictory, or
  missing;
- `design` — the agreed seam or module boundary cannot support the requirement;
- `knowledge` — a material fact or external constraint is unknown;
- `decision` — a human or PM choice is required;
- `dependency` — another scope, access grant, or external event blocks progress;
- `quality` — the result works but violates an applicable standard;
- `evidence` — the work may be complete but proof is missing or stale;
- `state-drift` — canonical and mirrored state disagree;
- `scope` — the requested change falls outside the accepted contract.

## Acceptance

Acceptance is explicit. A scope is accepted only when:

1. every criterion has current evidence;
2. all required verification passes;
3. no unresolved critical finding remains;
4. canonical state and mirrors agree;
5. the named acceptance authority confirms when human judgment is required.

Completion activity without these conditions is progress, not acceptance.

---

# 2. The canonical acceptance loop

Every workflow mode that advances state must implement this loop.

```text
OBSERVE -> SELECT -> EXECUTE -> VERIFY -> EVALUATE
   ^                                      |
   |                                      v
   +--- ROUTE GAP <- NOT ACCEPTED <- CLASSIFY
                                          |
                                          v
                                      ACCEPTED
                                          |
                                          v
                                  RECORD -> HAND OFF
```

## Step 1 — Observe

Read live canonical state before acting:

- current scope and acceptance contract;
- relevant issue body and comments;
- assignment and dependency relationships;
- workflow labels and optional Project fields;
- repository artifacts, tests, domain docs, ADRs, and specs;
- evidence and unresolved findings from prior iterations.

Produce an iteration snapshot with a stable scope identity. Cached state may
orient the agent, but live state governs mutation.

**Completion criterion:** one unambiguous scope, acceptance contract, current
evidence set, and mutation target are known.

## Step 2 — Select

Choose exactly one smallest useful change that can reduce a known gap. Prefer a
vertical behavior slice or one decision over a broad batch.

Record:

- selected gap;
- owner of the gap;
- intended evidence;
- expected state change;
- commands or human decision needed to verify it.

**Completion criterion:** the iteration has one gap and a checkable expected
result.

## Step 3 — Execute

Invoke the specialist that owns the gap and let it apply only the selected
change. Examples:

- behavior or test -> `tdd-rpm` inside `implement-rpm`;
- specification -> `grilling-rpm` or `to-spec-rpm`;
- design -> `codebase-design-rpm` plus a revised ticket/spec;
- knowledge -> `research-rpm`;
- runnable uncertainty -> `prototype-rpm`;
- decision -> `grill-with-docs-rpm` or Wayfinder;
- dependency/access -> PM task or `wizard-rpm`;
- quality -> local refactor or a follow-up ticket, according to scope;
- state drift -> tracker adapter reconciliation.

**Completion criterion:** the selected change exists and no unrelated scope was
silently added.

## Step 4 — Verify

Run the verification method named by the acceptance contract. Verification must
produce inspectable evidence, not an unsupported completion statement.

Use the narrowest relevant check first. Parent-level checks run only after child
scopes pass their focused checks.

**Completion criterion:** every criterion affected by the iteration has a fresh
verdict and evidence pointer.

## Step 5 — Evaluate

Compare the complete current evidence set with the scope's acceptance contract.

The result is exactly one of:

- `Accepted` — all acceptance conditions are satisfied;
- `Not accepted` — one or more actionable gaps remain;
- `Blocked` — progress requires unresolved dependency, access, authority, or
  external state;
- `Needs decision` — acceptance depends on explicit human judgment;
- `Stopped` — the authority chooses to cancel, supersede, or move the scope out
  of scope.

**Completion criterion:** one verdict and its reasons are explicit.

## Step 6 — Classify and route gaps

For `Not accepted`, classify each failed criterion with one canonical gap type.
Choose the highest-impact eligible gap for the next iteration and route it to
its owner.

The next iteration must change at least one of:

- the implementation;
- the test or verification method;
- the acceptance contract through an authorized decision;
- the design/seam;
- the available evidence;
- the dependency or access state.

Repeating the same action against unchanged state is a stalled loop.

**Completion criterion:** exactly one next action is named, or the loop enters a
terminal/blocking state.

## Step 7 — Record acceptance

For `Accepted`:

- attach evidence to the canonical work record;
- synchronize workflow state through the configured adapter;
- record newly unblocked scopes;
- update parent milestone/phase evidence without automatically accepting the
  parent;
- retain review and decision history through links rather than duplicated prose.

**Completion criterion:** canonical state, mirrors, and evidence links agree.

## Step 8 — Hand off

Return exactly one next action:

- begin the next eligible child scope;
- verify the parent scope;
- request a named human decision;
- wait on a named blocker;
- run phase review;
- stop because the requested destination is accepted.

**Completion criterion:** the next actor can continue without reconstructing
the prior iteration.

---

# 3. Loop levels and promotion rules

## Behavior loop

Owner: `tdd-rpm`.

Acceptance requires:

- the new test was observed red for the expected reason;
- minimum implementation made it green;
- justified local refactoring remained green;
- no behavior outside the current slice was added.

Accepted behavior returns to `implement-rpm` for seam-level checks.

## Seam loop

Owner: `implement-rpm`.

Acceptance requires:

- all behavior slices at the seam are accepted;
- focused tests pass;
- typecheck passes;
- the seam remains consistent with the ticket/spec;
- the seam change is committed according to repository policy.

Accepted seams remain child evidence. They do not by themselves accept the
ticket.

## Ticket loop

Owner: the executing specialist plus `project-management-rpm done` for enrolled
work.

Acceptance requires:

- every ticket criterion has evidence;
- full relevant verification passes;
- standards and spec review have no unresolved critical finding;
- artifacts and commits are linked;
- tracker state is synchronized.

## Milestone loop

Owner: `project-management-rpm`.

Acceptance requires the milestone outcome to be demonstrably true. Accepted
tickets are inputs, not automatic proof of the milestone outcome.

## Product-phase loop

Owner: `project-management-rpm phase-review`; acceptance authority: PM.

Acceptance requires:

- each exit criterion has sufficient current evidence;
- contradictory evidence and inherited gaps are visible;
- the phase goal has an outcome verdict;
- the PM explicitly chooses advance, extend, pivot, pause, or stop.

An empty backlog or completed sprint cannot automatically accept a product
phase.

---

# 4. Canonical routing matrix

This table becomes the single source of truth for gap routing. Routers and
specialist skills point here instead of restating it.

| Gap | Owning route | Returns when |
| --- | --- | --- |
| Behavior | `tdd-rpm` via `implement-rpm` | Focused behavior is red-green-refactored |
| Test | `tdd-rpm` | Verification is sensitive, deterministic, and green |
| Specification | `grilling-rpm` or `to-spec-rpm` | Acceptance contract is unambiguous |
| Design | `codebase-design-rpm` | Seam/design decision is recorded |
| Knowledge | `research-rpm` | Cited evidence answers the exact question |
| Decision | Wayfinder or `grill-with-docs-rpm` | Authorized decision is recorded |
| Runnable uncertainty | `prototype-rpm` | Prototype records a verdict, not production code |
| Dependency | PM backlog/prepare or `wizard-rpm` | Dependency is resolved or explicitly accepted |
| Quality | Local refactor, review, or follow-up ticket | Applicable standard is satisfied |
| Evidence | Owning execution skill | Fresh evidence is attached |
| State drift | Tracker adapter reconciliation | Canonical and mirrored state agree |
| Scope | PM/spec authority | Scope is included, deferred, split, or rejected |

If more than one gap applies, address the earliest upstream gap first:

```text
knowledge/decision -> specification -> design -> behavior/test -> quality -> evidence/state
```

This prevents implementation work from compensating for an unresolved product
decision or ambiguous acceptance criterion.

---

# 5. Standard skill contract

Every operational skill must expose these sections or point to a shared contract
that supplies them:

1. **Owns** — the decisions and state this skill controls.
2. **Inputs** — required artifacts and identifiers.
3. **Preconditions** — live checks required before mutation.
4. **Process** — ordered steps with completion criteria.
5. **Verification** — commands, observations, or human checks.
6. **Acceptance** — exact terminal conditions.
7. **Gap routing** — where each failure class returns.
8. **Writes** — canonical and mirrored state touched.
9. **Recovery** — reconciliation behavior after partial failure.
10. **Handoff** — exactly one normal next route.

The contract must use installed canonical skill names ending in `-rpm`. Labels
and user-facing slash commands must be declared separately from skill package
names so normalization cannot silently break routing.

## Router rule

`ask-matt-rpm` is an index, not a second implementation. It must point to the
canonical routing matrix and read the target skill before making a load-bearing
claim. A router consistency check must fail when it names a missing skill or a
mode absent from the target skill.

## Specialist rule

A specialist accepts only its owned scope. It returns evidence and a verdict to
the parent rather than declaring the parent workflow complete.

---

# 6. State and mutation stability

## Canonical state

Preserve the existing source-of-truth split:

- issue body — complete work and acceptance contract;
- native issue relationships — dependency and hierarchy;
- assignee — ownership;
- labels — portable identity and workflow state;
- GitHub Project fields — optional structured mirrors;
- repository artifacts — specs, research, ADRs, tests, and deliverables;
- adapter config — resolved repository and Project identity.

## Mutation protocol

Every multi-write operation must follow:

1. re-read live state;
2. calculate the intended patch and recovery patch;
3. write canonical state first unless a different order is required for safety;
4. write mirrors;
5. re-read and verify invariants;
6. apply the recovery patch when verification fails;
7. record unresolved drift when recovery is impossible.

The adapter must return structured results containing:

- operation id;
- before snapshot;
- completed writes;
- verification results;
- recovery writes;
- final verdict.

Idempotency means rerunning an accepted operation leaves state unchanged and
returns the same semantic result.

## Reconciliation

Add a read-only `reconcile` operation that reports differences among issue
state, labels, assignment, relationships, Project fields, and adapter config.
With explicit confirmation, `reconcile --apply` repairs mirrors from canonical
state. It must not overwrite an ambiguous canonical record.

---

# 7. Iteration record

Each ticket-level or higher iteration writes a compact durable record:

```markdown
## Acceptance iteration <n>

- Scope: <stable identity and link>
- Gap addressed: <canonical gap type + summary>
- Change: <artifact/commit/decision link>
- Verification: <command/check + result link or summary>
- Criteria affected: <criterion ids>
- Verdict: Accepted | Not accepted | Blocked | Needs decision | Stopped
- Remaining gaps: <ids or None>
- Next action: <exactly one route and owner>
```

Do not paste large logs into issues. Link artifacts or provide the minimum
diagnostic excerpt needed to understand the verdict.

The iteration number is scoped to the canonical work record. A resumed agent
reads the latest record before selecting the next gap.

---

# 8. Loop safety

## Progress guard

Before starting another iteration, compare it with the prior iteration. The
loop may continue only when the planned action changes evidence, state, method,
or the authorized acceptance contract.

After two consecutive iterations with the same gap and no material evidence
change, classify the loop as `Stalled` and route to one of:

- specification clarification;
- design reconsideration;
- new research or prototype;
- human/PM decision;
- explicit scope split;
- stop.

## Retry budgets

Retries are gap-specific, not a global arbitrary count:

- transient tool/network failure — retry safely when idempotent;
- deterministic verification failure — change the work before rerunning;
- ambiguous requirement — no implementation retry before clarification;
- missing authority/access — enter Blocked rather than polling inside the
  session;
- contradictory evidence — enter Needs decision or return to Wayfinder.

## Authority boundary

An agent may recommend a change to acceptance criteria, scope, priority, or
phase. Only the authority named by the acceptance contract may approve it. The
change and rationale become part of the iteration record.

---

# 9. Validation and continuous integration

Add a repository validator that treats skill contracts as an interconnected
system.

## Static validation

Validate on every pull request:

- every skill directory has valid `SKILL.md` frontmatter;
- `name` matches the directory name;
- every `agents/openai.yaml` is parseable and names the same skill coherently;
- invocation policies do not contradict across metadata surfaces;
- every referenced `*-rpm` skill exists;
- unscoped legacy skill invocations are rejected;
- every relative document/script link exists;
- every router mode exists in the target operational skill;
- canonical labels, states, phase names, and Project options agree;
- proposed-only specifications are visibly marked and are not described as
  operational behavior;
- scripts parse and expose expected commands.

## Contract tests

Build scenario fixtures with a fake tracker/`gh` boundary. Cover at minimum:

1. first-time setup in Issues-only mode;
2. setup with Projects enabled;
3. resume after a partial initialization failure;
4. Wayfinder decision accepted and handed to specification;
5. behavior failing, then accepted through red-green-refactor;
6. ticket review failure routed back to implementation;
7. ambiguous criterion routed back to specification;
8. claim conflict caused by concurrent assignment;
9. partial state transition recovered or reported as drift;
10. accepted ticket updating—but not automatically accepting—its milestone and
    phase;
11. phase review requiring explicit PM authority;
12. stalled loop escalation.

## Adapter tests

Test pure planning and state-transition logic independently from GitHub. The
`gh` subprocess layer must be injectable so fixtures can simulate success,
conflict, partial failure, and retry without live credentials.

CI acceptance requires static validation, unit tests, scenario contract tests,
and script syntax checks to pass.

---

# 10. Implementation sequence

Implement as vertical increments. Each increment must pass its own acceptance
criteria before the next begins.

## Increment 1 — Contract inventory and normalization

Deliver:

- machine-readable inventory of 37 skills;
- canonical skill names and invocation policies;
- cross-reference and link validator;
- removal of legacy unscoped skill calls;
- explicit separation of proposed specifications from operational contracts.

Acceptance signal: CI can prove that every skill reference and router target
resolves to an installed contract.

## Increment 2 — Shared acceptance contract

Deliver:

- canonical vocabulary and routing matrix in shared reference files;
- standard contract sections in core skills;
- acceptance iteration record template;
- `ask-matt-rpm` pointers to the shared contract.

Apply first to:

- `project-management-rpm`;
- `wayfinder-rpm`;
- `to-spec-rpm`;
- `to-tickets-rpm`;
- `implement-rpm`;
- `tdd-rpm`;
- `code-review-rpm`.

Acceptance signal: one sample feature can move through discovery, delivery,
review, and PM completion with one uninterrupted evidence chain.

## Increment 3 — Adapter recovery and reconciliation

Deliver:

- structured mutation plans/results;
- before/after invariant checks;
- recovery patches for multi-write operations;
- claim-time audit annotation;
- `reconcile` and confirmed `reconcile --apply`;
- fake-`gh` unit tests.

Acceptance signal: every injected partial failure either restores the before
state or reports an explicit recoverable drift record.

## Increment 4 — Parent-scope acceptance

Deliver:

- milestone verification independent of ticket counts;
- phase evidence evaluation independent of delivery completion;
- explicit PM phase authority;
- evidence promotion rules from behavior to seam to ticket to milestone to
  phase.

Acceptance signal: accepted child work cannot incorrectly mark a parent scope
accepted.

## Increment 5 — Stalled-loop and operational views

Deliver:

- progress guard and stalled classification;
- one-next-action enforcement;
- status reporting for current gap, last evidence change, and next owner;
- integration with the PM intelligence work described in
  `skills/project-management-rpm/IMPLEMENTATION-SPEC.md`.

Acceptance signal: repeated unchanged failures escalate to the correct owner
instead of creating an infinite retry loop.

## Increment 6 — Repository governance

Deliver:

- CI workflow;
- contribution and review checklist;
- root README with installation, lifecycle, and versioning guidance;
- compatibility policy for skill renames, labels, modes, and templates;
- changelog/release convention.

Acceptance signal: a new or changed skill cannot merge while breaking the
canonical workflow graph.

---

# 11. Migration and compatibility

Migration must be non-destructive and resumable.

1. Inventory current skill names, modes, labels, fields, and references.
2. Add canonical names and compatibility mappings before removing legacy names.
3. Mark current `Claimed` behavior as operational until the PM intelligence
   specification's workflow migration is implemented.
4. Introduce acceptance iteration records only when new work occurs; do not
   rewrite all historical issues.
5. Reconcile existing PM projects without recreating project, phase, task, or
   Wayfinder issues.
6. Preserve Issues-only mode throughout migration.
7. Remove compatibility paths only in a documented breaking release.

The migration report must list every unresolved ambiguity and require a human
choice rather than guessing canonical state.

---

# 12. Pull-request and review protocol

Every implementation PR created from this specification must include:

- the increment and acceptance criteria it implements;
- links to changed canonical contracts;
- scenario(s) exercised;
- verification commands and results;
- migration or compatibility impact;
- unresolved gaps and intentionally deferred work;
- evidence that routers, operational skills, templates, and adapter behavior
  agree.

Review remains two-axis:

- **Standards** — repository contract, writing quality, state invariants, and
  maintainability;
- **Spec** — increment requirements and acceptance criteria.

A PR is accepted only when both axes have no unresolved blocking finding and CI
passes. Review failures become classified gaps and re-enter the canonical loop;
they are not patched outside the contract.

---

# 13. Acceptance criteria

## Coherence

- [ ] One canonical acceptance loop is referenced by every core workflow skill.
- [ ] Every operational skill declares ownership, inputs, preconditions,
      verification, acceptance, gap routing, writes, recovery, and handoff.
- [ ] Router recommendations resolve to existing skills and modes.
- [ ] All skill-to-skill calls use canonical `-rpm` names.
- [ ] Proposed specifications are distinguishable from implemented behavior.

## Iteration

- [ ] Every iteration selects one scope and one gap.
- [ ] Verification produces durable evidence linked to criteria.
- [ ] A failed check is classified before additional work starts.
- [ ] Gap routing returns to the stage that owns the failure.
- [ ] Repeated unchanged iterations enter `Stalled` and escalate.
- [ ] Every iteration ends with exactly one next action or terminal state.

## Acceptance integrity

- [ ] Behavior, seam, ticket, milestone, and phase acceptance remain distinct.
- [ ] Child acceptance supplies evidence but does not automatically accept its
      parent.
- [ ] Human/PM acceptance authority is explicit where judgment is required.
- [ ] Acceptance criteria changes are authorized and recorded.
- [ ] Completion cannot be claimed while a critical finding or criterion gap
      remains.

## State stability

- [ ] Canonical and mirrored state responsibilities are documented once.
- [ ] Multi-write operations verify postconditions from live state.
- [ ] Partial failures recover or emit explicit drift records.
- [ ] Repeating an accepted operation is idempotent.
- [ ] Reconciliation can report drift without mutation.
- [ ] Applied reconciliation requires explicit confirmation.

## Validation

- [ ] Static validation covers metadata, references, links, modes, labels, and
      scripts.
- [ ] Core loop scenarios run against a fake tracker boundary.
- [ ] Adapter tests cover success, conflict, partial failure, recovery, and
      idempotent retry.
- [ ] CI blocks contract drift.
- [ ] A documented end-to-end fixture reaches acceptance through at least one
      failed iteration and correct reroute.

---

# 14. Definition of success

The complete workflow is coherent when every participant can answer from the
canonical records:

- What scope are we advancing?
- What does acceptance require?
- What evidence exists now?
- Which criterion is still failing?
- What type of gap is it?
- Which skill or human owns that gap?
- What changed in the latest iteration?
- Why is another iteration justified?
- Is this scope accepted, blocked, awaiting a decision, or stopped?
- What is the single next action?

The workflow is stable when an agent can stop at any boundary, another agent can
resume from durable state, partial tracker failures can be reconciled, and a
change to one skill cannot silently invalidate the rest of the workflow graph.
