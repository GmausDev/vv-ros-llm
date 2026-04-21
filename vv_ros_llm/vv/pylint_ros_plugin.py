"""Custom pylint plugin with ROS 2 (rclpy) checkers.

Register via `pylint --load-plugins=vv_ros_llm.vv.pylint_ros_plugin`.
"""

from __future__ import annotations

from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint import PyLinter


class RclpyLifecycleChecker(BaseChecker):
    name = "rclpy-lifecycle"
    msgs = {
        "W9001": (
            "Missing rclpy.init() call",
            "missing-rclpy-init",
            "Program must call rclpy.init(args=args) before creating nodes.",
        ),
        "W9002": (
            "Missing rclpy.shutdown() call",
            "missing-rclpy-shutdown",
            "Program must call rclpy.shutdown() before exit.",
        ),
        "W9003": (
            "Missing destroy_node() call",
            "missing-destroy-node",
            "Nodes should call destroy_node() to release DDS resources.",
        ),
    }

    def __init__(self, linter: PyLinter):
        super().__init__(linter)
        self._saw_init = False
        self._saw_shutdown = False
        self._saw_destroy = False

    def visit_call(self, node: nodes.Call) -> None:
        if isinstance(node.func, nodes.Attribute):
            func_name = node.func.attrname
            parent = node.func.expr.as_string() if hasattr(node.func, "expr") else ""
            if func_name == "init" and "rclpy" in parent:
                self._saw_init = True
            if func_name == "shutdown" and "rclpy" in parent:
                self._saw_shutdown = True
            if func_name == "destroy_node":
                self._saw_destroy = True

    def close(self) -> None:
        if not self._saw_init:
            self.add_message("missing-rclpy-init", node=None, line=1)
        if not self._saw_shutdown:
            self.add_message("missing-rclpy-shutdown", node=None, line=1)
        if not self._saw_destroy:
            self.add_message("missing-destroy-node", node=None, line=1)
        self._saw_init = self._saw_shutdown = self._saw_destroy = False


class BlockingCallInCallbackChecker(BaseChecker):
    name = "rclpy-blocking-callbacks"
    msgs = {
        "W9010": (
            "Blocking call %s inside rclpy callback",
            "blocking-in-callback",
            "Callbacks registered with create_timer/create_subscription should not block.",
        ),
    }
    BLOCKING = {"time.sleep", "input", "requests.get", "requests.post"}

    def __init__(self, linter: PyLinter):
        super().__init__(linter)
        self._in_callback = 0

    def visit_functiondef(self, node: nodes.FunctionDef) -> None:
        if node.name.endswith("_callback") or "callback" in node.name.lower():
            self._in_callback += 1

    def leave_functiondef(self, node: nodes.FunctionDef) -> None:
        if node.name.endswith("_callback") or "callback" in node.name.lower():
            self._in_callback = max(0, self._in_callback - 1)

    def visit_call(self, node: nodes.Call) -> None:
        if not self._in_callback:
            return
        name = ""
        if isinstance(node.func, nodes.Attribute):
            base = node.func.expr.as_string() if hasattr(node.func, "expr") else ""
            name = f"{base}.{node.func.attrname}"
        elif isinstance(node.func, nodes.Name):
            name = node.func.name
        if name in self.BLOCKING:
            self.add_message("blocking-in-callback", node=node, args=(name,))


class QosDepthChecker(BaseChecker):
    name = "rclpy-qos-depth"
    msgs = {
        "W9020": (
            "create_publisher/subscription missing explicit qos_profile or depth",
            "missing-qos-depth",
            "Prefer explicit QoS or at minimum an integer depth >= 1.",
        ),
    }

    def visit_call(self, node: nodes.Call) -> None:
        if isinstance(node.func, nodes.Attribute) and node.func.attrname in (
            "create_publisher",
            "create_subscription",
        ):
            if len(node.args) < 3 and not any(
                k.arg in ("qos_profile", "depth") for k in node.keywords
            ):
                self.add_message("missing-qos-depth", node=node)


def register(linter: PyLinter) -> None:
    linter.register_checker(RclpyLifecycleChecker(linter))
    linter.register_checker(BlockingCallInCallbackChecker(linter))
    linter.register_checker(QosDepthChecker(linter))
