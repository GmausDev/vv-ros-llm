from __future__ import annotations
import pytest

from vv_ros_llm.vv.base import MethodContext
from vv_ros_llm.vv.hypothesis_runner import HypothesisRunner
from vv_ros_llm.vv.z3_checks import Z3Checks

@pytest.mark.asyncio
async def test_hypothesis_and_z3_on_clean_spec(tmp_path):
    iface = {
        "node_name": "n",
        "topics_published": [{"name": "/a", "type": "std_msgs/Int32"}],
        "topics_subscribed": [{"name": "/b", "type": "std_msgs/String"}],
    }
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="",
                        entry_point="N", interface_spec=iface, test_oracle={"checks": []},
                        workspace=tmp_path)
    h = await HypothesisRunner().run(ctx)
    z = await Z3Checks().run(ctx)
    assert h.passed and z.passed

@pytest.mark.asyncio
async def test_hypothesis_catches_duplicate_topics(tmp_path):
    iface = {
        "node_name": "n",
        "topics_published": [
            {"name": "/a", "type": "std_msgs/Int32"},
            {"name": "/a", "type": "std_msgs/Int32"},
        ],
        "topics_subscribed": [],
    }
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="",
                        entry_point="N", interface_spec=iface, test_oracle={"checks": []},
                        workspace=tmp_path)
    h = await HypothesisRunner().run(ctx)
    assert not h.passed
    assert any("duplicate" in str(f).lower() for f in h.findings)

@pytest.mark.asyncio
async def test_z3_catches_bad_qos_depth(tmp_path):
    iface = {
        "node_name": "n",
        "topics_published": [{"name": "/a", "type": "std_msgs/Int32", "qos": {"depth": 0}}],
        "topics_subscribed": [],
    }
    ctx = MethodContext(task_id="T", candidate_idx=0, candidate_code="",
                        entry_point="N", interface_spec=iface, test_oracle={"checks": []},
                        workspace=tmp_path)
    z = await Z3Checks().run(ctx)
    assert not z.passed
