from __future__ import annotations

from vv_ros_llm.vv.oracle_runner import KNOWN_TYPES, write_oracle_tests


def test_write_oracle_tests_creates_file(tmp_path):
    p = write_oracle_tests(tmp_path)
    assert p.exists()
    assert p.name == "test_oracle.py"
    assert (tmp_path / "tests").is_dir()


def test_oracle_test_file_contains_type_dispatch(tmp_path):
    p = write_oracle_tests(tmp_path)
    body = p.read_text(encoding="utf-8")
    for t in (
        "node_exists",
        "topic_published",
        "topic_subscribed",
        "message_content",
        "log_output_contains",
        "service_called",
        "parameter_value",
    ):
        assert t in body, f"missing dispatch branch for {t}"


def test_known_types_matches_dispatch():
    assert {
        "node_exists",
        "topic_published",
        "topic_subscribed",
        "message_content",
        "log_output_contains",
        "service_called",
        "parameter_value",
    } <= KNOWN_TYPES
