from __future__ import annotations
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

_CODE_BLOCK = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

DEFAULT_TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptBuilder:
    def __init__(self, templates_dir: Path | str = DEFAULT_TEMPLATE_DIR):
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            undefined=StrictUndefined,
            autoescape=select_autoescape(enabled_extensions=()),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        task: dict,
        fewshot: list[dict] | None = None,
        ros_distro: str = "humble",
        strictness: str = "strict",
    ) -> str:
        system = self.env.get_template("system.j2").render(
            ros_distro=ros_distro, strictness=strictness
        )
        task_str = self.env.get_template("task.j2").render(
            task_id=task["task_id"],
            prompt=task["prompt"],
            entry_point=task["entry_point"],
            interface_spec=task.get("interface_spec", {}),
            node_type=task.get("node_type", "unknown"),
            difficulty=task.get("difficulty", "unknown"),
            ros_concepts=task.get("ros_concepts", []),
        )
        parts = [system, task_str]
        if fewshot:
            parts.insert(1, self.env.get_template("fewshot.j2").render(examples=fewshot))
        return "\n\n".join(parts).strip() + "\n"


def extract_python_code(text: str) -> str:
    """Extract first python code block; fall back to the raw text if none found."""
    m = _CODE_BLOCK.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()
