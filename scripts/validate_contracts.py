#!/usr/bin/env python3
"""Validate the repository's interconnected skill contracts using stdlib only."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
INVENTORY = ROOT / "skill-inventory.json"
FRONTMATTER = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
NAME = re.compile(r"^name:\s*['\"]?([^'\"\n]+)['\"]?\s*$", re.MULTILINE)
MARKDOWN_LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")
SLASH_CALL = re.compile(r"`/(?!compact\b)([a-z][a-z0-9-]+)(?=[\s`<]|$)")
RPM_NAME = re.compile(r"\b([a-z][a-z0-9-]*-rpm)\b")
MODE_HEADING = re.compile(r"^# Mode: ([a-z][a-z-]*)", re.MULTILINE)
PM_CALL = re.compile(r"/project-management-rpm\s+([a-z][a-z-]*)")


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError("missing `---` frontmatter")
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    return fields, text


def relative_links(path: Path, text: str) -> list[Path]:
    links: list[Path] = []
    for target in MARKDOWN_LINK.findall(text):
        target = target.split("#", 1)[0]
        if (
            not target
            or target == "link"
            or "://" in target
            or target.startswith(("#", "mailto:", "./src/"))
        ):
            continue
        links.append((path.parent / target).resolve())
    return links


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    inventory_path = root / INVENTORY.relative_to(ROOT)
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{inventory_path.relative_to(root)}: invalid inventory: {exc}"]

    skill_root = root / "skills"
    directories = sorted(p for p in skill_root.iterdir() if p.is_dir())
    actual = [p.name for p in directories]
    expected = inventory.get("skills")
    if expected != actual:
        errors.append("skill-inventory.json: skills must exactly match sorted skill directories")

    texts: dict[str, str] = {}
    for directory in directories:
        skill_file = directory / "SKILL.md"
        if not skill_file.exists():
            errors.append(f"{directory.relative_to(root)}: missing SKILL.md")
            continue
        try:
            fields, text = parse_frontmatter(skill_file)
        except ValueError as exc:
            errors.append(f"{skill_file.relative_to(root)}: {exc}")
            continue
        texts[directory.name] = text
        if fields.get("name") != directory.name:
            errors.append(
                f"{skill_file.relative_to(root)}: name {fields.get('name')!r} does not match directory"
            )
        if not fields.get("description"):
            errors.append(f"{skill_file.relative_to(root)}: description is required")

        agent_file = directory / "agents" / "openai.yaml"
        if not agent_file.exists():
            errors.append(f"{agent_file.relative_to(root)}: missing metadata")
        else:
            agent_text = agent_file.read_text(encoding="utf-8")
            if "interface:" not in agent_text or "display_name:" not in agent_text:
                errors.append(f"{agent_file.relative_to(root)}: invalid interface metadata")
            display = re.search(r"^\s*display_name:\s*['\"]?([^'\"\n]+)", agent_text, re.MULTILINE)
            if not display or not display.group(1).endswith(" RPM"):
                errors.append(
                    f"{agent_file.relative_to(root)}: display_name must coherently identify the RPM skill"
                )
            implicit = re.search(r"allow_implicit_invocation:\s*(true|false)", agent_text)
            if fields.get("disable-model-invocation") == "true" and implicit and implicit.group(1) == "true":
                errors.append(
                    f"{agent_file.relative_to(root)}: invocation policy contradicts SKILL.md frontmatter"
                )

        for link in relative_links(skill_file, text):
            if not link.exists():
                errors.append(f"{skill_file.relative_to(root)}: broken relative link to {link}")

        for call in SLASH_CALL.findall(text):
            if call.endswith("-rpm") and call not in actual:
                errors.append(f"{skill_file.relative_to(root)}: unknown skill invocation /{call}")
            elif not call.endswith("-rpm") and (skill_root / f"{call}-rpm").is_dir():
                errors.append(f"{skill_file.relative_to(root)}: legacy unscoped invocation /{call}")

        for reference in RPM_NAME.findall(text):
            if reference not in actual:
                errors.append(f"{skill_file.relative_to(root)}: unknown skill reference {reference}")

    for core in inventory.get("core_acceptance_skills", []):
        if "ACCEPTANCE-LOOP.md" not in texts.get(core, ""):
            errors.append(f"skills/{core}/SKILL.md: core skill must reference ACCEPTANCE-LOOP.md")

    router = texts.get(inventory.get("router", ""), "")
    project = texts.get("project-management-rpm", "")
    modes = set(MODE_HEADING.findall(project))
    for mode in PM_CALL.findall(router):
        if mode not in modes:
            errors.append(f"skills/ask-matt-rpm/SKILL.md: router mode {mode!r} is not implemented")

    for spec in root.rglob("*IMPLEMENTATION-SPEC.md"):
        prefix = spec.read_text(encoding="utf-8")[:400]
        if "## Status" not in prefix or "Proposed" not in prefix:
            errors.append(f"{spec.relative_to(root)}: proposed specification needs an explicit Status")

    python_files = sorted((root / "scripts").glob("*.py")) + [
        root / "skills" / "project-management-rpm" / "github_adapter.py"
    ]
    for script in python_files:
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except (OSError, SyntaxError) as exc:
            errors.append(f"{script.relative_to(root)}: script does not parse: {exc}")

    if "project-management-rpm" in actual:
        adapter_text = (
            root / "skills" / "project-management-rpm" / "github_adapter.py"
        ).read_text(encoding="utf-8")
        expected_commands = {
            "doctor", "bootstrap", "issue-create", "enroll", "relate", "claim",
            "state", "done", "reconcile", "milestone-ensure",
        }
        declared_commands = set(re.findall(r'add_parser\("([a-z-]+)"', adapter_text))
        if declared_commands != expected_commands:
            errors.append("skills/project-management-rpm/github_adapter.py: command surface drift")

        adapter_doc = (
            root / "skills" / "project-management-rpm" / "GITHUB-ADAPTER.md"
        ).read_text(encoding="utf-8")
        label_names = set(re.findall(
            r'^\s*"((?:pm|work|phase):[a-z0-9-]+)":', adapter_text, re.MULTILINE
        ))
        undocumented_labels = sorted(label for label in label_names if f"`{label}`" not in adapter_doc)
        if undocumented_labels:
            errors.append(
                "skills/project-management-rpm/GITHUB-ADAPTER.md: undocumented canonical labels: "
                + ", ".join(undocumented_labels)
            )

    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print("contract validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
