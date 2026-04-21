from __future__ import annotations

import json
import textwrap
from pathlib import Path

NODE_FILE = "candidate_node.py"
RUN_SCRIPT = "run_candidate.sh"
ORACLE_SPEC = "oracle.json"


def write_candidate_workspace(
    workspace: Path,
    *,
    candidate_code: str,
    entry_point: str,
    interface_spec: dict,
    test_oracle: dict,
    extras: dict[str, str] | None = None,
) -> Path:
    """Lay out files inside `workspace` so that VV methods can invoke them in-container.

    Produces:
      - candidate_node.py (the LLM-generated code)
      - oracle.json       (test oracle spec)
      - interface_spec.json
      - run_candidate.sh  (sources ROS env + launches main())
      - any extra files in `extras`
    """
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / NODE_FILE).write_text(candidate_code, encoding="utf-8")
    (workspace / ORACLE_SPEC).write_text(
        json.dumps(test_oracle, default=str), encoding="utf-8"
    )
    (workspace / "interface_spec.json").write_text(
        json.dumps(interface_spec, default=str), encoding="utf-8"
    )
    run_sh = (
        textwrap.dedent(
            f"""
            #!/usr/bin/env bash
            set -e
            python3 {NODE_FILE}
            """
        ).strip()
        + "\n"
    )
    (workspace / RUN_SCRIPT).write_text(run_sh, encoding="utf-8")
    if extras:
        for rel, content in extras.items():
            p = workspace / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return workspace
