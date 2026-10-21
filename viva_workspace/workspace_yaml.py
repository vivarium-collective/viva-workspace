"""Read, write, and validate a ``workspace.yaml`` against a workspace schema.

Shared by vivarium-workbench and viva-superpowers, which previously each carried
a byte-identical copy of this logic differing only in (a) WHERE the
``workspace.schema.json`` lives — the workbench resolves it from the live
workspace's ``.pbg/schemas/``, the plugin uses a bundled copy — and (b) a drift
bug (the plugin's writer dropped ``allow_unicode``, escaping non-ASCII). So the
schema path is a parameter here, each caller passes its own, and the writer
always preserves unicode. Each repo keeps a thin wrapper that supplies its own
``schema_path`` so existing call sites are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft7Validator, FormatChecker, ValidationError


class WorkspaceValidationError(Exception):
    """Raised when workspace.yaml does not conform to the schema."""


def _validator(schema_path: Path | str) -> Draft7Validator:
    return Draft7Validator(
        json.loads(Path(schema_path).read_text(encoding="utf-8")),
        format_checker=FormatChecker(),
    )


def validate_workspace(data: dict, schema_path: Path | str) -> None:
    try:
        _validator(schema_path).validate(data)
    except ValidationError as e:
        raise WorkspaceValidationError(str(e)) from e


def load_workspace(path: Path | str, schema_path: Path | str) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    validate_workspace(data, schema_path)
    return data


def save_workspace(path: Path | str, data: dict, schema_path: Path | str) -> None:
    validate_workspace(data, schema_path)
    Path(path).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
