#!/usr/bin/env python3
"""Compatibility entry point for the canonical Rayesh acceptance policy."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rayesh_runtime.acceptance import (  # noqa: F401
    Criterion,
    GAP_ORDER,
    GAP_ROUTES,
    Iteration,
    ScopeState,
    evaluate,
    progress_guard,
    promote_child_evidence,
    select_gap,
)
