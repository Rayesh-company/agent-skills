---
name: ask-matt-rpm
description: Route a user through the combined product/project-management workflow and Matt Pocock engineering skills. Explain what to run next, why, and where PM work hands off to specialist engineering skills.
disable-model-invocation: true
argument-hint: Describe where you are in the project or what you are trying to do.
---

# Ask Matt

Use this as the human-facing router for the combined PR-skill + Matt Pocock workflow.

The user should not need to memorize product phases, PM modes, Wayfinder, Scrum conventions, or the engineering skill graph. They describe their situation; this skill tells them **where they are, what to type next, what that command will do, and what the likely handoff after it is**.

This skill orients. It does not perform the routed work itself.

Read [`../../ACCEPTANCE-LOOP.md`](../../ACCEPTANCE-LOOP.md) for canonical gap
routing and acceptance levels. Use it as the route index; read the selected
operational skill before naming its preconditions, writes, acceptance, recovery,
or handoff. Return exactly one next command or terminal/blocking state.

## Router discipline

Before making a load-bearing claim about another skill, read that installed skill's `SKILL.md`.

At minimum:

- for any PM/product route, read `../project-management-rpm/SKILL.md`;
- for first-time setup, also read `../setup-pr-skills-rpm/SKILL.md`;
- for a Matt engineering route, read the `SKILL.md` for every skill whose behavior determines the recommendation;
- if a named skill is not installed or cannot be read, say so instead of inventing its behavior.

The routed skill is the source of truth. This router is only the map.

When a user asks a broad question such as "what should we do next?", first inspect the repo/tracker state available to you so the answer is anchored in the active project rather than in keywords alone.

## First distinction: which layer owns the question?

There are two cooperating layers.

### Product/project-management layer

Use `project-management-rpm` when the question is about:

- current product-development phase;
- phase goal or exit criteria;
- uncertainty that blocks a credible roadmap;
- roadmap or milestone sequencing;
- mixed-discipline backlog work;
- Scrum sprint planning/review;
- finding claimable work;
- prerequisite/readiness checks;
- recording task completion into sprint/phase state;
- deciding whether to advance, extend, pivot, pause, or stop a product phase.

The PM layer owns **why this work exists, where it sits in the product lifecycle, when it matters, and how it contributes to the current phase goal**.

### Matt engineering layer

Use Matt's specialist skills when the question is about **how to discover, specify, implement, debug, review, or improve a particular piece of engineering work**.

The two layers intentionally overlap at handoff points. Do not create duplicate work items just because both layers care about the same work.

## Important vocabulary: two different meanings of phase

Never conflate these.

- **Product phase** means Phase 0 Research & Business Planning, Phase 1 Demo, Phase 2 MVP, Phase 3 V1, or Phase 4 Full Product. `project-management-rpm` owns these.
- **Context boundary** means a boundary between chunks of an AI working session, where the user may continue, clear, hand off, use a subagent, or compact. Matt's context-management guidance owns this.

If the user says "phase" and the meaning is ambiguous, infer it from the surrounding task when possible; otherwise ask only if the distinction changes the route.

# Combined product flow

This is the default route for a new product or a product being actively managed through the PM layer.

## 0. First use in a repository

If Matt's tracker/domain setup or PM setup is missing, route to:

`/setup-pr-skills-rpm`

That command composes the original Matt setup with PM initialization. Do not tell the user to run both setup commands manually unless `setup-pr-skills-rpm` is unavailable.

Expected result:

- issue-tracker/domain conventions exist;
- when GitHub is configured, PM labels and the GitHub adapter config exist, with a Projects v2 board/fields when the token has `project` scope;
- one current product phase is confirmed by the PM;
- one phase goal and exit gate exist;
- a canonical `pm:project` record exists;
- an active `pm:phase` record exists;
- the user is pointed toward initial uncertainty mapping when needed.

## 1. Establish or inspect direction

Use:

`/project-management-rpm status`

when the user wants to know where the project stands.

Use:

`/project-management-rpm init`

when base Matt setup already exists but PM lifecycle state has not been initialized.

