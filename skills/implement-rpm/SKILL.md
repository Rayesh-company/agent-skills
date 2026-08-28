---
name: implement-rpm
description: "Implement a written, fully-specified ticket or spec end-to-end in the current branch. Use after to-spec-rpm or to-tickets-rpm has produced an actionable artifact and the user says 'implement this', 'build this', 'code this ticket', 'do the work', or hands over a numbered issue with acceptance criteria. Do not use for reviewing existing implementation, explaining code, drafting specs, planning, or writing tests in isolation — those are code-review-rpm, codebase-design-rpm, to-spec-rpm, wayfinder-rpm, and tdd-rpm respectively."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets. This skill is the execution stage of the RD pipeline — it assumes the upstream artifacts (seam map, acceptance criteria, branch) already exist.

## Acceptance contract

Read [`../../ACCEPTANCE-LOOP.md`](../../ACCEPTANCE-LOOP.md). This skill owns
behavior slices and seam-level integration on one ticket; it does not accept the
ticket, milestone, or phase. Inputs are the live branch, one actionable ticket,
agreed seams, criterion ids, verification commands, and prior iteration. Select
one gap per iteration, retain red/green/typecheck evidence, and record why the
next iteration changes evidence or method. A seam is accepted only under the
shared level rules. Restore a green working state after a failed partial change
or return an explicit gap. Hand off exactly once to `code-review-rpm`, an
upstream owner, a blocker, or the next behavior slice.

## Preconditions

Before starting, confirm all of the following. If any is missing, stop and hand back to the producing skill rather than improvising.

- **Seam map agreed.** A prepare pass from `/project-management-rpm` (or `/to-tickets-rpm`) has produced seams — concrete points where code crosses a boundary (module, function, contract). The seams name what changes and what stays fixed. If seams are missing or contested, escalate to `/grilling-rpm` before writing code.
- **Spec is actionable.** The spec or ticket has acceptance criteria that are testable, not aspirational. "Improve error handling" is not actionable; "replace generic `Error` with `DomainError` and add 3 unit tests covering empty input, malformed input, and timeout" is.
- **Branch prepped.** A working branch exists, is checked out, and has a clean working tree. Do not start implementation on `main` or with uncommitted changes from a prior task.

## Process

Work through these steps in order. Do not skip cadence — the loops below are what catch mistakes before they compound.

1. **Establish the loop.** For each seam in the seam map, delegate the inner cycle to `/tdd-rpm` and complete one behavior slice at a time: write the failing test at the seam and confirm red, write the minimum code to make it green, then perform any justified **local behavior-preserving refactor while staying green**. Do not batch all tests before any code, do not batch all code before any tests, and do not turn the refactor step into a cross-seam redesign. If the refactor suggests new behavior, begin another red cycle instead of smuggling it into cleanup.
2. **Typecheck after every seam.** Run the project's typechecker (e.g. `tsc --noEmit`, `mypy`, `cargo check`) after the seam's TDD cycles are green and local refactoring is complete. A green test with a broken type is not done. If the typechecker fails, treat it as a seam-level failure and loop back to step 1.
3. **Run single test files regularly.** When iterating on one seam, run only the test files relevant to that seam. Fast feedback keeps the loop tight. Re-run the focused tests after meaningful refactors. Avoid running the full suite during iteration — that comes at step 5.
4. **Commit at seam boundaries.** Each seam that closes green after tests, local refactoring, and types gets its own commit. Small commits are recoverable; a single mega-commit at the end is not. Commit message format follows the project's convention; if none exists, use `seam: <short description>`.
5. **Run the full test suite once at the end.** Only after all seams are closed, run the full suite. The full run catches cross-seam regressions that single-file runs cannot see. If the full suite is red, return to step 1 for the offending seam — do not patch around it.

## Refactoring boundary

Implementation and review both care about code quality, but at different scopes.

- **Inside the TDD loop:** perform small, behavior-preserving cleanup of the code and tests touched by the current slice. Typical examples are better names, removing duplication introduced by the slice, simplifying control flow, or improving locality. Keep focused tests green throughout.
- **Outside the TDD loop:** broader architectural changes, cross-seam restructuring, speculative abstractions, and repository-wide smell cleanup are not part of the local refactor step. Surface those to `/code-review-rpm`, `/codebase-design-rpm`, or a separately scoped ticket.

This boundary prevents two failure modes at once: deferring obvious local cleanup until context is lost, and allowing “refactor” to silently expand implementation scope.

## Failure modes

When one of the following happens, stop the implementation loop and respond as indicated. Do not push through.

- **Test suite red at step 5.** A seam that was green in isolation broke the suite. Return to step 1 for the seam whose tests changed most recently. If multiple seams contributed, pick the seam with the largest surface area and re-verify its neighbors before iterating.
- **Focused test breaks during refactor.** The refactor changed behavior or introduced a defect. Stop refactoring and restore green before continuing. Do not accept a red state as temporary cleanup debt.
- **Typecheck fails.** Stop writing new code. Fix the type error before resuming step 1. Type errors propagate — leaving them in place will mask the next test failure.
- **Commit blocked.** The working tree has changes that cannot be cleanly committed (merge conflict, pre-commit hook failure, dirty files from a prior task). Resolve before continuing. Do not `git commit --no-verify` to bypass hooks.
- **Seam disagreement mid-implementation.** What the seam map says and what the code requires diverge — the seam was wrong. Stop, surface the disagreement to the user with both readings, and hand off to `/grilling-rpm` to resolve. Do not silently redefine the seam.
- **Refactor reveals broader design work.** Finish or restore the current seam to green, record the design concern, and route it to `/code-review-rpm`, `/codebase-design-rpm`, or a follow-up ticket rather than expanding the implementation task implicitly.

## Post-conditions

Implementation is complete when all of the following are observable in the working tree.

- **Committed on branch.** Every seam from the seam map has at least one commit on the working branch. `git log <base-branch>..HEAD` shows the seam commits; `git status` is clean.
- **Acceptance criteria met.** Each acceptance criterion from the spec or ticket is covered by a passing test or an observable artifact. Cite the test name or file when claiming coverage so the next stage can verify.
- **Local refactors remained green.** Behavior-preserving cleanup performed during implementation was verified with focused tests before each seam closed.
- **Full suite green.** The full test suite ran at step 5 and passed. The branch is ready for review.

## Composition

This skill is the middle of a pipeline. Hand off as follows.

- **Use `/tdd-rpm` as the canonical inner implementation loop.** Its red → green → local refactor rules define how each behavior slice is completed; `implement-rpm` adds seam sequencing, typechecks, commits, full-suite verification, and ticket-level completion.
- **After post-conditions are met, invoke `/code-review-rpm`** on the branch against the spec. Do not skip this step even if the work feels obvious. Review evaluates the completed diff as a whole, including broader code smells and structural opportunities intentionally kept out of the local TDD refactor step.
- **If the spec is ambiguous, contradictory, or missing acceptance criteria mid-implementation, invoke `/grilling-rpm`** to resolve before writing more code. Ambiguity caught early costs minutes; ambiguity caught after three seams costs hours.
- **If a discovered defect points to a gap in the seam map (not just the code), route back to `/to-tickets-rpm`** to add the missing ticket rather than expanding scope inside implementation.
