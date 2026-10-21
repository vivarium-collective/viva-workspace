import json
import pytest
from viva_workspace.workspace_yaml import (
    WorkspaceValidationError, validate_workspace, load_workspace, save_workspace)

_SCHEMA = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}

def _schema(tmp_path):
    p = tmp_path / "workspace.schema.json"; p.write_text(json.dumps(_SCHEMA)); return p

def test_validate_ok_and_fail(tmp_path):
    sp = _schema(tmp_path)
    validate_workspace({"name": "ws"}, sp)
    with pytest.raises(WorkspaceValidationError):
        validate_workspace({}, sp)

def test_load_roundtrip(tmp_path):
    sp = _schema(tmp_path); wp = tmp_path / "workspace.yaml"; wp.write_text("name: demo\n")
    assert load_workspace(wp, sp) == {"name": "demo"}

def test_save_preserves_unicode(tmp_path):
    sp = _schema(tmp_path); wp = tmp_path / "workspace.yaml"
    save_workspace(wp, {"name": "café-µ"}, sp)
    text = wp.read_text(encoding="utf-8")
    assert "café-µ" in text and "\\u" not in text   # allow_unicode=True

def test_save_validates_before_write(tmp_path):
    sp = _schema(tmp_path); wp = tmp_path / "w.yaml"
    with pytest.raises(WorkspaceValidationError):
        save_workspace(wp, {}, sp)
    assert not wp.exists()
