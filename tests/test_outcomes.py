"""Tests for canonical-run outcome selection."""
from __future__ import annotations

from viva_workspace import canonical_outcomes, canonical_run


def test_canonical_flag_beats_newer_completed():
    spec = {
        "runs": [
            {
                "name": "old-canonical",
                "status": "completed",
                "timestamp": "2024-01-01",
                "canonical": True,
                "outcomes": {"PASS": True},
            },
            {
                "name": "newer-completed",
                "status": "completed",
                "timestamp": "2025-01-01",
                "outcomes": {"PASS": False},
            },
        ]
    }
    assert canonical_run(spec)["name"] == "old-canonical"
    assert canonical_outcomes(spec) == {"PASS": True}


def test_newest_completed_when_no_flag():
    spec = {
        "runs": [
            {"name": "a", "status": "completed", "timestamp": "2024-01-01",
             "outcomes": {"v": 1}},
            {"name": "b", "status": "completed", "timestamp": "2025-06-01",
             "outcomes": {"v": 2}},
            {"name": "c", "status": "running", "timestamp": "2025-12-01",
             "outcomes": {"v": 3}},
        ]
    }
    assert canonical_run(spec)["name"] == "b"
    assert canonical_outcomes(spec) == {"v": 2}


def test_last_canonical_flag_wins():
    spec = {
        "runs": [
            {"name": "c1", "canonical": True, "outcomes": {"n": 1}},
            {"name": "c2", "canonical": True, "outcomes": {"n": 2}},
        ]
    }
    assert canonical_run(spec)["name"] == "c2"


def test_falls_back_to_last_run_when_none_completed():
    spec = {"runs": [
        {"name": "a", "status": "running", "outcomes": {"x": 1}},
        {"name": "b", "status": "queued", "outcomes": {"x": 2}},
    ]}
    assert canonical_run(spec)["name"] == "b"


def test_empty():
    assert canonical_run({"runs": []}) is None
    assert canonical_outcomes({}) == {}
    assert canonical_outcomes(None) == {}


def test_accepts_bare_runs_list():
    runs = [{"name": "a", "status": "done", "timestamp": "2025-01-01",
             "outcomes": {"ok": True}}]
    assert canonical_outcomes(runs) == {"ok": True}
