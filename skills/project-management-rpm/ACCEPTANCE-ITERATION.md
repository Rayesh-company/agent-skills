# Acceptance iteration template

Append this compact record to the canonical ticket, milestone, or phase record.
Increment the number within that record. Link large logs and artifacts instead
of pasting them.

```markdown
## Acceptance iteration <n>

- Scope: <stable identity and link>
- Gap addressed: <behavior | test | specification | design | knowledge | decision | dependency | quality | evidence | state-drift | scope>
- Change: <artifact, commit, or decision link>
- Verification: <command/check + result link or compact summary>
- Criteria affected: <criterion ids>
- Verdict: Accepted | Not accepted | Blocked | Needs decision | Stopped
- Remaining gaps: <ids or None>
- Next action: <exactly one route and owner>
```

Before starting the next iteration, compare it with the latest record. If the
same gap appears twice without a material evidence change, record `Stalled` and
route upstream or to the named acceptance authority.