The PM should confirm the product phase. Do not infer phase only from how much code exists.

## 2. The goal is known but the route is foggy

Use:

`/project-management-rpm wayfind`

This is the PM-aware entry into Wayfinder. The destination is not "finish the whole phase". The destination is to resolve enough important uncertainty that a credible roadmap can be made.

The underlying Wayfinder map remains a Wayfinder artifact. Research, prototype, grilling, and decision tickets created inside it are not automatically duplicated as PM tasks.

When an individual Wayfinder ticket needs specialist work, route according to its kind:

- knowledge/evidence gap -> `/research-rpm`;
- decision that needs human pressure-testing -> readiness check if needed, then `/grill-with-docs-rpm`;
- runnable design question -> `/prototype-rpm`;
- fuzzy domain language -> `/domain-modeling-rpm`;
- human-only external setup -> `/wizard-rpm` when that installed skill fits.

## 3. The route is clear enough to sequence

Use:

`/project-management-rpm roadmap`

This turns the active phase goal plus resolved Wayfinder decisions into milestones and a mixed-discipline backlog.

Do not send all roadmap work through `to-tickets-rpm`. PM-native work can include research, product, design, business, documentation, operations, meetings, validation, procurement/access, and coherent small engineering tasks.

For engineering work that is large enough to need implementation slicing, hand off to Matt's engineering flow. The resulting engineering tickets are enrolled in the PM backlog directly; do not create wrapper PM duplicates.

## 4. Refine or reprioritize work

Use:

`/project-management-rpm backlog`

when outcomes, acceptance criteria, blockers, estimates, skills, technical depth, prerequisites, or priority need refinement before work is ready.

## 5. Plan or review a sprint

Use:

`/project-management-rpm sprint`

The sprint is organized around one sprint goal that advances the current product-phase goal. Leave suitable work unassigned so teammates can claim it instead of pre-assigning the entire sprint.

## 6. A teammate wants work

Use:

`/project-management-rpm claim`

The PM layer should choose from ready, unblocked, unassigned work using deadline feasibility, sprint/phase value, skills, technical depth, prerequisites, and effort. On GitHub, assignment is the authoritative claim and the PM adapter keeps the workflow label/Project status synchronized.

If a user says "give me something to do", "what can I pick up?", or "what should I work on next?", prefer this route when a PM-managed backlog exists.

## 7. A teammate has claimed work

Use:

`/project-management-rpm prepare <ticket>`

when the work is decision-heavy, unfamiliar, technically deep, has explicit prerequisites, or is about to enter a grilling session.

This is a readiness gate, not a generic study assignment. It should identify what the claimer must understand for this specific issue.

If a material knowledge gap exists, route to focused research before the original task. Example: a teammate should understand images, containers, registries, volumes, and the project's deployment constraints before defending a container deployment decision.

When the person is ready, route by work kind:

- research -> `/research-rpm`;
- decision/grilling -> `/grill-with-docs-rpm`;
- prototype -> `/prototype-rpm`;
- engineering build -> the engineering build flow below;
- non-code execution -> execute against the issue's acceptance criteria.

## 8. Work is complete

Use:

`/project-management-rpm done <ticket>`

for PM-managed tasks and enrolled engineering tickets so completion evidence updates blockers, sprint state, and product-phase exit evidence.

Closing a GitHub issue is not automatically proof that the product-phase goal was achieved.

## 9. Review the product phase

Use:

`/project-management-rpm phase-review`

The PM chooses among:

- advance;
- extend;
- pivot;
- pause;
- stop.

If advancing, set the next product-phase goal before automatically carrying the old roadmap forward. Re-wayfind if the new phase introduces meaningful uncertainty.

# GitHub PM adapter route

When the user asks how PM work maps to GitHub, verify `project-management/GITHUB-ADAPTER.md` and `docs/agents/github-pm.json` before answering.

