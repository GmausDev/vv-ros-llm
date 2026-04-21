from __future__ import annotations
from vv_ros_llm.llm.prompt_template import PromptBuilder, extract_python_code

def test_extract_python_code_finds_fenced_block():
    txt = "prose\n```python\nx = 1\n```\nmore"
    assert extract_python_code(txt) == "x = 1"

def test_extract_python_code_handles_py_alias():
    txt = "```py\nprint('hi')\n```"
    assert extract_python_code(txt) == "print('hi')"

def test_extract_python_code_raw_fallback():
    txt = "no fences, just code\nprint(1)"
    assert "print(1)" in extract_python_code(txt)

def test_prompt_builder_renders_minimal_task():
    pb = PromptBuilder()
    task = {"task_id": "T1", "prompt": "def body(): ...", "entry_point": "MyNode",
             "interface_spec": {"node_name": "n1"}, "node_type": "publisher",
             "difficulty": "Easy", "ros_concepts": ["publisher"]}
    out = pb.render(task)
    assert "T1" in out and "MyNode" in out and "publisher" in out

def test_prompt_builder_unicode_safe():
    pb = PromptBuilder()
    task = {"task_id": "Tñ", "prompt": "# café", "entry_point": "N",
             "interface_spec": {"node_name": "nñ"}, "node_type": "publisher",
             "difficulty": "Easy", "ros_concepts": []}
    out = pb.render(task)
    assert "café" in out and "nñ" in out
