# Canonical Acceptance Loop

This file is the operational contract for every skill that advances work. The
long-form rationale and migration plan remain in
[`WORKFLOW-COHERENCE-SPEC.md`](WORKFLOW-COHERENCE-SPEC.md); this file is the
implemented source of truth.

## Vocabulary

- **Scope:** exactly one behavior slice, ticket, milestone, or product phase.
- **Acceptance contract:** scope identity, owner, criteria, verification method,
  required evidence, acceptance authority, and boundaries.
- **Evidence:** an inspectable result tied to a criterion. Record its location,
  validation time, and whether it proves, supports, contradicts, or does not
  address that criterion.
- **Gap:** the difference between current evidence and the acceptance contract.
- **Acceptance:** the explicit verdict reached only after every criterion has
  current evidence, required verification passes, critical findings are closed,
  state mirrors agree, and the named human authority confirms when required.

Canonical gap types are `behavior`, `test`, `specification`, `design`,
`knowledge`, `decision`, `dependency`, `quality`, `evidence`, `state-drift`, and
`scope`. Use `runnable-uncertainty` when executable evidence is the smallest way
to resolve a design question.

## Loop

Every iteration must execute these steps in order:

1. **Observe** live canonical state, the acceptance contract, prior iteration,
   current evidence, and unresolved findings.
2. **Select** exactly one scope and the smallest useful gap. Name its owner, the
   intended evidence, and the expected state change.
3. **Execute** only the selected change through the owning specialist or human.
4. **Verify** with the method named in the contract and retain inspectable
   evidence.
5. **Evaluate** the complete evidence set. Emit exactly one verdict: `Accepted`,
   `Not accepted`, `Blocked`, `Needs decision`, or `Stopped`.
6. **Classify and route** every failed criterion before more work begins. Select
   one next gap using the routing matrix below.
7. **Record** accepted evidence and synchronize mirrors without promoting a
   parent scope automatically.
8. **Hand off** with exactly one next action or a terminal state.

The next iteration must change implementation, verification, authorized
contract, design, evidence, or dependency state. After two consecutive
iterations with the same gap and no material evidence change, emit `Stalled`
and route to specification clarification, design reconsideration, research or a
prototype, an explicit scope split, or the named human authority.

## Gap routing

| Gap | Owner | Return condition |
| --- | --- | --- |
| `knowledge` | `research-rpm` | Cited evidence answers the exact question |
| `decision` | `wayfinder-rpm` or `grill-with-docs-rpm` | Authorized decision is recorded |
| `specification` | `grilling-rpm` or `to-spec-rpm` | Acceptance contract is unambiguous |
| `design` | `codebase-design-rpm` | Seam/design decision is recorded |
| `runnable-uncertainty` | `prototype-rpm` | Prototype records a verdict |
| `behavior` | `tdd-rpm` through `implement-rpm` | Behavior slice completes red-green-refactor |
| `test` | `tdd-rpm` | Verification is sensitive, deterministic, and green |
| `dependency` | `project-management-rpm` or `wizard-rpm` | Dependency is resolved or explicitly accepted |
| `quality` | local refactor, `code-review-rpm`, or follow-up ticket | Applicable standard is satisfied |
| `evidence` | owning execution skill | Fresh evidence is attached |
| `state-drift` | tracker reconciliation | Canonical state and mirrors agree |
| `scope` | PM/spec authority | Scope is included, deferred, split, or rejected |

Resolve upstream gaps before downstream ones:

`knowledge/decision -> specification -> design -> behavior/test -> quality -> evidence/state`

## Acceptance levels

- **Behavior:** `tdd-rpm` observed the expected red, reached minimum green, kept
  justified local refactoring green, and added no hidden behavior.
- **Seam:** `implement-rpm` has accepted child behavior slices, focused tests,
  typecheck, spec consistency, and a seam commit.
- **Ticket:** all criteria have evidence, relevant verification passes, both
  review axes have no blocking finding, artifacts are linked, and tracker state
  agrees.
- **Milestone:** its outcome is demonstrated independently of child ticket
  counts.
- **Product phase:** exit evidence supports an outcome verdict and the PM
  explicitly chooses advance, extend, pivot, pause, or stop.

Child acceptance is evidence for its parent; it never accepts the parent.

## Operational skill contract

An operational skill must provide, directly or by this shared contract:

1. **Owns** — decisions and state controlled by the skill.
2. **Inputs** — required identifiers and artifacts.
3. **Preconditions** — live checks before work or mutation.
4. **Process** — the Observe-to-Hand-off loop specialized to its scope.
5. **Verification** — commands, observations, or human checks.
6. **Acceptance** — exact terminal conditions at the owned level.
7. **Gap routing** — a pointer to this matrix plus any specialization.
8. **Writes** — canonical and mirrored state touched.
9. **Recovery** — reconciliation after partial failure.
10. **Handoff** — exactly one normal next route.

Skills accept only the scope they own and return evidence and a verdict to their
parent. Routers are indexes: they read the routed skill before making a
load-bearing claim and do not duplicate its implementation.

## Mutation protocol

For every multi-write operation:

1. re-read live state;
2. calculate intended and recovery patches;
3. write canonical state first unless safety requires a different order;
4. write mirrors;
5. re-read and verify invariants;
6. apply recovery when verification fails;
7. emit an explicit drift record if recovery cannot restore consistency.

Return an operation id, before snapshot, completed writes, verification results,
recovery writes, final verdict, and unresolved drift. Rerunning an accepted
operation must leave state unchanged and return the same semantic result.

## Iteration record

Use this durable record at ticket level and above:

```markdown
## Acceptance iteration <n>

- Scope: <stable identity and link>
- Gap addressed: <canonical type + summary>
- Change: <artifact, commit, or decision link>
- Verification: <check + result link or compact summary>
- Criteria affected: <criterion ids>
- Verdict: Accepted | Not accepted | Blocked | Needs decision | Stopped
- Remaining gaps: <ids or None>
- Next action: <exactly one route and owner>
```

Do not paste large logs into canonical work records. Link the artifact and keep
only the diagnostic excerpt needed to understand the verdict.
