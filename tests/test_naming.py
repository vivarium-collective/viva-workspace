"""Tests for package naming and the viva_/pbg_ compat shim."""
from __future__ import annotations

from viva_workspace import legacy_package_slug, package_slug, resolve_package_dir


def test_canonical_viva_prefix():
    assert package_slug("my-workspace") == "viva_my_workspace"
    assert package_slug(None) == "viva_workspace"
    assert package_slug("") == "viva_workspace"


def test_legacy_slug():
    assert legacy_package_slug("my-workspace") == "pbg_my_workspace"


def test_resolve_prefers_canonical(tmp_path):
    (tmp_path / "viva_demo").mkdir()
    (tmp_path / "pbg_demo").mkdir()
    assert resolve_package_dir(tmp_path, "demo") == tmp_path / "viva_demo"


def test_resolve_falls_back_to_legacy_pbg(tmp_path):
    (tmp_path / "pbg_demo").mkdir()
    assert resolve_package_dir(tmp_path, "demo") == tmp_path / "pbg_demo"


def test_resolve_defaults_to_canonical_when_neither_exists(tmp_path):
    assert resolve_package_dir(tmp_path, "demo") == tmp_path / "viva_demo"
