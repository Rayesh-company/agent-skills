---
name: setup-pr-skills-rpm
description: Set up Matt Pocock's engineering skill configuration, then initialize the product/project-management layer by selecting the current product phase and phase goal. Run once per repo before using project-management.
disable-model-invocation: true
---

# Setup PR Skills

This is the one-time entry point for a repo using the PR product/project-management workflow.

## Goal

Finish with both layers configured:

1. Matt Pocock engineering prerequisites: issue tracker, triage vocabulary when applicable, and domain-doc layout.
2. Product/project-management state: current phase, phase goal, phase exit criteria, target date, canonical project issue, and active phase issue.
3. When GitHub is the tracker: canonical PM labels plus an optional GitHub Project v2 with structured PM fields, configured through the bundled GitHub adapter.

Do not duplicate Matt's setup logic here. Compose it.

## Process

### 1. Detect Matt setup

Check for `docs/agents/issue-tracker.md` and `docs/agents/domain.md`.

- If either is missing, call the Skill tool for `setup-matt-pocock-skills` and let that workflow complete.
- If both exist, briefly summarize the configured tracker and domain-doc layout and continue.

If the configured tracker cannot represent issues, record that limitation and use its documented local equivalent. Do not silently switch trackers.

### 2. Bootstrap the GitHub adapter when applicable

Read `docs/agents/issue-tracker.md`. If the configured tracker is GitHub:

1. read `../project-management-rpm/GITHUB-ADAPTER.md`,
2. **resolve the target repository** by running `gh repo view --json nameWithOwner --jq .nameWithOwner` from the repository root, or honoring an explicit `--repo OWNER/REPO` passed on the skill invocation; if the resolve call fails or the resolved repo differs from the value already stored in `docs/agents/github-pm.json` (when that file exists), surface the discrepancy and ask the human which repo to target before proceeding,
3. **enumerate what bootstrap will write** on that exact remote — do not hardcode a label count; compute it live:
   - `LABELS` in `project-management-rpm/github_adapter.py` defines the canonical set; intersect it with `gh label list --repo OWNER/REPO --json name --jq '.[].name'` to obtain `N_NEW` (missing) and `M_EXISTING` (present, will be force-updated),
   - check whether a GitHub Project with the configured `project_title` already exists for the resolved owner via `gh project list --owner OWNER --limit 100 --format json`,
   - check whether the current `gh` token has the `project` scope (the adapter probes this internally; you can pre-check with `gh auth status`),
4. **opt-in prompt** — present exactly this question to the user verbatim (substituting the resolved values) and wait for an explicit answer before invoking bootstrap:

   > Bootstrap will create **{N_NEW}** new labels on **github.com/{OWNER}/{REPO}** ({M_EXISTING} canonical labels already present and will be force-updated to current descriptions/colors). It will also write `docs/agents/github-pm.json` locally. {PROJECT_LINE}Continue? [Y/n]

   where `{PROJECT_LINE}` is one of:
   - scope available and Project missing: `It will also create a new GitHub Project titled "{PROJECT_TITLE}" with PM custom fields. `
   - scope available and Project present: `It will also reuse the existing GitHub Project (#{PROJECT_NUMBER}). `
   - scope unavailable: `Projects scope is unavailable, so labels and config only (Issues-only mode). `

   - Answer **y** / **Y** / Enter: proceed to sub-step 5 below.
   - Answer **n** (or anything other than `y`/`Y`/empty): abort the bootstrap sub-step. Do not invoke `github_adapter.py bootstrap`. Do not call `gh label create` or `gh project create`. Tell the human: `Bootstrap skipped. Re-run /setup-pr-skills-rpm when you are ready to create the PM labels on github.com/OWNER/REPO.` Then continue to step 3 (Detect prior PM setup) — that step is read-only and is not affected by the declined prompt.
   - Labels-but-no-Project variant: if the user wants labels but not the Project, pass `--issues-only` to the bootstrap command in sub-step 5 and include that choice in the consent line above (`... but skip Project creation (Issues-only mode).`).
5. run the bundled `../project-management-rpm/github_adapter.py bootstrap` from the repository root (add `--issues-only` only if the human opted out of Project creation in sub-step 4),
6. let it create/update PM labels and `docs/agents/github-pm.json`,
7. if the current token has the `project` scope, let it create/reuse one GitHub Project and its PM fields,
8. if Projects access is unavailable, continue in Issues-only mode and tell the human they can later run `gh auth refresh -s project` and rerun `/setup-pr-skills-rpm` to upgrade.

Do not require GitHub Projects as a prerequisite for issue-based PM work. Do not run this adapter for a non-GitHub tracker. Do not skip the opt-in prompt even if `docs/agents/github-pm.json` already exists; a force-update of an existing label color or description still writes to the shared remote and the human must consent.

### 3. Detect prior PM setup

Look for `docs/agents/project-management.md` and for a tracker item labelled/marked `pm:project`.

- If a canonical project record already exists, do not create a second one. Ask whether the user wants to resume it or intentionally restart project-management state.
- If there is no PM setup, continue.

### 4. Start PM initialization

Call the Skill tool for `project-management-rpm` with the instruction `init`.

The `project-management-rpm` skill owns the interview about phase and goal. Do not ask those questions twice here.

### 5. Finish

After PM initialization completes, tell the user:

- which phase is active,
- the phase goal,
- where the canonical project record lives,
- where the active phase record lives,
- whether GitHub Projects is enabled or the repo is in Issues-only PM mode,
- where the GitHub PM Project lives when enabled,
- and that the next recommended action is the initial Wayfinder proposed by project-management.

The setup is not considered complete if phase or phase goal is still unset.
