"""Tests for the layout map, root-walker, study_dir, and mtime memo."""
from __future__ import annotations

import os

import pytest

from viva_workspace import WorkspacePaths, find_workspace_root, study_dir
from viva_workspace import paths as paths_mod


@pytest.fixture(autouse=True)
def _clear_cache():
    paths_mod._clear_load_cache()
    yield
    paths_mod._clear_load_cache()


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


# --- study_dir: flat vs nested via the layout map --------------------------

def test_study_dir_flat_layout(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    _write(tmp_path / "studies" / "s1" / "study.yaml", "name: s1\n")
    d = study_dir(tmp_path, "s1")
    assert d == (tmp_path / "studies" / "s1").resolve()


def test_study_dir_nested_layout_via_map(tmp_path):
    _write(tmp_path / "workspace.yaml", "layout:\n  studies: workspace/studies\n")
    _write(tmp_path / "workspace" / "studies" / "s1" / "study.yaml", "name: s1\n")
    d = study_dir(tmp_path, "s1")
    assert d == (tmp_path / "workspace" / "studies" / "s1").resolve()


def test_study_dir_nested_under_investigation(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    _write(
        tmp_path / "investigations" / "inv1" / "studies" / "s2" / "study.yaml",
        "name: s2\n",
    )
    d = study_dir(tmp_path, "s2")
    assert d == (tmp_path / "investigations" / "inv1" / "studies" / "s2").resolve()
    # owner derived from nested layout
    wp = WorkspacePaths.load(tmp_path)
    assert wp.study_owner("s2") == "inv1"


def test_study_dir_missing_returns_canonical_write_location(tmp_path):
    _write(tmp_path / "workspace.yaml", "layout:\n  studies: workspace/studies\n")
    d = study_dir(tmp_path, "newstudy")
    assert d == (tmp_path / "workspace" / "studies" / "newstudy").resolve()


def test_study_dir_must_exist_raises(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    with pytest.raises(FileNotFoundError):
        study_dir(tmp_path, "nope", must_exist=True)


def test_study_dir_accepts_workspacepaths(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    _write(tmp_path / "studies" / "s1" / "study.yaml", "name: s1\n")
    wp = WorkspacePaths.load(tmp_path)
    assert study_dir(wp, "s1") == (tmp_path / "studies" / "s1").resolve()


def test_flat_wins_over_nested_on_collision(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    _write(tmp_path / "studies" / "dup" / "study.yaml", "name: dup\n")
    _write(
        tmp_path / "investigations" / "inv1" / "studies" / "dup" / "study.yaml",
        "name: dup\n",
    )
    assert study_dir(tmp_path, "dup") == (tmp_path / "studies" / "dup").resolve()


# --- find_workspace_root ---------------------------------------------------

def test_root_walk_from_nested_dir(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    deep = tmp_path / "investigations" / "inv1" / "studies" / "s1"
    deep.mkdir(parents=True)
    assert find_workspace_root(deep) == tmp_path.resolve()


def test_root_walk_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_workspace_root(tmp_path)


def test_root_walk_default_cwd(tmp_path, monkeypatch):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    assert find_workspace_root() == tmp_path.resolve()


# --- layout defaults / drift reconciliation --------------------------------

def test_layout_defaults_include_reconciled_keys():
    wp = WorkspacePaths.from_config("/tmp/x", {})
    # union of workbench + superpowers vendored keys
    for key in ("studies", "reports", "pbg", "notes", "experiments"):
        assert wp.dir(key) is not None


def test_package_dir_from_name_and_package_path(tmp_path):
    wp = WorkspacePaths.from_config(tmp_path, {"name": "my-thing"})
    assert wp.package.name == "viva_my_thing"
    wp2 = WorkspacePaths.from_config(tmp_path, {"package_path": "custom_pkg"})
    assert wp2.package.name == "custom_pkg"


# --- mtime memoization -----------------------------------------------------

def test_mtime_memo_no_reparse_when_unchanged(tmp_path):
    _write(tmp_path / "workspace.yaml", "name: demo\n")
    start = paths_mod._parse_count
    WorkspacePaths.load(tmp_path)
    after_first = paths_mod._parse_count
    assert after_first == start + 1
    for _ in range(5):
        WorkspacePaths.load(tmp_path)
    assert paths_mod._parse_count == after_first  # no re-parse


def test_mtime_memo_reparse_on_change(tmp_path):
    wf = tmp_path / "workspace.yaml"
    _write(wf, "name: demo\n")
    WorkspacePaths.load(tmp_path)
    base = paths_mod._parse_count
    # bump mtime to a distinct value and change content
    _write(wf, "layout:\n  studies: workspace/studies\n")
    os.utime(wf, ns=(base + 10**9, base + 10**9))
    wp = WorkspacePaths.load(tmp_path)
    assert paths_mod._parse_count == base + 1  # re-parsed
    assert wp.rel("studies") == "workspace/studies"
