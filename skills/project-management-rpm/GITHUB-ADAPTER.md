# GitHub PM Adapter

Use this adapter when `docs/agents/issue-tracker.md` identifies GitHub as the configured issue tracker.

The adapter keeps GitHub **Issues** as the durable work records and optionally adds a GitHub **Project (Projects v2)** as the structured planning/indexing surface. The issue body remains the complete human-readable contract; Project fields are query/sort/group metadata, not a replacement for the issue.

## Source-of-truth split

- GitHub Issue body: outcome, why it matters, acceptance criteria, prerequisites, skills, technical context, evidence.
- GitHub Issue relationships: parent/sub-issue and blocking/blocked-by dependencies.
- GitHub assignee: authoritative claim/owner for active work.
- GitHub labels: portable PM identity, phase, work kind, and workflow state.
- GitHub Project fields: structured phase/sprint/effort/deadline/technical-depth/work-type/priority/status metadata.
- `docs/agents/github-pm.json`: machine-readable adapter configuration. Do not hand-edit project numbers unless the GitHub Project was intentionally migrated/recreated.

Never create a PM wrapper issue around an existing `to-tickets-rpm` or Wayfinder issue merely to put it on the board. Enroll the existing issue.

## Requirements

- `gh` must be installed and authenticated for issue operations.
- GitHub Project operations require the `project` token scope. Check with `gh auth status`; if needed the human can run `gh auth refresh -s project`.
- If Projects access is unavailable, continue in **Issues-only mode**. Labels, assignment, issue relationships, task creation, and closing still work. Do not block PM setup solely because the Project board cannot be created.

The current GitHub CLI supports native issue assignment, parent/sub-issue relationships, and blocking relationships through `gh issue edit`. Prefer those native relationships over duplicating dependency lists in comments.

## Bootstrap

Run the bundled adapter from the repository root:

```bash
python3 <skill-dir>/github_adapter.py bootstrap
```

Optional overrides:

```bash
python3 <skill-dir>/github_adapter.py bootstrap \
  --repo OWNER/REPO \
  --project-owner OWNER_OR_ORG \
  --project-title "Product Delivery"
```

Bootstrap is idempotent. It:

1. detects the repository and GitHub authentication,
2. creates/updates canonical PM labels,
3. tries to create or reuse one GitHub Project,
4. creates missing PM Project fields,
5. writes `docs/agents/github-pm.json`.

When Projects access is unavailable it writes a config with `projects_enabled: false`. After the human grants `project` scope, rerun bootstrap to upgrade the repo to full Projects mode.

## Canonical labels

Structure:

- `pm:project`
- `pm:phase`
- `pm:task`
- `pm:milestone`

Workflow:

- `pm:backlog`
- `pm:ready`
- `pm:claimed`
- `pm:blocked`
- `pm:in-progress`
- `pm:review`
- `pm:done`

Work kind:

- `work:engineering`
- `work:research`
- `work:product`
- `work:design`
- `work:business`
- `work:docs`
- `work:ops`
- `work:meeting`
- `work:validation`
- `work:access`
- `work:other`

Phase:

- `phase:0`
- `phase:1`
- `phase:2`
- `phase:3`
- `phase:4`

## Canonical GitHub Project fields

The adapter creates these custom fields when full Projects access is available:

| Field | Type | Values / meaning |
|---|---|---|
| `PM Status` | single select | Backlog, Ready, Claimed, In Progress, Blocked, Review, Done |
| `Product Phase` | single select | Phase 0, Phase 1, Phase 2, Phase 3, Phase 4 |
| `Sprint` | text | sprint name/id chosen by PM |
| `Effort` | number | story points or configured numeric convention |
| `Deadline` | date | task deadline |
| `Technical Depth` | number | 0–4 |
| `Work Type` | single select | Engineering, Research, Product, Design, Business, Docs, Ops, Meeting, Validation, Access, Other |
| `Priority` | single select | P0, P1, P2, P3 |

Do not assume GitHub's built-in `Status` field has the PM workflow options. `PM Status` is intentionally separate and owned by this adapter.

The adapter does not create Project views/layouts because the current `gh project` CLI exposes project/field/item CRUD but not a stable `view-create` command. A human may group a board view by `PM Status` without changing the workflow contract.

