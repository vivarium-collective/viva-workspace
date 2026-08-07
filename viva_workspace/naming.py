"""Workspace Python-package naming — the LOCKED ``viva_<slug>`` decision plus a
``pbg_<slug>`` legacy compat shim.

Consolidates the ``package_slug`` helper that both
``vivarium_workbench/lib/workspace_paths.py`` and
``viva_superpowers/workspace_paths.py`` defined identically as
``f"pbg_{slug}"``. As part of the pbg -> viva rebrand the canonical prefix is
now ``viva_``; :func:`package_slug` returns that. Existing workspaces still ship
a ``pbg_<slug>/`` package directory, so :func:`resolve_package_dir` recognizes an
on-disk ``pbg_<slug>`` during the migration window instead of silently pointing
at a non-existent ``viva_<slug>``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


def _slugify(name: Optional[str]) -> str:
    return (name or "workspace").replace("-", "_")


def package_slug(name: Optional[str]) -> str:
    """Canonical Python package directory name for a workspace named ``name``.

    LOCKED decision: standardize on ``viva_<slug>`` (was ``pbg_<slug>`` before the
    rebrand). ``None``/empty -> ``viva_workspace``; hyphens become underscores.
    """
    return f"viva_{_slugify(name)}"


def legacy_package_slug(name: Optional[str]) -> str:
    """The pre-rebrand ``pbg_<slug>`` package name, for compat recognition."""
    return f"pbg_{_slugify(name)}"


def resolve_package_dir(root: Union[Path, str], name: Optional[str]) -> Path:
    """Absolute package directory for a workspace, honoring the migration window.

    Returns ``<root>/viva_<slug>`` (canonical) UNLESS that directory is absent and
    a legacy ``<root>/pbg_<slug>`` directory exists on disk, in which case the
    existing ``pbg_<slug>`` path is returned so a not-yet-migrated workspace keeps
    resolving to its real package. Once ``viva_<slug>`` exists it always wins,
    even if a stale ``pbg_<slug>`` also lingers.
    """
    root = Path(root)
    canonical = root / package_slug(name)
    if canonical.is_dir():
        return canonical
    legacy = root / legacy_package_slug(name)
    if legacy.is_dir():
        return legacy
    return canonical
