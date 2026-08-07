"""Canonical-run outcome selection — the LOCKED semantics for which of a study's
recorded runs is authoritative.

Ported verbatim (minus the reconciliation/DB-writing machinery, which stays in
vivarium-workbench / viva-superpowers) from
``viva_superpowers/study_outcomes.py::canonical_run`` / ``canonical_outcomes``.

The rule, in priority order:

1. A run explicitly flagged ``canonical: true`` wins (last such run, if several).
2. Otherwise the newest COMPLETED run by ``timestamp``.
3. Otherwise the last run in the list.
4. Otherwise ``None`` / ``{}``.

This is deliberately NOT a last-run-wins merge across runs: :func:`canonical_outcomes`
returns exactly ONE run's ``outcomes`` dict, so an older ``canonical: true`` run
correctly overrides a newer completed run.
"""
from __future__ import annotations

from typing import Optional, Union

# Status strings that count as a completed run.
_COMPLETE = {"complete", "completed", "ran", "done"}

# A study spec (dict with a "runs" list) or a bare runs list.
SpecOrRuns = Union[dict, list, None]


def _runs_of(spec_or_runs: SpecOrRuns) -> list[dict]:
    if isinstance(spec_or_runs, list):
        runs = spec_or_runs
    else:
        runs = (spec_or_runs or {}).get("runs") or []
    return [r for r in runs if isinstance(r, dict)]


def canonical_run(spec_or_runs: SpecOrRuns) -> Optional[dict]:
    """The run whose outcomes are authoritative: an explicit ``canonical: true``
    (last one wins), else the newest completed run by ``timestamp``, else the last
    run, else ``None``."""
    runs = _runs_of(spec_or_runs)
    if not runs:
        return None
    flagged = [r for r in runs if r.get("canonical") is True]
    if flagged:
        return flagged[-1]
    completed = [r for r in runs if str(r.get("status", "")).lower() in _COMPLETE]
    if completed:
        return max(completed, key=lambda r: r.get("timestamp") or "")
    return runs[-1]


def canonical_outcomes(spec_or_runs: SpecOrRuns) -> dict:
    """The canonical run's ``outcomes`` dict (empty if none)."""
    run = canonical_run(spec_or_runs)
    return (run or {}).get("outcomes") or {}