## Create a managed issue

Use the skill's Markdown templates to prepare the body, then publish through the adapter:

```bash
python3 <skill-dir>/github_adapter.py issue-create \
  --kind task \
  --title "Interview 5 restaurant operators" \
  --body-file /tmp/task.md \
  --phase 0 \
  --status Ready \
  --work-type Research \
  --effort 3 \
  --deadline 2026-08-28 \
  --technical-depth 1 \
  --priority P1 \
  --sprint "Sprint 1"
```

For project and phase records use `--kind project` or `--kind phase`. A phase issue should normally also use `--parent <project-issue-number>`.

## Enroll an existing issue

Use this for Wayfinder work that should be visible in execution planning and especially for engineering issues produced by `to-tickets-rpm`:

```bash
python3 <skill-dir>/github_adapter.py enroll 82 \
  --phase 2 \
  --status Ready \
  --work-type Engineering \
  --effort 5 \
  --deadline 2026-09-04 \
  --technical-depth 3 \
  --priority P1 \
  --sprint "Sprint 4"
```

Enrolling adds missing PM metadata to the same issue. It does not replace the original issue body or create a duplicate.

## Relationships

Set parent and blockers using native GitHub relationships:

```bash
python3 <skill-dir>/github_adapter.py relate 82 --parent 12 --blocked-by 71 72
```

The adapter delegates to the current `gh issue edit --parent` / `--add-blocked-by` interface.

## Claim

After `project-management claim` recommends an issue and the teammate accepts:

```bash
python3 <skill-dir>/github_adapter.py claim 82 --assignee @me
```

Claim behavior:

1. re-reads the live issue,
2. refuses a closed issue,
3. refuses an issue already assigned to somebody else,
4. assigns the selected teammate,
5. transitions `pm:ready` -> `pm:claimed`,
6. sets `PM Status=Claimed` when Projects is enabled,
7. re-reads assignment and warns if concurrent assignment produced multiple owners.

Do not treat a comment such as "I'm taking this" as a claim. Assignment is authoritative.

## Workflow transitions

```bash
python3 <skill-dir>/github_adapter.py state 82 "In Progress"
python3 <skill-dir>/github_adapter.py state 82 Blocked
python3 <skill-dir>/github_adapter.py state 82 Review
```

The adapter keeps the workflow label and `PM Status` field aligned.

## Complete work

```bash
python3 <skill-dir>/github_adapter.py done 82 \
  --comment "Acceptance criteria verified. Evidence: <link>."
```

The adapter posts completion evidence **before** closing. This matters because an issue may already have been auto-closed by a commit/PR; a close command with an attached comment can otherwise skip the explanation on an already-closed issue.

Then it applies `pm:done`, sets `PM Status=Done` when available, and closes only if still open.

## Roadmap milestones

Roadmap milestones may use native GitHub Milestones. Ensure/reuse one with:

```bash
python3 <skill-dir>/github_adapter.py milestone-ensure \
  --title "Customer Evidence" \
  --description "Evidence needed to satisfy Phase 0 customer-validation criteria" \
  --due 2026-08-31
```

Then pass `--milestone "Customer Evidence"` to `issue-create`, or use normal `gh issue edit --milestone` for an existing issue.

## Read/query conventions

Prefer structured reads, for example:

```bash
gh issue view 82 --json number,title,state,body,labels,assignees,milestone,comments,url
```

For a list view, fetch slim metadata first and only fetch full bodies for candidate tasks. Avoid loading every issue body/comment into context when the PM only needs a status list.

For Projects metadata:

```bash
gh project item-list <number> --owner <owner> --format json --limit 200
```

Use `docs/agents/github-pm.json` to find the configured project number/owner instead of guessing.

## Failure behavior

- `gh` missing/not authenticated -> stop GitHub writes and tell the human what prerequisite is missing.
- issues available but Projects scope missing -> continue Issues-only and record the limitation.
- existing field has an incompatible type -> do not destroy it; warn and keep issue-body/label metadata canonical until the PM resolves the field conflict.
- issue already assigned -> do not steal/reassign it silently.
- duplicate project title -> prefer the project number already stored in config; otherwise surface ambiguity instead of guessing.
- repository transfer/project migration -> rerun bootstrap and deliberately update the adapter config.
