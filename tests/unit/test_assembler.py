from __future__ import annotations

import json
from pathlib import Path

from vv_ros_llm.vv.assembler import NODE_FILE, RUN_SCRIPT, write_candidate_workspace


def test_writes_core_files(tmp_path):
    write_candidate_workspace(
        tmp_path,
        candidate_code="print('hi')",
        entry_point="MyNode",
        interface_spec={"node_name": "n"},
        test_oracle={"checks": []},
    )
    assert (tmp_path / NODE_FILE).read_text() == "print('hi')"
    oracle_json = json.loads((tmp_path / "oracle.json").read_text())
    assert oracle_json == {"checks": []}
    iface = json.loads((tmp_path / "interface_spec.json").read_text())
    assert iface["node_name"] == "n"
    assert RUN_SCRIPT in [p.name for p in tmp_path.iterdir()]


def test_writes_extras(tmp_path):
    write_candidate_workspace(
        tmp_path,
        candidate_code="",
        entry_point="N",
        interface_spec={},
        test_oracle={},
        extras={"tests/extra.py": "# hello", "README.md": "doc"},
    )
    assert (tmp_path / "tests" / "extra.py").read_text() == "# hello"
    assert (tmp_path / "README.md").read_text() == "doc"


def test_writes_non_serializable_fields_via_default_str(tmp_path):
    write_candidate_workspace(
        tmp_path,
        candidate_code="",
        entry_point="N",
        interface_spec={"maybe_path": Path("/tmp/x")},
        test_oracle={"checks": []},
    )
    iface = json.loads((tmp_path / "interface_spec.json").read_text())
    assert "maybe_path" in iface
    assert isinstance(iface["maybe_path"], str)
