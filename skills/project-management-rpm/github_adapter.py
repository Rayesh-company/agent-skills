#!/usr/bin/env python3
"""GitHub adapter for the PR-Skill project-management workflow.

Uses only Python stdlib + the GitHub CLI (`gh`). Issue records remain canonical;
GitHub Projects v2 is an optional structured metadata/indexing surface.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterable

CONFIG_PATH = Path("docs/agents/github-pm.json")

LABELS: dict[str, tuple[str, str]] = {
    "pm:project": ("5319E7", "Canonical product/project management record"),
    "pm:phase": ("7057FF", "Product development phase record"),
    "pm:task": ("8250DF", "Project-management executable work item"),
    "pm:milestone": ("A371F7", "Roadmap milestone/meta work"),
    "pm:backlog": ("D4C5F9", "PM workflow: backlog"),
    "pm:ready": ("0E8A16", "PM workflow: ready to claim"),
    "pm:claimed": ("1D76DB", "PM workflow: claimed/owned"),
    "pm:blocked": ("D93F0B", "PM workflow: blocked"),
    "pm:in-progress": ("FBCA04", "PM workflow: in progress"),
    "pm:review": ("BFDADC", "PM workflow: review/validation"),
    "pm:done": ("C2E0C6", "PM workflow: done"),
    "work:engineering": ("0052CC", "Engineering work"),
    "work:research": ("006B75", "Research/learning work"),
    "work:product": ("1D76DB", "Product work"),
    "work:design": ("D4C5F9", "Design work"),
    "work:business": ("C5DEF5", "Business/commercial work"),
    "work:docs": ("0075CA", "Documentation work"),
    "work:ops": ("E99695", "Operations work"),
    "work:meeting": ("F9D0C4", "Meeting/facilitation work"),
    "work:validation": ("BFD4F2", "Validation/testing work"),
    "work:access": ("F9C513", "Access/procurement/setup work"),
    "work:other": ("EDEDED", "Other project work"),
    "phase:0": ("D4C5F9", "Phase 0 — Research & Business Planning"),
    "phase:1": ("BFDADC", "Phase 1 — Demo"),
    "phase:2": ("A2EEEF", "Phase 2 — MVP"),
    "phase:3": ("C2E0C6", "Phase 3 — V1"),
    "phase:4": ("0E8A16", "Phase 4 — Full Product"),
}

WORKFLOW_LABELS = {
    "Backlog": "pm:backlog",
    "Ready": "pm:ready",
    "Claimed": "pm:claimed",
    "In Progress": "pm:in-progress",
    "Blocked": "pm:blocked",
    "Review": "pm:review",
    "Done": "pm:done",
}

WORK_TYPE_LABELS = {
    "Engineering": "work:engineering",
    "Research": "work:research",
    "Product": "work:product",
    "Design": "work:design",
    "Business": "work:business",
    "Docs": "work:docs",
    "Ops": "work:ops",
    "Meeting": "work:meeting",
    "Validation": "work:validation",
    "Access": "work:access",
    "Other": "work:other",
}

PROJECT_FIELDS: list[tuple[str, str, list[str] | None]] = [
    ("PM Status", "SINGLE_SELECT", list(WORKFLOW_LABELS)),
    ("Product Phase", "SINGLE_SELECT", [f"Phase {i}" for i in range(5)]),
    ("Sprint", "TEXT", None),
    ("Effort", "NUMBER", None),
    ("Deadline", "DATE", None),
    ("Technical Depth", "NUMBER", None),
    ("Work Type", "SINGLE_SELECT", list(WORK_TYPE_LABELS)),
    ("Priority", "SINGLE_SELECT", ["P0", "P1", "P2", "P3"]),
]


class AdapterCommandError(RuntimeError):
    """A recoverable failure at the injected GitHub command boundary."""


GhRunner = Callable[..., subprocess.CompletedProcess[str]]
GH_RUNNER: GhRunner = subprocess.run


@dataclass
class MutationResult:
    operation_id: str
    operation: str
    before: dict[str, Any]
    intended: dict[str, Any]
    completed_writes: list[str] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    recovery_writes: list[str] = field(default_factory=list)
    final_verdict: str = "Not accepted"
    drift: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def operation_id(operation: str, issue: int, before: dict[str, Any], intended: dict[str, Any]) -> str:
    payload = json.dumps(
        {"operation": operation, "issue": issue, "before": before, "intended": intended},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def die(message: str, code: int = 2) -> "NoReturn":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def run_gh(args: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if GH_RUNNER is subprocess.run and shutil.which("gh") is None:
        die("GitHub CLI `gh` is not installed or not on PATH")
    cmd = ["gh", *list(args)]
    proc = GH_RUNNER(cmd, text=True, capture_output=True)
    if check and proc.returncode != 0:
        stderr = proc.stderr.strip() or proc.stdout.strip() or "unknown gh error"
        raise AdapterCommandError(f"{' '.join(cmd)} failed: {stderr}")
    return proc


def gh_json(args: Iterable[str], *, check: bool = True) -> Any:
    proc = run_gh(args, check=check)
    if proc.returncode != 0:
        return None
    text = proc.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        die(f"expected JSON from gh but received invalid JSON: {exc}")


def detect_repo(explicit: str | None = None) -> dict[str, str]:
    args = ["repo", "view"]
    if explicit:
        args.append(explicit)
    args += ["--json", "nameWithOwner,url"]
    data = gh_json(args)
    name_with_owner = data.get("nameWithOwner") if isinstance(data, dict) else None
    url = data.get("url") if isinstance(data, dict) else None
    if not name_with_owner:
        die("could not determine GitHub repository; run inside a GitHub clone or pass --repo OWNER/REPO")
    owner, name = name_with_owner.split("/", 1)
    return {"repo": name_with_owner, "repo_owner": owner, "repo_name": name, "repo_url": url or ""}


def auth_ok() -> bool:
    return run_gh(["auth", "status"], check=False).returncode == 0


def projects_access(owner: str) -> tuple[bool, str]:
    proc = run_gh(["project", "list", "--owner", owner, "--limit", "1", "--format", "json"], check=False)
    if proc.returncode == 0:
        return True, ""
    return False, (proc.stderr.strip() or proc.stdout.strip())


def load_config(required: bool = True) -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        if required:
            die(f"{CONFIG_PATH} is missing; run `github_adapter.py bootstrap` first")
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        die(f"could not read {CONFIG_PATH}: {exc}")


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")


def repo_flag(repo: str) -> list[str]:
    return ["-R", repo]


def ensure_labels(repo: str) -> None:
    for name, (color, description) in LABELS.items():
        run_gh([
            "label", "create", name,
            "--force",
            "--color", color,
            "--description", description,
            *repo_flag(repo),
        ])


def find_projects(owner: str, title: str) -> list[dict[str, Any]]:
    data = gh_json(["project", "list", "--owner", owner, "--limit", "100", "--format", "json"])
    projects = data.get("projects", []) if isinstance(data, dict) else []
    return [p for p in projects if p.get("title") == title]


def ensure_project(owner: str, title: str, configured_number: int | None = None) -> dict[str, Any]:
    if configured_number is not None:
        data = gh_json(["project", "view", str(configured_number), "--owner", owner, "--format", "json"], check=False)
        if isinstance(data, dict) and data.get("number") == configured_number:
            return data

    matches = find_projects(owner, title)
    if len(matches) > 1:
        die(f"multiple GitHub Projects named {title!r} exist for {owner}; pass/reuse an explicit configured project number")
    if len(matches) == 1:
        number = matches[0].get("number")
        return gh_json(["project", "view", str(number), "--owner", owner, "--format", "json"])

    created = gh_json(["project", "create", "--owner", owner, "--title", title, "--format", "json"])
    if not isinstance(created, dict):
        die("GitHub Project was created but its metadata could not be read")
    return created


def ensure_project_fields(owner: str, number: int) -> list[str]:
    data = gh_json(["project", "field-list", str(number), "--owner", owner, "--limit", "100", "--format", "json"])
    existing = {f.get("name"): f for f in (data.get("fields", []) if isinstance(data, dict) else [])}
    warnings: list[str] = []
    for name, data_type, options in PROJECT_FIELDS:
        current = existing.get(name)
        if current:
            current_type = current.get("type", "")
            is_single_select = "singleselect" in current_type.lower()
            if data_type == "SINGLE_SELECT" and not is_single_select:
                warnings.append(f"field {name!r} already exists with type {current_type}; expected SINGLE_SELECT")
            elif data_type != "SINGLE_SELECT" and is_single_select:
                warnings.append(f"field {name!r} already exists as a single-select field; expected {data_type}")
            if data_type == "SINGLE_SELECT" and options:
                current_options = {opt.get("name") for opt in current.get("options", []) if isinstance(opt, dict)}
                missing = [opt for opt in options if opt not in current_options]
                if current_options and missing:
                    warnings.append(f"field {name!r} is missing options: {', '.join(missing)}")
            continue
        args = [
            "project", "field-create", str(number),
            "--owner", owner,
            "--name", name,
            "--data-type", data_type,
            "--format", "json",
        ]
        if options:
            args += ["--single-select-options", ",".join(options)]
        run_gh(args)
    return warnings


def project_metadata_from_config(config: dict[str, Any]) -> tuple[str, int] | None:
    if not config.get("projects_enabled"):
        return None
    owner = config.get("project_owner")
    number = config.get("project_number")
    if owner and isinstance(number, int):
        return owner, number
    return None


def issue_url(issue: int, repo: str) -> str:
    data = gh_json(["issue", "view", str(issue), *repo_flag(repo), "--json", "url"])
    if not isinstance(data, dict) or not data.get("url"):
        die(f"could not resolve URL for issue #{issue}")
    return data["url"]


def ensure_project_item(issue: int, config: dict[str, Any]) -> bool:
    project = project_metadata_from_config(config)
    if project is None:
        return False
    owner, number = project
    url = issue_url(issue, config["repo"])
    proc = run_gh([
        "project", "item-add", str(number),
        "--owner", owner,
        "--url", url,
        "--format", "json",
    ], check=False)
    if proc.returncode != 0:
        msg = (proc.stderr + "\n" + proc.stdout).lower()
        if "already" not in msg and "exists" not in msg:
            die(f"could not add {url} to GitHub Project: {proc.stderr.strip() or proc.stdout.strip()}")
    return True


def set_project_field(issue: int, field: str, value: str | int | float | None, config: dict[str, Any]) -> None:
    project = project_metadata_from_config(config)
    if project is None or value is None or value == "":
        return
    owner, number = project
    url = issue_url(issue, config["repo"])
    args = ["project", "item-edit", str(number), "--owner", owner, "--url", url, "--field", field]
    if field == "Deadline":
        args += ["--date", str(value)]
    elif field in {"Effort", "Technical Depth"}:
        args += ["--number", str(value)]
    elif field == "Sprint":
        args += ["--text", str(value)]
    else:
        args += ["--value", str(value)]
    run_gh(args)


def remove_labels(issue: int, labels: Iterable[str], repo: str) -> None:
    names = list(labels)
    if not names:
        return
    existing = gh_json(["issue", "view", str(issue), *repo_flag(repo), "--json", "labels"])
    current = {x.get("name") for x in existing.get("labels", [])} if isinstance(existing, dict) else set()
    to_remove = [name for name in names if name in current]
    if to_remove:
        run_gh(["issue", "edit", str(issue), *repo_flag(repo), "--remove-label", ",".join(to_remove)])


def add_labels(issue: int, labels: Iterable[str], repo: str) -> None:
    names = [x for x in labels if x]
    if names:
        run_gh(["issue", "edit", str(issue), *repo_flag(repo), "--add-label", ",".join(names)])


def issue_snapshot(issue: int, config: dict[str, Any]) -> dict[str, Any]:
    data = gh_json([
        "issue", "view", str(issue), *repo_flag(config["repo"]),
        "--json", "number,state,labels,assignees,url",
    ])
    if not isinstance(data, dict):
        raise AdapterCommandError(f"could not read issue #{issue}")
    snapshot = {
        "issue": issue,
        "state": data.get("state"),
        "labels": sorted(
            label.get("name") for label in data.get("labels", [])
            if isinstance(label, dict) and label.get("name")
        ),
        "assignees": sorted(
            owner.get("login") for owner in data.get("assignees", [])
            if isinstance(owner, dict) and owner.get("login")
        ),
        "url": data.get("url"),
    }
    if project_metadata_from_config(config) is not None:
        snapshot["project_status"] = project_status_for_issue(issue, config)
    return snapshot


def workflow_statuses(snapshot: dict[str, Any]) -> list[str]:
    reverse = {label: status for status, label in WORKFLOW_LABELS.items()}
    return [reverse[label] for label in snapshot.get("labels", []) if label in reverse]


def plan_state_transition(snapshot: dict[str, Any], status: str) -> dict[str, Any]:
    if status not in WORKFLOW_LABELS:
        die(f"unknown status {status!r}; choose one of: {', '.join(WORKFLOW_LABELS)}")
    return {
        "status": status,
        "workflow_label": WORKFLOW_LABELS[status],
        "requires_assignee": status == "Claimed",
    }


def verify_state_snapshot(snapshot: dict[str, Any], status: str) -> list[dict[str, Any]]:
    statuses = workflow_statuses(snapshot)
    results = [{
        "invariant": "exactly one workflow state",
        "passed": statuses == [status],
        "observed": statuses,
        "expected": [status],
    }]
    if status == "Claimed":
        results.append({
            "invariant": "claimed work has an assignee",
            "passed": bool(snapshot.get("assignees")),
            "observed": snapshot.get("assignees", []),
            "expected": "at least one assignee",
        })
    if "project_status" in snapshot:
        results.append({
            "invariant": "PM Status mirror agrees with workflow label",
            "passed": snapshot.get("project_status") == status,
            "observed": snapshot.get("project_status"),
            "expected": status,
        })
    return results


def restore_workflow_snapshot(issue: int, snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    repo = config["repo"]
    remove_labels(issue, WORKFLOW_LABELS.values(), repo)
    prior_labels = [label for label in snapshot.get("labels", []) if label in WORKFLOW_LABELS.values()]
    add_labels(issue, prior_labels, repo)
    prior_statuses = workflow_statuses(snapshot)
    ensure_project_item(issue, config)
    writes = ["restored workflow labels"]
    if len(prior_statuses) == 1:
        set_project_field(issue, "PM Status", prior_statuses[0], config)
        writes.append("restored PM Status mirror")
    elif project_metadata_from_config(config) is not None:
        writes.append("PM Status mirror requires manual clearing")
    return writes


def set_state(issue: int, status: str, config: dict[str, Any]) -> MutationResult:
    before = issue_snapshot(issue, config)
    intended = plan_state_transition(before, status)
    result = MutationResult(
        operation_id=operation_id("state", issue, before, intended),
        operation="state",
        before=before,
        intended=intended,
    )
    existing = workflow_statuses(before)
    mirror_valid = "project_status" not in before or before.get("project_status") == status
    already_valid = (
        existing == [status]
        and (status != "Claimed" or bool(before["assignees"]))
        and mirror_valid
    )
    if already_valid:
        result.verification_results = verify_state_snapshot(before, status)
        result.final_verdict = "Accepted"
        return result

    try:
        repo = config["repo"]
        remove_labels(issue, WORKFLOW_LABELS.values(), repo)
        result.completed_writes.append("removed prior workflow labels")
        add_labels(issue, [WORKFLOW_LABELS[status]], repo)
        result.completed_writes.append(f"set label {WORKFLOW_LABELS[status]}")
        ensure_project_item(issue, config)
        set_project_field(issue, "PM Status", status, config)
        if project_metadata_from_config(config) is not None:
            result.completed_writes.append(f"set PM Status={status}")
        after = issue_snapshot(issue, config)
        result.verification_results = verify_state_snapshot(after, status)
        if all(check["passed"] for check in result.verification_results):
            result.final_verdict = "Accepted"
            return result
        raise AdapterCommandError("state postconditions failed")
    except (AdapterCommandError, SystemExit) as exc:
        result.verification_results.append({"invariant": "mutation completed", "passed": False, "error": str(exc)})
        try:
            result.recovery_writes.extend(restore_workflow_snapshot(issue, before, config))
            recovered = issue_snapshot(issue, config)
            if workflow_statuses(recovered) == workflow_statuses(before):
                result.final_verdict = "Recovered"
            else:
                result.final_verdict = "State drift"
                result.drift.append("workflow labels differ from the before snapshot after recovery")
        except (AdapterCommandError, SystemExit) as recovery_error:
            result.final_verdict = "State drift"
            result.drift.append(f"recovery failed: {recovery_error}")
        return result


def apply_metadata(
    issue: int,
    config: dict[str, Any],
    *,
    phase: int | None = None,
    status: str | None = None,
    work_type: str | None = None,
    effort: float | None = None,
    deadline: str | None = None,
    technical_depth: float | None = None,
    priority: str | None = None,
    sprint: str | None = None,
) -> None:
    repo = config["repo"]
    ensure_project_item(issue, config)
    if phase is not None:
        if phase not in range(5):
            die("phase must be 0, 1, 2, 3, or 4")
        remove_labels(issue, [f"phase:{i}" for i in range(5)], repo)
        add_labels(issue, [f"phase:{phase}"], repo)
        set_project_field(issue, "Product Phase", f"Phase {phase}", config)
    if status is not None:
        state_result = set_state(issue, status, config)
        if state_result.final_verdict != "Accepted":
            raise AdapterCommandError(json.dumps(state_result.to_dict(), sort_keys=True))
    if work_type is not None:
        if work_type not in WORK_TYPE_LABELS:
            die(f"unknown work type {work_type!r}; choose one of: {', '.join(WORK_TYPE_LABELS)}")
        remove_labels(issue, WORK_TYPE_LABELS.values(), repo)
        add_labels(issue, [WORK_TYPE_LABELS[work_type]], repo)
        set_project_field(issue, "Work Type", work_type, config)
    if effort is not None:
        set_project_field(issue, "Effort", effort, config)
    if deadline:
        set_project_field(issue, "Deadline", deadline, config)
    if technical_depth is not None:
        if not (0 <= technical_depth <= 4):
            die("technical depth must be between 0 and 4")
        set_project_field(issue, "Technical Depth", technical_depth, config)
    if priority:
        if priority not in {"P0", "P1", "P2", "P3"}:
            die("priority must be one of P0, P1, P2, P3")
        set_project_field(issue, "Priority", priority, config)
    if sprint:
        set_project_field(issue, "Sprint", sprint, config)


def cmd_doctor(args: argparse.Namespace) -> None:
    if shutil.which("gh") is None:
        print(json.dumps({"gh_installed": False}, indent=2))
        return
    repo = detect_repo(args.repo)
    ok = auth_ok()
    access, reason = projects_access(args.project_owner or repo["repo_owner"]) if ok else (False, "not authenticated")
    print(json.dumps({
        **repo,
        "gh_installed": True,
        "authenticated": ok,
        "projects_access": access,
        "projects_reason": reason,
        "config_exists": CONFIG_PATH.exists(),
    }, indent=2))


def cmd_bootstrap(args: argparse.Namespace) -> None:
    repo = detect_repo(args.repo)
    if not auth_ok():
        die("gh is not authenticated; run `gh auth login` and retry")
    ensure_labels(repo["repo"])

    previous = load_config(required=False)
    project_owner = args.project_owner or previous.get("project_owner") or repo["repo_owner"]
    project_title = args.project_title or previous.get("project_title") or f"{repo['repo_name']} Product Delivery"
    config: dict[str, Any] = {
        "adapter": "github",
        **repo,
        "project_owner": project_owner,
        "project_title": project_title,
        "projects_enabled": False,
        "project_number": None,
        "project_url": None,
    }

    access, reason = projects_access(project_owner)
    warnings: list[str] = []
    if args.issues_only:
        reason = "--issues-only requested"
    elif access:
        configured_number = previous.get("project_number") if previous.get("project_owner") == project_owner else None
        project = ensure_project(project_owner, project_title, configured_number)
        number = project.get("number")
        if not isinstance(number, int):
            die("GitHub Project metadata did not include a numeric project number")
        warnings.extend(ensure_project_fields(project_owner, number))
        config.update({
            "projects_enabled": True,
            "project_number": number,
            "project_url": project.get("url"),
        })
    else:
        warnings.append("GitHub Projects unavailable; continuing in Issues-only mode")
        if reason:
            warnings.append(reason)
        warnings.append("To enable Projects, verify auth and run: gh auth refresh -s project")

    save_config(config)
    print(json.dumps({"config": config, "warnings": warnings}, indent=2))


def add_metadata_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--phase", type=int, choices=range(5))
    parser.add_argument("--status", choices=list(WORKFLOW_LABELS))
    parser.add_argument("--work-type", choices=list(WORK_TYPE_LABELS))
    parser.add_argument("--effort", type=float)
    parser.add_argument("--deadline", help="YYYY-MM-DD")
    parser.add_argument("--technical-depth", type=float)
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"])
    parser.add_argument("--sprint")


def cmd_enroll(args: argparse.Namespace) -> None:
    config = load_config()
    apply_metadata(
        args.issue, config,
        phase=args.phase,
        status=args.status,
        work_type=args.work_type,
        effort=args.effort,
        deadline=args.deadline,
        technical_depth=args.technical_depth,
        priority=args.priority,
        sprint=args.sprint,
    )
    print(f"enrolled #{args.issue}")


def cmd_issue_create(args: argparse.Namespace) -> None:
    config = load_config()
    repo = config["repo"]
    kind_label = {"project": "pm:project", "phase": "pm:phase", "task": "pm:task", "milestone": "pm:milestone"}[args.kind]
    labels = [kind_label]
    if args.phase is not None:
        labels.append(f"phase:{args.phase}")
    if args.status:
        labels.append(WORKFLOW_LABELS[args.status])
    if args.work_type:
        labels.append(WORK_TYPE_LABELS[args.work_type])

    gh_args = ["issue", "create", *repo_flag(repo), "--title", args.title, "--body-file", args.body_file]
    for label in labels:
        gh_args += ["--label", label]
    if args.milestone:
        gh_args += ["--milestone", args.milestone]
    proc = run_gh(gh_args)
    url = proc.stdout.strip().splitlines()[-1].strip()
    try:
        issue = int(url.rstrip("/").split("/")[-1])
    except ValueError:
        die(f"issue created but could not parse issue number from output: {url!r}")

    if args.parent is not None:
        run_gh(["issue", "edit", str(issue), *repo_flag(repo), "--parent", str(args.parent)])
    if args.blocked_by:
        run_gh(["issue", "edit", str(issue), *repo_flag(repo), "--add-blocked-by", ",".join(map(str, args.blocked_by))])

    apply_metadata(
        issue, config,
        phase=args.phase,
        status=args.status,
        work_type=args.work_type,
        effort=args.effort,
        deadline=args.deadline,
        technical_depth=args.technical_depth,
        priority=args.priority,
        sprint=args.sprint,
    )
    print(json.dumps({"number": issue, "url": url}, indent=2))


def cmd_relate(args: argparse.Namespace) -> None:
    config = load_config()
    repo = config["repo"]
    gh_args = ["issue", "edit", str(args.issue), *repo_flag(repo)]
    if args.parent is not None:
        gh_args += ["--parent", str(args.parent)]
    if args.blocked_by:
        gh_args += ["--add-blocked-by", ",".join(map(str, args.blocked_by))]
    if args.blocking:
        gh_args += ["--add-blocking", ",".join(map(str, args.blocking))]
    if len(gh_args) == 5:
        die("relate requires --parent, --blocked-by, or --blocking")
    run_gh(gh_args)
    print(f"updated relationships for #{args.issue}")


def resolve_assignee(login: str) -> tuple[str, str]:
    """Return (gh argument, canonical login) for assignment comparisons."""
    if login != "@me":
        return login, login
    proc = run_gh(["api", "user", "--jq", ".login"])
    canonical = proc.stdout.strip()
    if not canonical:
        die("could not resolve @me to the authenticated GitHub login")
    return "@me", canonical


def cmd_claim(args: argparse.Namespace) -> None:
    config = load_config()
    repo = config["repo"]
    data = gh_json(["issue", "view", str(args.issue), *repo_flag(repo), "--json", "state,assignees,labels"])
    if data.get("state") != "OPEN":
        die(f"issue #{args.issue} is not open")
    current = [a.get("login") for a in data.get("assignees", []) if a.get("login")]
    assignment_arg, target = resolve_assignee(args.assignee)
    if current and target not in current:
        die(f"issue #{args.issue} is already assigned to {', '.join(current)}; refusing to steal the claim")
    before = issue_snapshot(args.issue, config)
    intended = {"status": "Claimed", "assignee": target, "audit_annotation": True}
    result = MutationResult(
        operation_id=operation_id("claim", args.issue, before, intended),
        operation="claim",
        before=before,
        intended=intended,
    )
    assignment_added = target not in current
    try:
        if assignment_added:
            run_gh(["issue", "edit", str(args.issue), *repo_flag(repo), "--add-assignee", assignment_arg])
            result.completed_writes.append(f"assigned {target}")
        state_result = set_state(args.issue, "Claimed", config)
        result.completed_writes.extend(state_result.completed_writes)
        if state_result.final_verdict != "Accepted":
            raise AdapterCommandError(f"state transition ended {state_result.final_verdict}")
        annotation = f"Claimed by @{target}. Operation `{result.operation_id}`."
        run_gh(["issue", "comment", str(args.issue), *repo_flag(repo), "--body", annotation])
        result.completed_writes.append("recorded claim annotation")
        after = issue_snapshot(args.issue, config)
        result.verification_results = verify_state_snapshot(after, "Claimed")
        result.verification_results.append({
            "invariant": "claimer is assigned",
            "passed": target in after["assignees"],
            "observed": after["assignees"],
            "expected": target,
        })
        result.final_verdict = "Accepted" if all(x["passed"] for x in result.verification_results) else "State drift"
        if len(after["assignees"]) > 1:
            result.drift.append("multiple assignees detected; resolve ownership explicitly")
    except (AdapterCommandError, SystemExit) as exc:
        result.verification_results.append({"invariant": "claim completed", "passed": False, "error": str(exc)})
        try:
            result.recovery_writes.extend(restore_workflow_snapshot(args.issue, before, config))
            if assignment_added:
                run_gh(["issue", "edit", str(args.issue), *repo_flag(repo), "--remove-assignee", assignment_arg])
                result.recovery_writes.append(f"removed assignee {target}")
            result.final_verdict = "Recovered"
        except (AdapterCommandError, SystemExit) as recovery_error:
            result.final_verdict = "State drift"
            result.drift.append(f"claim recovery failed: {recovery_error}")
    print(json.dumps(result.to_dict(), indent=2))
    if result.final_verdict != "Accepted":
        raise SystemExit(1)


def cmd_state(args: argparse.Namespace) -> None:
    config = load_config()
    result = set_state(args.issue, args.status, config)
    print(json.dumps(result.to_dict(), indent=2))
    if result.final_verdict != "Accepted":
        raise SystemExit(1)


def cmd_done(args: argparse.Namespace) -> None:
    config = load_config()
    repo = config["repo"]
    if args.comment:
        run_gh(["issue", "comment", str(args.issue), *repo_flag(repo), "--body", args.comment])
    result = set_state(args.issue, "Done", config)
    if result.final_verdict != "Accepted":
        print(json.dumps(result.to_dict(), indent=2))
        raise SystemExit(1)
    data = gh_json(["issue", "view", str(args.issue), *repo_flag(repo), "--json", "state"])
    if data.get("state") == "OPEN":
        run_gh(["issue", "close", str(args.issue), *repo_flag(repo)])
    result.completed_writes.append("closed issue" if data.get("state") == "OPEN" else "issue already closed")
    print(json.dumps(result.to_dict(), indent=2))


def project_status_for_issue(issue: int, config: dict[str, Any]) -> str | None:
    project = project_metadata_from_config(config)
    if project is None:
        return None
    owner, number = project
    data = gh_json([
        "project", "item-list", str(number), "--owner", owner,
        "--format", "json", "--limit", "200",
    ])
    items = data.get("items", []) if isinstance(data, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        content = item.get("content", {})
        if not isinstance(content, dict) or str(content.get("number")) != str(issue):
            continue
        for key in ("PM Status", "pm Status", "pm_status"):
            if item.get(key):
                return str(item[key])
        for field_value in item.get("fieldValues", []):
            if isinstance(field_value, dict) and field_value.get("field", {}).get("name") == "PM Status":
                return field_value.get("name") or field_value.get("text")
    return None


def reconcile_snapshot(
    snapshot: dict[str, Any],
    project_status: str | None,
    *,
    mirror_expected: bool = False,
) -> dict[str, Any]:
    statuses = workflow_statuses(snapshot)
    differences: list[dict[str, Any]] = []
    ambiguous = len(statuses) > 1
    canonical_status = statuses[0] if len(statuses) == 1 else None
    if len(statuses) != 1:
        differences.append({
            "surface": "labels",
            "expected": "exactly one workflow label",
            "observed": statuses,
            "repairable": False,
        })
    if canonical_status == "Claimed" and not snapshot.get("assignees"):
        differences.append({
            "surface": "assignment",
            "expected": "an assignee for Claimed",
            "observed": [],
            "repairable": False,
        })
        ambiguous = True
    if canonical_status is not None and (
        (mirror_expected and project_status is None)
        or (project_status is not None and project_status != canonical_status)
    ):
        differences.append({
            "surface": "PM Status",
            "expected": canonical_status,
            "observed": project_status,
            "repairable": True,
        })
    return {
        "issue": snapshot.get("issue"),
        "canonical_status": canonical_status,
        "project_status": project_status,
        "differences": differences,
        "ambiguous": ambiguous,
        "verdict": "Consistent" if not differences else ("Ambiguous" if ambiguous else "Drift"),
    }


def cmd_reconcile(args: argparse.Namespace) -> None:
    config = load_config()
    snapshot = issue_snapshot(args.issue, config)
    report = reconcile_snapshot(
        snapshot,
        snapshot.get("project_status"),
        mirror_expected=project_metadata_from_config(config) is not None,
    )
    if not args.apply:
        print(json.dumps({"mode": "read-only", **report}, indent=2))
        return
    if args.confirm != "APPLY":
        die("reconcile --apply requires --confirm APPLY")
    if report["ambiguous"] or not report["canonical_status"]:
        die("canonical issue state is ambiguous; refusing to apply reconciliation")
    result = set_state(args.issue, report["canonical_status"], config)
    print(json.dumps({"mode": "apply", "before_report": report, "mutation": result.to_dict()}, indent=2))
    if result.final_verdict != "Accepted":
        raise SystemExit(1)


def flatten_pages(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list) and data and isinstance(data[0], list):
        return [item for page in data for item in page if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def cmd_milestone_ensure(args: argparse.Namespace) -> None:
    config = load_config()
    repo = config["repo"]
    data = gh_json([
        "api", f"repos/{repo}/milestones?state=all&per_page=100",
        "--paginate", "--slurp",
    ])
    milestones = flatten_pages(data)
    matches = [m for m in milestones if m.get("title") == args.title]
    if len(matches) > 1:
        die(f"multiple milestones named {args.title!r} found")
    if matches:
        print(json.dumps(matches[0], indent=2))
        return
    gh_args = ["api", "--method", "POST", f"repos/{repo}/milestones", "-f", f"title={args.title}"]
    if args.description:
        gh_args += ["-f", f"description={args.description}"]
    if args.due:
        gh_args += ["-f", f"due_on={args.due}T23:59:59Z"]
    created = gh_json(gh_args)
    print(json.dumps(created, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GitHub adapter for the PR-Skill PM workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="inspect gh/repo/Projects readiness")
    p.add_argument("--repo")
    p.add_argument("--project-owner")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("bootstrap", help="ensure labels, optional Project v2 fields, and write adapter config")
    p.add_argument("--repo")
    p.add_argument("--project-owner")
    p.add_argument("--project-title")
    p.add_argument("--issues-only", action="store_true", help="configure labels/issues without a GitHub Project")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("issue-create", help="create and enroll a managed GitHub issue")
    p.add_argument("--kind", choices=["project", "phase", "task", "milestone"], required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    p.add_argument("--parent", type=int)
    p.add_argument("--blocked-by", type=int, nargs="*")
    p.add_argument("--milestone")
    add_metadata_args(p)
    p.set_defaults(func=cmd_issue_create)

    p = sub.add_parser("enroll", help="enroll an existing issue in PM metadata/Project")
    p.add_argument("issue", type=int)
    add_metadata_args(p)
    p.set_defaults(func=cmd_enroll)

    p = sub.add_parser("relate", help="set native GitHub parent/blocking relationships")
    p.add_argument("issue", type=int)
    p.add_argument("--parent", type=int)
    p.add_argument("--blocked-by", type=int, nargs="*")
    p.add_argument("--blocking", type=int, nargs="*")
    p.set_defaults(func=cmd_relate)

    p = sub.add_parser("claim", help="claim an unassigned open issue")
    p.add_argument("issue", type=int)
    p.add_argument("--assignee", default="@me")
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("state", help="synchronize workflow label and PM Status field")
    p.add_argument("issue", type=int)
    p.add_argument("status", choices=list(WORKFLOW_LABELS))
    p.set_defaults(func=cmd_state)

    p = sub.add_parser("done", help="record evidence, set Done, then close if still open")
    p.add_argument("issue", type=int)
    p.add_argument("--comment")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("reconcile", help="report or explicitly repair workflow-state drift")
    p.add_argument("issue", type=int)
    p.add_argument("--apply", action="store_true", help="repair mirrors from unambiguous issue state")
    p.add_argument("--confirm", help="must be APPLY when --apply is used")
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("milestone-ensure", help="reuse or create a native GitHub Milestone")
    p.add_argument("--title", required=True)
    p.add_argument("--description")
    p.add_argument("--due", help="YYYY-MM-DD")
    p.set_defaults(func=cmd_milestone_ensure)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except AdapterCommandError as exc:
        die(str(exc))


if __name__ == "__main__":
    main()
