# PM task issue template

Every executable project task can be a ticket, not only code. Label it `pm:task` plus one `work:*` kind.

## Outcome

<What is true when this ticket is complete. Prefer an externally verifiable result.>

## Why this matters

<Link the task to the phase goal, milestone, decision, or risk it advances.>

## Work kind

<engineering | research | product | design | business | docs | ops | meeting | validation | access | other>

## Acceptance criteria

- [ ] <criterion>
- [ ] <criterion>

## Planning metadata

Priority: <P0 | P1 | P2 | P3>

Sprint: <sprint name/id or backlog>

Milestone: <roadmap milestone or none>

Product phase: <0 | 1 | 2 | 3 | 4>

## Deadline / timing

Due: <date or none>

Timing reason: <hard dependency, event, sprint target, preference, none>

## Effort

Estimate: <1 | 2 | 3 | 5 | 8 story points, or XS/S/M/L when the team does not use points>

Expected shape: <focused task | half-day | day | multi-day; do not pretend estimates are precise>

## Skills needed

Required:
- <skill/domain>

Helpful:
- <skill/domain>

Technical depth: <0-4>
- 0 = non-technical
- 1 = technical literacy
- 2 = practitioner
- 3 = advanced/specialist
- 4 = deep expert/judgment-heavy

## What to know before starting

The claimer should be able to check these honestly before beginning:

- [ ] I understand the user/business context this task serves.
- [ ] I understand the key terms listed below.
- [ ] I have read the referenced docs/research.
- [ ] I know the decision or acceptance criteria I am responsible for.
- [ ] I have the required access/tools/data.

Key terms/concepts:
- <e.g. Docker containers vs images; OAuth; target segment; pricing model>

Read first:
- <doc/research/link>

## Prerequisite research

<None, or link to a research task that blocks this ticket.>

If the claimer cannot explain a required concept well enough to participate, propose a focused research ticket first. Research should answer the specific knowledge gap, not become an open-ended course.

## Blocked by

- <ticket(s) or none>

## Collaboration mode

<AFK agent | HITL | human-only | pair/group>

## Claiming

A teammate claims this ticket by becoming its assignee. Before claiming, check that:

- blockers are closed,
- the deadline is feasible relative to the estimate,
- required skill/technical depth is a reasonable match,
- prerequisites/read-first material are satisfied or explicitly accepted as first work,
- no other assignee already owns it.

## Notes for grilling / decision work

If this task will use `grill-with-docs-rpm`, do not start the grill until the claimer passes the "What to know before starting" checklist. If not ready, create/complete prerequisite research first.


## GitHub adapter note

When GitHub is the configured tracker, keep this issue body as the complete work contract and mirror only sortable/indexable metadata into the configured GitHub Project. Assignment is the authoritative claim. Use native parent/blocking relationships rather than copying dependency truth into comments.
