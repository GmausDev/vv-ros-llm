from __future__ import annotations

import textwrap
from pathlib import Path

KNOWN_TYPES = {
    "node_exists",
    "topic_published",
    "topic_subscribed",
    "message_content",
    "log_output_contains",
    "service_called",
    "parameter_value",
}

_TEST_TEMPLATE = '''
import json
import importlib.util
import pathlib

import pytest

SPEC = json.loads(pathlib.Path("/workspace/oracle.json").read_text())
CHECKS = SPEC.get("checks", [])


def _import_candidate():
    spec = importlib.util.spec_from_file_location(
        "candidate_node", "/workspace/candidate_node.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def candidate_module():
    return _import_candidate()


@pytest.mark.parametrize(
    "check", CHECKS, ids=[c.get("type", "?") for c in CHECKS]
)
def test_oracle_check(candidate_module, check):
    t = check.get("type", "")
    if t == "node_exists":
        assert check.get("node_name"), "node_name required"
    elif t == "topic_published":
        assert check.get("topic"), "topic required"
    elif t == "topic_subscribed":
        assert check.get("topic"), "topic required"
    elif t == "message_content":
        assert check.get("topic") and check.get("field"), "topic+field required"
    elif t == "log_output_contains":
        assert check.get("pattern"), "pattern required"
    elif t == "service_called":
        assert check.get("service"), "service required"
    elif t == "parameter_value":
        assert check.get("node") and check.get("parameter"), "node+parameter required"
    else:
        pytest.xfail(f"oracle check type {t!r} not implemented in MVP")
'''


def write_oracle_tests(workspace: Path) -> Path:
    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    path = tests_dir / "test_oracle.py"
    path.write_text(textwrap.dedent(_TEST_TEMPLATE), encoding="utf-8")
    return path
