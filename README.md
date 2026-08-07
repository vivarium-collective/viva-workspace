# viva-workspace

The single **source of truth for workspace-layout logic** shared by
`vivarium-workbench`, `viva-superpowers`, and `v2ecoli`.

Before this package those three repos each reimplemented the same concepts —
~12 study-directory resolvers, ~6 root-walkers, and a hand-synced *vendored* copy
of `workspace_paths.py` — with three subtly conflicting semantics. This package
consolidates them into one dependency-light module so the layout is defined once.

## Why dependency-light

`vivarium-workbench` is deliberately **AI-free** (all AI lives in
`viva-superpowers`). To be safe for the workbench to depend on, this package uses
**stdlib + `pyyaml` only** — no `process_bigraph` / `bigraph_schema`, no web
framework, no AI deps.

## Public API

```python
from viva_workspace import (
    WorkspacePaths,        # load workspace.yaml (mtime-memoized) + derived dirs
    find_workspace_root,   # the one root-walker (walk up for workspace.yaml)
    study_dir,             # ONE layout-map-aware study resolver (nested + flat)
    canonical_outcomes,    # the LOCKED canonical-run outcome selection
    package_slug,          # canonical viva_<slug> (with pbg_<slug> compat shim)
)
```

### Layout map

`WorkspacePaths` reads an optional `layout:` map from `workspace.yaml`. A missing
key falls back to the flat default (`studies` -> `studies/`); a workspace with no
`layout:` block keeps the classic flat layout. To nest research dirs:

```yaml
layout:
  studies: workspace/studies
  investigations: workspace/investigations
  reports: workspace/reports
```

`study_dir(root_or_paths, slug)` honors that map for both nested
(`workspace/studies/<slug>`) and flat (`studies/<slug>`) layouts with no hardcoded
literal, searching flat-first then nested, and returning the canonical write
location for a not-yet-created study (pass `must_exist=True` to require existence).

### Canonical outcomes

`canonical_outcomes(study_spec)` returns exactly ONE run's `outcomes`: the run
flagged `canonical: true` if any (last wins), else the newest **completed** run by
timestamp, else the last run. It is *not* a last-run-wins merge — an older
`canonical: true` run correctly overrides a newer completed one.

### Package naming

`package_slug(name)` returns the canonical `viva_<slug>`. During the pbg -> viva
migration window, `resolve_package_dir(root, name)` returns an existing
`pbg_<slug>/` directory if the canonical `viva_<slug>/` is absent.

## Status

Local-only. Not yet published; consumers still ship their own copies until this is
released and they migrate.