- GitHub setup missing -> `/setup-pr-skills-rpm`.
- Labels/issues work but no Project board -> explain Issues-only mode; the human can grant `project` scope and rerun setup.
- Existing engineering/Wayfinder issue needs PM planning metadata -> enroll the same issue; do not create a wrapper duplicate.
- User wants to claim work -> `/project-management-rpm claim`; accepted claims become GitHub assignments.
- User wants to change delivery state -> project-management owns the transition and the adapter keeps `pm:*` labels plus `PM Status` aligned.
- User asks about GitHub board fields -> use Product Phase, Sprint, Effort, Deadline, Technical Depth, Work Type, Priority, and PM Status from the adapter contract.

Do not claim that setup creates custom GitHub Project views/layouts. The adapter creates project/fields/items; users can group a board view by `PM Status` in the GitHub UI.

# Phase 0 route

Phase 0 is Research & Business Planning.

The end state is not merely "we researched the idea". The phase must produce enough evidence for a decision and the required proposal in both English and Farsi.

Typical route:

`/setup-pr-skills-rpm`

-> confirm Phase 0 + goal

-> `/project-management-rpm wayfind`

-> research / interviews / prototypes / grilling / domain decisions as needed

-> `/project-management-rpm roadmap`

-> `/project-management-rpm sprint`

-> claim / prepare / execute / done

-> produce and review the bilingual proposal

-> `/project-management-rpm phase-review`

If the user tries to jump from a raw idea straight to a large implementation backlog, point out the unresolved Phase 0 uncertainty and route to the PM-aware Wayfinder unless the PM explicitly chooses to bypass it.

# Engineering build flow inside the PM system

Once a PM/Wayfinder decision has produced a sufficiently concrete engineering item, Matt's original engineering workflow owns implementation detail.

Verify the relevant installed skills before choosing the branch.

## Idea or feature needs sharpening

Use `/grill-with-docs-rpm` when the feature/design can be meaningfully clarified in a working directory through conversation and project documentation.

If one important question cannot be settled on paper and needs runnable evidence, take a `/prototype-rpm` detour and bring the learning back into the main thread using the installed handoff/context conventions.

## Small, concrete build

When the work is genuinely small enough for one working session and does not need a durable multi-ticket plan, route to `/implement-rpm` if its current `SKILL.md` supports that route.

## Multi-session engineering build

For a substantial but already-understood build, the normal route is:

`/to-spec-rpm`

-> `/to-tickets-rpm`

-> `/implement-rpm` per ready ticket

-> implementation's review path / `/code-review-rpm` as documented by the installed skill.

Under PM management, add the resulting issues to the current milestone/sprint/backlog rather than recreating them as `pm:task` wrappers.

After an enrolled ticket is finished, return upward with:

`/project-management-rpm done <ticket>`

so product/sprint state sees the result. On GitHub this uses the adapter to post evidence, set `pm:done`/`PM Status=Done`, and close only if the issue is still open.

## Huge or genuinely foggy engineering effort

If the destination is understood but the path itself cannot fit coherently in one session, use Wayfinder. Inside a managed product, prefer:

`/project-management-rpm wayfind`

because it preserves the phase goal and PM handoff. Use `/wayfinder-rpm` directly when the effort is intentionally outside PM lifecycle management.

# Other Matt on-ramps

These routes remain available and are not replaced by PM.

## Incoming bug reports or feature requests

Use `/triage-rpm` for work that arrived raw from other people and needs to become agent-ready.

Do not triage tickets that were already deliberately created by `to-tickets-rpm` or PM backlog refinement unless the current `triage-rpm` skill explicitly documents such a use.

Once an incoming issue becomes ready and belongs to the active product, it can be enrolled in the PM backlog.

## Something is broken

Use `/diagnosing-bugs-rpm` for a difficult bug, intermittent failure, or regression that needs systematic reproduction and diagnosis.

If the bug becomes normal implementation work afterward, merge back into the appropriate engineering/PM flow.

## Codebase health

Use `/improve-codebase-architecture-rpm` for architecture-health/deepening work rather than pretending it is a product feature.

If the selected improvement becomes planned product work, connect it to the relevant PM milestone/task instead of duplicating the issue.

# Vocabulary and supporting skills

These are not product phases or Scrum states. Route to them when their specific problem appears.

