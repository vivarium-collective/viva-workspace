"""viva-workspace — the shared source of truth for workspace-layout logic.

One dependency-light (stdlib + pyyaml) package consolidating the workspace-layout
helpers that vivarium-workbench, viva-superpowers and v2ecoli each reimplemented:
the ``layout:`` map + derived directories (:class:`WorkspacePaths`), the
root-walker (:func:`find_workspace_root`), the single layout-aware study
resolver (:func:`study_dir`), canonical-run outcome selection
(:func:`canonical_outcomes`) and package naming (:func:`package_slug`).

Deliberately free of AI / process_bigraph / web-framework deps so the AI-free
workbench can depend on it safely.
"""
from __future__ import annotations

from .naming import (
    legacy_package_slug,
    package_slug,
    resolve_package_dir,
)
from .outcomes import canonical_outcomes, canonical_run
from .paths import (
    LAYOUT_DEFAULTS,
    LAYOUT_KEYS,
    WorkspacePaths,
    find_workspace_root,
    study_dir,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "WorkspacePaths",
    "LAYOUT_DEFAULTS",
    "LAYOUT_KEYS",
    "find_workspace_root",
    "study_dir",
    "canonical_outcomes",
    "canonical_run",
    "package_slug",
    "legacy_package_slug",
    "resolve_package_dir",
]
