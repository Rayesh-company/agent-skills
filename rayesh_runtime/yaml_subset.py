"""Small stdlib-only YAML subset used by Rayesh workflow definitions.

The repository intentionally keeps CI validation dependency-free. This parser
supports the subset Rayesh v1 emits: indentation-based mappings plus scalar
values and JSON-style flow lists/maps. It is deliberately strict; unsupported
YAML features fail with a useful error rather than being interpreted loosely.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")


class YamlSubsetError(ValueError):
    pass


def _scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "":
        return None
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"null", "~"}:
        return None
    if value.startswith(("[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError(
                "flow lists/maps must use JSON quoting in Rayesh YAML v1"
            ) from exc
    if value.startswith(("'", '"')):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise YamlSubsetError(f"invalid quoted scalar: {value}") from exc
        if not isinstance(parsed, str):
            raise YamlSubsetError("quoted scalars must resolve to strings")
        return parsed
    if re.fullmatch(r"-?[0-9]+", value):
        return int(value)
    if re.fullmatch(r"-?[0-9]+\.[0-9]+", value):
        return float(value)
    if value in {"|", ">"}:
        raise YamlSubsetError(
            "block scalars are not supported in Rayesh YAML v1; use a quoted string"
        )
    return value


def loads(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    # Stack entries are (indent of key that introduced this mapping, mapping).
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_number, original in enumerate(text.splitlines(), start=1):
        if not original.strip() or original.lstrip().startswith("#"):
            continue
        if "\t" in original[: len(original) - len(original.lstrip())]:
            raise YamlSubsetError(f"line {line_number}: tabs are not allowed")

        indent = len(original) - len(original.lstrip(" "))
        if indent % 2:
            raise YamlSubsetError(
                f"line {line_number}: indentation must use multiples of two spaces"
            )
        body = original.strip()
        if body.startswith("- "):
            raise YamlSubsetError(
                f"line {line_number}: block sequences are unsupported; use JSON-style []"
            )
        if ":" not in body:
            raise YamlSubsetError(f"line {line_number}: expected key: value")

        key, raw_value = body.split(":", 1)
        key = key.strip()
        if not _KEY.fullmatch(key):
            raise YamlSubsetError(f"line {line_number}: invalid key {key!r}")

        while stack[-1][0] >= indent:
            stack.pop()
        parent_indent, parent = stack[-1]
        if indent > parent_indent + 2 and parent_indent != -1:
            raise YamlSubsetError(
                f"line {line_number}: indentation jumps more than one level"
            )
        if key in parent:
            raise YamlSubsetError(f"line {line_number}: duplicate key {key!r}")

        parsed = _scalar(raw_value)
        if parsed is None and raw_value.strip() == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = parsed

    return root


def load(path) -> dict[str, Any]:
    return loads(path.read_text(encoding="utf-8"))