- `/domain-modeling-rpm` — domain terms are fuzzy, overloaded, or causing design confusion.
- `/codebase-design-rpm` — the problem is the shape/seam/interface of a code module rather than the product roadmap.
- `/tdd-rpm` — a concrete behavior should be built test-first without needing the whole PM/spec flow.
- `/code-review-rpm` — review an existing diff/branch/PR against the skill's current review contract.
- `/research-rpm` — gather evidence from primary/high-trust sources and leave the research artifact expected by the installed skill.
- `/to-questionnaire-rpm` — the missing information lives with another human/stakeholder and should be collected asynchronously.
- `/wizard-rpm` — the work requires human-only dashboard/credential/infrastructure steps.
- `/resolving-merge-conflicts-rpm` — already in an active merge/rebase conflict.
- `/wait-what-rpm` — the explanation that just happened did not land; re-explain rather than changing workflows.
- `/teach-rpm` — the user wants to learn a concept over multiple sessions, rather than merely become ready for one ticket.

Read the named skill before promising any specific behavior.

# Context boundaries are separate from product phases

When the user asks whether to clear, compact, hand off, continue, or split work into another agent/session, follow Matt's installed context-boundary guidance.

Do not use a product phase transition to solve a context-window problem, and do not use `/compact` or `/handoff-rpm` as a substitute for `/project-management-rpm phase-review`.

A useful rule of thumb:

- product phase changed because the **product has reached or changed an outcome**;
- context changed because the **working session needs a different memory/ownership boundary**.

# Common situations

Consolidated routing reference. Each row picks a default command for the user's situation. Caveats and the ordered walkthrough live in the Combined product flow section above; verify against the relevant skill files before running anything.

| User situation | Default next command |
| --- | --- |
| Brand-new product/repo | `/setup-pr-skills-rpm` |
| Setup exists but product phase/goal is missing | `/project-management-rpm init` |
| "Where are we?" | `/project-management-rpm status` |
| Phase goal is known but route is uncertain | `/project-management-rpm wayfind` |
| Enough decisions are resolved to plan delivery | `/project-management-rpm roadmap` |
| Backlog items are vague/not ready | `/project-management-rpm backlog` |
| Need to choose this sprint | `/project-management-rpm sprint` |
| Teammate asks what they can work on | `/project-management-rpm claim` |
| Claimed ticket requires unfamiliar knowledge | `/project-management-rpm prepare <ticket>` |
| Need evidence/reading | `/research-rpm` or a research ticket, depending on ownership |
| Need a hard human decision discussion | `prepare` if needed -> `/grill-with-docs-rpm` |
| Need runnable evidence for a design choice | `/prototype-rpm` |
| Engineering feature is understood but multi-session | `/to-spec-rpm` -> `/to-tickets-rpm` -> `/implement-rpm` |
| Engineering task is small and concrete | `/implement-rpm`, if current skill contract fits |
| Work is completed and PM-managed | `/project-management-rpm done <ticket>` |
| Sprint/phase outcome needs review | `/project-management-rpm sprint` or `phase-review` |
| Product phase may be over | `/project-management-rpm phase-review` |
| Raw incoming issues | `/triage-rpm` |
| Hard bug/regression | `/diagnosing-bugs-rpm` |
| Need help understanding the workflow | `/ask-matt-rpm` |

# How to answer the user

Keep the response short enough to act on. Prefer this shape:

**You are here:** one sentence describing the current state.

**Run next:** the exact slash command.

**Why:** one or two sentences explaining the routing decision and, when useful, why the nearest alternative is wrong.

**Likely handoff:** the next command after this one if the current step succeeds.

When the user asks for a broader explanation, show the relevant slice of the workflow, not every skill in the repository.

If the user already knows exactly which skill they want and is not asking for comparison/orientation, tell them to invoke it directly; do not insert `/ask-matt-rpm` as ceremony.

# Source-of-truth rule

This router must evolve whenever a user-reachable PM or Matt skill is added, renamed, removed, or changes where it sits in the flow.

When this router disagrees with another skill's `SKILL.md`, the other skill wins. Update this router afterward.
