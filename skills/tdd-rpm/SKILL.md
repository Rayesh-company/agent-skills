---
name: tdd-rpm
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
---

# Test-Driven Development

TDD is the red → green → refactor loop. This skill is the reference that makes that loop produce tests worth keeping and implementation changes that remain small, behavior-focused, and maintainable: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle: consult them before and during the loop, not after.

## Acceptance contract

Read [`../../ACCEPTANCE-LOOP.md`](../../ACCEPTANCE-LOOP.md). This skill owns one
behavior or test gap at one agreed seam. Inputs are the criterion id, public
behavior, seam, focused command, and prior evidence. Preserve evidence of the
expected red, minimum green, and green local refactor. A behavior slice is
accepted only under the shared behavior-level rules; return its evidence to
`implement-rpm` without accepting the seam or ticket. Route ambiguous behavior
to `to-spec-rpm`, contested seams to `codebase-design-rpm`, invalid tests back
through another changed TDD iteration, and broader quality work to review.

When exploring the codebase, read `CONTEXT.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in the area you're touching.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification: "user can checkout with valid cart" tells you exactly what capability exists, and it survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams: where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything, so agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

When the shape of that interface is itself in question (how deep the module is, where the seam belongs, what the interface should expose), call the Skill tool with "codebase-design-rpm" for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled**: mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological**: the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth: a known-good literal, a worked example, the spec.
- **Horizontal slicing**: writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead: one test → one implementation → local refactor → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.
- **Refactor-before-green**: restructuring production code while the new behavior is still failing. This mixes behavior changes and structural changes, making failures harder to localize. Get green first.
- **Scope-creep refactor**: using the refactor step to redesign unrelated modules or address broad codebase smells. The refactor step is local to the slice just made green; broader cleanup belongs in review or a separately scoped ticket.

## Rules of the loop

- **Red before green.** Write the failing test first, run it, and confirm it fails for the expected reason. A test that is already green has not demonstrated the missing behavior.
- **Minimum green.** Write only enough implementation to make the current test pass. Don't anticipate future tests or add speculative features.
- **Refactor only while green.** After the test passes, make small behavior-preserving improvements to the code or test if they improve names, duplication, readability, locality, or the shape of the implementation. Re-run the focused tests after each meaningful refactor and keep them green.
- **One slice at a time.** One seam, one behavior/test, one minimal implementation, then any justified local refactor before starting the next behavior.
- **Refactor is not redesign.** The TDD refactor step is deliberately narrow. Do not change requirements, public behavior, agreed seams, or unrelated architecture. If a broader structural problem is discovered, finish the current green cycle and surface it to `code-review-rpm`, `codebase-design-rpm`, or a follow-up ticket.
- **New behavior requires a new red.** If a refactor exposes a missing behavior or suggests a new requirement, stop refactoring and begin another cycle with a failing test.

## Cycle completion

A TDD cycle is complete when:

1. the new test was observed failing for the expected reason,
2. the minimum implementation made it pass,
3. any local refactor was completed with focused tests remaining green, and
4. no new behavior was smuggled in during refactoring.

When this skill is used inside `implement-rpm`, return control after each completed slice/seam so implementation can typecheck, commit at the seam boundary, and continue the broader ticket workflow.

## Relationship to code review

TDD and code review have different responsibilities:

- **TDD refactoring** keeps the code touched by the current behavior slice clean enough to continue safely while the implementation context is fresh.
- **`code-review-rpm`** evaluates the completed diff as a whole against repository standards and the originating spec. It can identify broader smells, cross-seam design problems, and refactors that were intentionally out of scope for the local TDD loop.

Do not defer obvious, safe local cleanup merely because review happens later; equally, do not turn the local TDD refactor step into an unbounded architecture rewrite.
