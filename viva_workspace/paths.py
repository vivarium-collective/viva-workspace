"""Canonical resolution of a workspace's directory layout.

Single source of truth for the ``layout:`` map in ``workspace.yaml`` and the
derived well-known directories (``studies/``, ``investigations/``, ``reports/``,
the Python package, ...). Consolidated from three divergent implementations that
this package replaces:

* ``vivarium-workbench`` ``vivarium_workbench/lib/workspace_paths.py`` — the
  fullest ``WorkspacePaths`` (mtime-memoized ``load``, layout map, ~231 lines).
  This is the canonical base.
* ``viva-superpowers`` ``viva_superpowers/workspace_paths.py`` — a hand-synced
  vendored copy. Its ``LAYOUT_DEFAULTS`` had drifted to include ``notes`` and
  ``experiments`` keys not present in the workbench copy, and it dropped the
  mtime memo. Reconciled here by taking the UNION of layout keys and keeping the
  memoized ``load``.
* ``v2ecoli`` — the layout-map-aware ``_studies_root()`` /
  ``study_dir`` in ``v2ecoli/composites/ecoli_structural.py`` (reads
  ``layout.studies``) and the hardcoded ``ws/"workspace"/"studies"/slug``
  literals in ``v2ecoli/library/parquet_viz.py`` + ``workflow/*``. Those
  hardcoded literals are exactly what the layout-map-driven :func:`study_dir`
  below replaces.

Backward compatibility: a key left out of ``layout:`` falls back to the
conventional flat name (``studies`` -> ``studies/``). A workspace with no
``layout:`` block at all therefore keeps the classic flat layout, so existing
workspaces are unaffected.

Example ``workspace.yaml`` nesting research dirs under ``workspace/``::

    layout:
      studies: workspace/studies
      investigations: workspace/investigations
      composites: workspace/composites
      references: workspace/references
      datasets: workspace/datasets
      reports: workspace/reports
      pbg: workspace/.pbg
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping, Optional, Union

import yaml

from .naming import package_slug

# The canonical flat layout — the single source of truth for directory names.
# Keys are logical names used throughout the codebase; values are the default
# workspace-root-relative paths. The Python package (`package`) is special: it
# derives from `package_path`/`name` in workspace.yaml, so it has no fixed
# default here.
#
# Drift reconciliation: `notes` and `experiments` came from the viva-superpowers
# vendored copy; the rest match vivarium-workbench. The union is safe because an
# unused key simply resolves to a directory nothing reads.
LAYOUT_DEFAULTS: dict[str, str] = {
    "studies": "studies",
    "investigations": "investigations",
    "composites": "composites",
    "references": "references",
    "datasets": "datasets",
    "notes": "notes",
    "experiments": "experiments",
    "reports": "reports",
    "pbg": ".pbg",
    "scripts": "scripts",
    "tests": "tests",
    "docs": "docs",
}

# Logical names a workspace may override via `layout:` (`package` is normally
# set through `package_path`, but may also be relocated via `layout`).
LAYOUT_KEYS = tuple(LAYOUT_DEFAULTS) + ("package",)


# mtime-keyed memo for ``WorkspacePaths.load``. ``load`` was called ~126 times
# across the dashboard, each re-``stat``ing, re-reading and re-parsing
# ``workspace.yaml``. The layout rarely changes within a process lifetime, so we
# cache the resolved ``WorkspacePaths`` keyed by resolved root, tagged with the
# ``workspace.yaml`` mtime (ns). A cached entry is reused only while that mtime
# is unchanged; any edit (or create/delete) changes the tag and forces a
# re-parse, so the cache stays correct. Not locked: a benign race just re-parses.
# ``_parse_count`` is a test hook incremented on each real parse.
_LOAD_CACHE: dict[str, tuple[Optional[int], "WorkspacePaths"]] = {}
_parse_count = 0


def _clear_load_cache() -> None:
    """Drop the ``WorkspacePaths.load`` memo (test/utility helper)."""
    _LOAD_CACHE.clear()


def find_workspace_root(start: Union[Path, str, None] = None) -> Path:
    """Walk up from ``start`` (default CWD) to the nearest ancestor holding a
    ``workspace.yaml``; return that directory.

    The single root-walker consolidating ``vivarium_workbench.lib._root``'s
    CWD-fallback loop and the copy-pasted ``_find_workspace_root`` in
    ``v2ecoli/library/parquet_viz.py`` (and siblings). Raises ``FileNotFoundError``
    if no workspace root is found.
    """
    here = Path(start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "workspace.yaml").is_file():
            return candidate
    raise FileNotFoundError(
        f"no workspace.yaml found walking up from {here}"
    )


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved directory layout for a single workspace.

    Construct via :meth:`load` (reads ``workspace.yaml``) or :meth:`from_config`
    (caller supplies the parsed dict). Access directories by attribute
    (``wp.studies``) or by name (``wp.dir("studies")``). Subpaths are formed by
    joining onto the result, e.g. ``wp.pbg / "schemas"`` or
    ``wp.reports / "figures" / study``.
    """

    root: Path
    _layout: Mapping[str, str]

    @classmethod
    def from_config(
        cls, root: Union[Path, str], config: Optional[Mapping] = None
    ) -> "WorkspacePaths":
        config = dict(config or {})
        layout = dict(LAYOUT_DEFAULTS)
        # Package directory: explicit package_path wins, else derive from name.
        layout["package"] = config.get("package_path") or package_slug(config.get("name"))
        # Apply explicit per-directory overrides.
        overrides = config.get("layout") or {}
        for key, value in overrides.items():
            if key in LAYOUT_KEYS and isinstance(value, str) and value:
                layout[key] = value
        return cls(Path(root).resolve(), layout)

    @classmethod
    def load(cls, root: Union[Path, str]) -> "WorkspacePaths":
        """Resolve layout from ``<root>/workspace.yaml`` (empty if missing).

        Memoized by resolved root + ``workspace.yaml`` mtime: a repeated load
        with an unchanged file returns the cached instance without re-parsing;
        a changed (or newly created/deleted) file invalidates the entry.
        """
        root = Path(root)
        resolved = str(root.resolve())
        wf = root / "workspace.yaml"
        try:
            mtime: Optional[int] = wf.stat().st_mtime_ns
        except OSError:
            # Missing/unreadable workspace.yaml -> empty config. Tag None so a
            # later creation (mtime becomes an int) invalidates the entry.
            mtime = None
        cached = _LOAD_CACHE.get(resolved)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        config: dict = {}
        if mtime is not None:
            config = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
            global _parse_count
            _parse_count += 1
        wp = cls.from_config(root, config)
        _LOAD_CACHE[resolved] = (mtime, wp)
        return wp

    def dir(self, name: str) -> Path:
        """Absolute path to the directory registered under logical ``name``."""
        if name not in self._layout:
            raise KeyError(f"unknown workspace directory: {name!r}")
        return self.root / self._layout[name]

    def rel(self, name: str) -> str:
        """Workspace-root-relative path string for logical ``name``."""
        return self._layout[name]

    # Convenience accessors -------------------------------------------------
    @property
    def studies(self) -> Path: return self.dir("studies")
    @property
    def investigations(self) -> Path: return self.dir("investigations")
    @property
    def composites(self) -> Path: return self.dir("composites")
    @property
    def references(self) -> Path: return self.dir("references")
    @property
    def datasets(self) -> Path: return self.dir("datasets")
    @property
    def notes(self) -> Path: return self.dir("notes")
    @property
    def experiments(self) -> Path: return self.dir("experiments")
    @property
    def reports(self) -> Path: return self.dir("reports")
    @property
    def pbg(self) -> Path: return self.dir("pbg")
    @property
    def scripts(self) -> Path: return self.dir("scripts")
    @property
    def tests(self) -> Path: return self.dir("tests")
    @property
    def docs(self) -> Path: return self.dir("docs")
    @property
    def package(self) -> Path: return self.dir("package")

    # Study resolution (investigation-centric structure) --------------------
    def iter_study_dirs(self) -> Iterator[Path]:
        """Yield every study dir. Flat ``studies/<slug>/`` FIRST (so a top-level
        study wins on a slug collision and is never shadowed by a nested copy),
        then nested ``investigations/<inv>/studies/<slug>/`` for any slug not
        already yielded. A dir is a study iff it holds ``study.yaml``. Both roots
        are resolved via the layout map (never hardcoded literals)."""
        seen: set[str] = set()
        flat = self.dir("studies")
        if flat.is_dir():
            for s in sorted(p for p in flat.iterdir() if p.is_dir()):
                if (s / "study.yaml").is_file() and s.name not in seen:
                    seen.add(s.name)
                    yield s
        inv_root = self.dir("investigations")
        if inv_root.is_dir():
            for inv in sorted(p for p in inv_root.iterdir() if p.is_dir()):
                sroot = inv / "studies"
                if sroot.is_dir():
                    for s in sorted(p for p in sroot.iterdir() if p.is_dir()):
                        if (s / "study.yaml").is_file() and s.name not in seen:
                            seen.add(s.name)
                            yield s

    def study_dir(self, slug: str, must_exist: bool = False) -> Path:
        """Resolve a study by slug, honoring the layout map.

        Searches existing studies flat-first then nested (see
        :meth:`iter_study_dirs`) and returns the found dir. If the slug does not
        exist yet and ``must_exist`` is False (default), returns the CANONICAL
        location it would occupy — ``self.studies / slug`` — so callers writing a
        new study land in the layout-map-driven location. With ``must_exist=True``
        an absent slug raises ``FileNotFoundError`` (the old workbench semantics).

        This unifies two divergent behaviours: the workbench/superpowers resolver
        was a lookup that RAISED when absent, while v2ecoli's ``study_dir`` /
        ``_studies_root`` DERIVED an output path (``layout.studies/<slug>``) for a
        study that may not exist yet. ``must_exist`` selects between them.
        """
        for s in self.iter_study_dirs():
            if s.name == slug:
                return s
        if must_exist:
            raise FileNotFoundError(f"study {slug!r} not found under {self.root}")
        return self.studies / slug

    def report_dir(self, inv_slug: str) -> Path:
        """Per-investigation report/publication dir: investigations/<slug>/reports/."""
        return self.dir("investigations") / inv_slug / "reports"

    def inputs_dir(self, inv_slug: str) -> Path:
        """investigations/<inv_slug>/inputs (per-investigation owned inputs)."""
        return self.dir("investigations") / inv_slug / "inputs"

    def study_owner(self, slug: str) -> Optional[str]:
        """Owning investigation slug for a study: nested layout wins, else the
        study.yaml ``investigation:`` back-ref, else None.

        (The workbench's extra forward-list fallback scanned each
        ``investigation.yaml``'s ``studies:`` list via
        ``investigation_member_slugs`` — dropped here to keep this package free of
        the vivarium-workbench dependency. Consumers needing it can layer it on.)
        """
        try:
            d = self.study_dir(slug, must_exist=True)
        except FileNotFoundError:
            return None
        try:
            parts = d.relative_to(self.dir("investigations")).parts
            if len(parts) >= 3 and parts[1] == "studies":
                return parts[0]
        except ValueError:
            pass
        sy = d / "study.yaml"
        if sy.is_file():
            data = yaml.safe_load(sy.read_text(encoding="utf-8")) or {}
            return data.get("investigation")
        return None


def study_dir(
    root_or_paths: Union["WorkspacePaths", Path, str],
    slug: str,
    must_exist: bool = False,
) -> Path:
    """Layout-map-aware study directory resolver — the ONE resolver replacing the
    ~12 study-dir resolvers scattered across the three repos (including the
    hardcoded ``ws/"workspace"/"studies"/slug`` literals in v2ecoli).

    Accepts either a :class:`WorkspacePaths` or a workspace root (Path/str; loaded
    via :meth:`WorkspacePaths.load`). Delegates to :meth:`WorkspacePaths.study_dir`,
    so it honors ``layout.studies`` (nested ``workspace/studies`` vs legacy flat
    ``studies``) with no hardcoded literal, searches nested + flat, and — unless
    ``must_exist`` — returns the canonical write location for a not-yet-created
    study.
    """
    paths = root_or_paths if isinstance(root_or_paths, WorkspacePaths) \
        else WorkspacePaths.load(root_or_paths)
    return paths.study_dir(slug, must_exist=must_exist)
