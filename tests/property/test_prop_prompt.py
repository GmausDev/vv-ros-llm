from __future__ import annotations
from hypothesis import given, settings, strategies as st
from vv_ros_llm.llm.prompt_template import PromptBuilder, extract_python_code

_pb = PromptBuilder()

@settings(max_examples=50, deadline=None)
@given(description=st.text(min_size=0, max_size=200))
def test_render_never_raises_on_arbitrary_text(description):
    task = {"task_id": "T1", "prompt": description, "entry_point": "N",
             "interface_spec": {"node_name": "n"}, "node_type": "publisher",
             "difficulty": "Easy", "ros_concepts": []}
    out = _pb.render(task)
    assert isinstance(out, str) and len(out) > 0

@settings(max_examples=50, deadline=None)
@given(text=st.text(min_size=0, max_size=400))
def test_extract_returns_str(text):
    assert isinstance(extract_python_code(text), str)
